import hashlib
import importlib.util
import io
import json
import os
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("managed_install", ROOT / "scripts/managed_install.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="niimstudio-installer-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.home = self.base / "test user"
        self.home.mkdir()
        self.environment = {"HOME": str(self.home), "XDG_DATA_HOME": str(self.home / "data")}
        self.patch = patch.dict(os.environ, self.environment)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.paths = installer.locations()
        self.saved = self.home / "data/niimstudio/keep.json"
        self.saved.parent.mkdir(parents=True)
        self.saved.write_text("private-label-fixture")

    def bundle(self, version="0.1.0", extra=None):
        directory = self.base / (version + str(len(list(self.base.glob("0.*")))))
        directory.mkdir()
        files = {
            "release.json": json.dumps({**installer.PRODUCT, "version": version}).encode(),
            "dist/index.html": version.encode(),
            "native/niimstudio/app.py": b"# synthetic",
            "LICENSE": b"MIT fixture",
            f"packaging/{installer.ICON}": (ROOT / f"packaging/{installer.ICON}").read_bytes(),
        }
        for name in ("scripts/niimstudio", "scripts/system-python", "scripts/managed_install.py", "install.sh"):
            files[name] = (ROOT / name).read_bytes()
        files.update(extra or {})
        archive = directory / installer.ASSET
        with tarfile.open(archive, "w:gz") as bundle:
            for name, data in sorted(files.items()):
                member = tarfile.TarInfo("niimstudio/" + name)
                member.size = len(data)
                member.mode = 0o755 if name in ("scripts/niimstudio", "scripts/system-python", "install.sh") else 0o644
                bundle.addfile(member, io.BytesIO(data))
        checksums = directory / "SHA256SUMS"
        checksums.write_text(hashlib.sha256(archive.read_bytes()).hexdigest() + "  " + installer.ASSET + "\n")
        return archive, checksums

    def test_install_repeat_upgrade_and_uninstall_preserve_user_data(self):
        first = self.bundle()
        installer.install(*first)
        old = (self.paths["root"] / "current").resolve()
        installer.install(*first)
        self.assertEqual((self.paths["root"] / "current").resolve(), old)
        installer.install(*self.bundle("0.1.1"))
        self.assertNotEqual((self.paths["root"] / "current").resolve(), old)
        self.assertTrue(old.exists())
        self.assertIn("test user", self.paths["desktop"].read_text())
        installer.uninstall()
        self.assertFalse(self.paths["launcher"].is_symlink())
        self.assertFalse(self.paths["root"].exists())
        self.assertEqual(self.saved.read_text(), "private-label-fixture")

    def test_corrupt_archive_is_rejected_before_any_install_changes(self):
        archive, checksums = self.bundle()
        archive.write_bytes(archive.read_bytes() + b"corruption")
        with self.assertRaisesRegex(ValueError, "checksum"):
            installer.install(archive, checksums)
        self.assertFalse(self.paths["root"].exists())

    def test_unrelated_launcher_is_not_replaced(self):
        launcher = self.paths["launcher"]
        launcher.parent.mkdir(parents=True)
        launcher.write_text("not-niimstudio")
        with self.assertRaisesRegex(ValueError, "Unrelated launcher"):
            installer.install(*self.bundle())
        self.assertEqual(launcher.read_text(), "not-niimstudio")

    def test_source_migration_requires_opt_in_and_keeps_checkout(self):
        source = self.base / "source/scripts"
        source.mkdir(parents=True)
        (source / "niimstudio").write_text("source fixture")
        self.paths["launcher"].parent.mkdir(parents=True)
        self.paths["launcher"].symlink_to(source / "niimstudio")
        self.paths["desktop"].parent.mkdir(parents=True)
        self.paths["desktop"].write_text(f"X-NiimStudio-Project={source.parent}\n")
        bundle = self.bundle()
        with self.assertRaisesRegex(ValueError, "replace-source"):
            installer.install(*bundle)
        installer.install(*bundle, replace_source=True)
        self.assertEqual((source / "niimstudio").read_text(), "source fixture")

    def test_traversal_absolute_links_and_duplicates_are_rejected(self):
        for name, kind in [
            ("niimstudio/../outside", tarfile.REGTYPE),
            ("/outside", tarfile.REGTYPE),
            ("niimstudio/link", tarfile.SYMTYPE),
            ("niimstudio/link", tarfile.LNKTYPE),
            ("niimstudio/device", tarfile.CHRTYPE),
        ]:
            with self.subTest(name=name, kind=kind), tempfile.TemporaryDirectory(dir=self.base) as temp:
                archive = Path(temp) / "unsafe.tar.gz"
                with tarfile.open(archive, "w:gz") as bundle:
                    member = tarfile.TarInfo(name)
                    member.type, member.linkname = kind, "/outside"
                    bundle.addfile(member)
                destination = Path(temp) / "out"
                destination.mkdir()
                with self.assertRaises(ValueError):
                    installer.extract_release(archive, destination)

    def test_incomplete_bundle_cannot_replace_active_release(self):
        installer.install(*self.bundle())
        before = (self.paths["root"] / "current").resolve()
        with self.assertRaisesRegex(ValueError, "manifest"):
            installer.install(*self.bundle("0.1.1", {"release.json": b'{"product":"other"}'}))
        self.assertEqual((self.paths["root"] / "current").resolve(), before)

    def test_failed_integration_rolls_back_current_and_launcher(self):
        installer.install(*self.bundle())
        old = (self.paths["root"] / "current").resolve()
        original = installer.atomic_file
        failed = False

        def failing(path, *args, **kwargs):
            nonlocal failed
            if path == self.paths["desktop"] and not failed:
                failed = True
                raise OSError("simulated disk failure")
            return original(path, *args, **kwargs)

        with patch.object(installer, "atomic_file", failing), self.assertRaises(OSError):
            installer.install(*self.bundle("0.1.1"))
        self.assertEqual((self.paths["root"] / "current").resolve(), old)
        self.assertTrue(self.paths["launcher"].is_symlink())

    def test_concurrent_install_does_not_switch_the_active_version(self):
        bundle = self.bundle()
        installer.install(*bundle)
        with installer.install_lock(self.paths["root"]), self.assertRaisesRegex(ValueError, "in progress"):
            installer.install(*bundle)

    def test_modified_release_is_not_overwritten(self):
        bundle = self.bundle()
        installer.install(*bundle)
        target = self.paths["root"] / "current/dist/index.html"
        target.write_text("user change")
        with self.assertRaisesRegex(ValueError, "modified"):
            installer.install(*bundle)
        self.assertEqual(target.read_text(), "user change")

    def test_foreign_current_symlink_and_icon_block_uninstall(self):
        installer.install(*self.bundle())
        self.paths["icon"].write_text("<!-- NiimStudio local install --> modified")
        with self.assertRaisesRegex(ValueError, "modified"):
            installer.uninstall()
        self.assertTrue(self.paths["launcher"].exists())
        current = self.paths["root"] / "current"
        current.unlink()
        current.symlink_to(self.saved.parent)
        with self.assertRaisesRegex(ValueError, "unrelated current"):
            installer.uninstall()
        self.assertEqual(self.saved.read_text(), "private-label-fixture")

    @unittest.skipIf(os.geteuid() == 0, "bootstrap intentionally refuses root")
    def test_flatpak_bootstrap_verifies_before_install_and_keeps_data(self):
        fake_bin = self.base / "bin"
        fake_bin.mkdir()
        assets = self.base / "assets"
        assets.mkdir()
        log = self.base / "flatpak.log"
        for arch in ("x86_64", "aarch64"):
            (assets / f"niimstudio-linux-{arch}.flatpak").write_bytes(b"synthetic-flatpak")
        (assets / "SHA256SUMS").write_text(
            "".join(
                f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n" for path in assets.glob("*.flatpak")
            )
        )
        scripts = {
            "curl": """#!/usr/bin/env python3
import os,sys,shutil
from pathlib import Path
args=sys.argv[1:]
shutil.copyfile(Path(os.environ['FIXTURE_ASSETS'])/args[-1].rsplit('/',1)[-1],args[args.index('--output')+1])
""",
            "flatpak": """#!/usr/bin/env python3
import os,sys
from pathlib import Path
args=sys.argv[1:]
if 'info' in args: sys.exit(1)
if 'remotes' in args: print('niimstudio-runtime\\thttps://dl.flathub.org/repo/')
if 'install' in args: Path(os.environ['FIXTURE_LOG']).write_text('installed')
""",
        }
        for name, script in scripts.items():
            (fake_bin / name).write_text(script)
            (fake_bin / name).chmod(0o755)
        environment = {
            **os.environ,
            "PATH": str(fake_bin) + ":" + os.environ["PATH"],
            "FIXTURE_ASSETS": str(assets),
            "FIXTURE_LOG": str(log),
        }
        command = ["bash", str(ROOT / "install.sh"), "--flatpak", "--no-deps", "--yes"]
        result = subprocess.run(command, env=environment, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(log.read_text(), "installed")
        log.unlink()
        (assets / "SHA256SUMS").write_text("0" * 64 + "  niimstudio-linux-" + os.uname().machine + ".flatpak\n")
        result = subprocess.run(command, env=environment, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(log.exists())
        self.assertEqual(self.saved.read_text(), "private-label-fixture")

    def test_flatpak_permissions_do_not_grant_general_home_access(self):
        manifest = json.loads((ROOT / "packaging/flatpak/io.github.niimstudio.App.json").read_text())
        self.assertEqual(manifest["app-id"], "io.github.niimstudio.App")
        self.assertIn("--system-talk-name=org.bluez", manifest["finish-args"])
        self.assertNotIn("--filesystem=home", manifest["finish-args"])
        self.assertNotIn("--filesystem=host", manifest["finish-args"])

    def test_package_dispatch_covers_linux_families_without_executing_packages(self):
        functions = (ROOT / "install.sh").read_text().rsplit('main "$@"', 1)[0]
        expected = {
            "arch": "pacman",
            "ubuntu": "apt-get",
            "debian": "apt-get",
            "fedora": "dnf",
            "rhel": "dnf",
            "opensuse-tumbleweed": "zypper",
            "alpine": "apk",
            "void": "xbps-install",
        }
        for distro, manager in expected.items():
            with self.subTest(distro=distro):
                release = self.base / "os-release"
                release.write_text(f"ID={distro}\n")
                script = functions + '\ndeclare -a deps=(); dependency_command flatpak "$1"; printf "%s" "${deps[0]}"\n'
                result = subprocess.check_output(["bash", "-s", "--", str(release)], input=script, text=True)
                self.assertEqual(result, manager)


if __name__ == "__main__":
    unittest.main()
