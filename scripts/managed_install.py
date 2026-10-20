#!/usr/bin/env python3
"""Stdlib-only, user-local release installation. No app data or system settings."""

import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

PRODUCT = {"product": "niimstudio", "format": 1}
MARKER = ".niimstudio-install.json"
MANIFEST = "release.json"
ASSET = "niimstudio-linux.tar.gz"
ICON = "io.github.niimstudio.App.svg"


def locations():
    home = Path.home()
    data = Path(os.environ.get("XDG_DATA_HOME", home / ".local/share"))
    if not data.is_absolute():
        raise ValueError("XDG_DATA_HOME must be absolute")
    return {
        "root": data / "niimstudio-app",
        "launcher": home / ".local/bin/niimstudio",
        "desktop": data / "applications/io.github.niimstudio.App.desktop",
        "icon": data / f"icons/hicolor/scalable/apps/{ICON}",
    }


def read_json(path):
    return json.loads(path.read_text())


def owned_root(root):
    if root.is_symlink():
        raise ValueError("The managed install directory must not be a symlink")
    if root.exists() and any(root.iterdir()):
        if not (root / MARKER).is_file() or read_json(root / MARKER) != PRODUCT:
            raise ValueError(f"Refusing to replace an unrelated directory: {root}")
    current = root / "current"
    if current.exists() or current.is_symlink():
        if not current.is_symlink() or current.resolve().parent != root.resolve() / "releases":
            raise ValueError("Refusing an unrelated current-release path")


def atomic_file(path, content=None, link=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=".niimstudio-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as file:
            if content is not None:
                file.write(content)
                file.flush()
                os.fsync(file.fileno())
        if link is not None:
            temporary.unlink()
            temporary.symlink_to(link)
        else:
            temporary.chmod(0o644)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def install_lock(root):
    owned_root(root)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if (root / ".install.lock").is_symlink():
        raise ValueError("Install lock must not be a symlink")
    with (root / ".install.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError("Another NiimStudio installation is in progress") from error
        owned_root_contents = set(root.iterdir()) - {root / ".install.lock"}
        if not owned_root_contents:
            atomic_file(root / MARKER, json.dumps(PRODUCT).encode())
        yield


def verify_archive(archive, checksums):
    if archive.stat().st_size > 50 * 1024 * 1024:
        raise ValueError("Release download is unexpectedly large")
    hashes = [
        line.split()[0]
        for line in checksums.read_text().splitlines()
        if len(line.split()) == 2 and line.split()[1] == ASSET
    ]
    with archive.open("rb") as source:
        actual = hashlib.file_digest(source, "sha256").hexdigest()
    if len(hashes) != 1 or not re.fullmatch(r"[a-f0-9]{64}", hashes[0]) or hashes[0] != actual:
        raise ValueError("Release checksum mismatch")
    return actual


def extract_release(archive, destination):
    """No links, devices, duplicate paths, traversal, or unbounded expansion."""
    with tarfile.open(archive, "r:gz") as bundle:
        seen, total = set(), 0
        for index, member in enumerate(bundle):
            name = PurePosixPath(member.name)
            if (
                index > 5000
                or name.is_absolute()
                or ".." in name.parts
                or not name.parts
                or name.parts[0] != "niimstudio"
            ):
                raise ValueError("Unsafe release archive path")
            if name in seen or not (member.isdir() or member.isfile()):
                raise ValueError("Release archive contains duplicate paths or special files")
            seen.add(name)
            total += member.size
            if member.size < 0 or total > 100 * 1024 * 1024:
                raise ValueError("Release archive expands beyond its size limit")
            target = destination.joinpath(*name.parts[1:])
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.extractfile(member) as source, target.open("xb") as output:
                    shutil.copyfileobj(source, output)
                target.chmod(0o755 if member.mode & 0o111 else 0o644)
    manifest = read_json(destination / MANIFEST)
    if (
        manifest.get("product") != "niimstudio"
        or manifest.get("format") != 1
        or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?", manifest.get("version", ""))
    ):
        raise ValueError("Invalid NiimStudio release manifest")
    for required in (
        "dist/index.html",
        "native/niimstudio/app.py",
        "scripts/niimstudio",
        "scripts/system-python",
        "scripts/managed_install.py",
        "install.sh",
        f"packaging/{ICON}",
        "LICENSE",
    ):
        if not (destination / required).is_file():
            raise ValueError(f"Incomplete release: missing {required}")
    return manifest


def integration_owned(paths, replace_source=False):
    root, launcher, desktop, icon = (paths[key] for key in ("root", "launcher", "desktop", "icon"))
    source = None
    text = desktop.read_text() if desktop.is_file() and not desktop.is_symlink() else ""
    project = next(
        (line.split("=", 1)[1] for line in text.splitlines() if line.startswith("X-NiimStudio-Project=")), ""
    )
    if project and launcher.is_symlink() and launcher.resolve() == Path(project) / "scripts/niimstudio":
        source = project
    managed_desktop = (
        f"X-NiimStudio-Install={root}" in text.splitlines() and "X-NiimStudio-Managed=true" in text.splitlines()
    )
    if launcher.exists() or launcher.is_symlink():
        if not launcher.is_symlink() or (
            os.readlink(launcher) != str(root / "current/scripts/niimstudio") and not source
        ):
            raise ValueError(f"Unrelated launcher already exists: {launcher}")
    if desktop.exists() or desktop.is_symlink():
        if desktop.is_symlink() or not (managed_desktop or source):
            raise ValueError(f"Unrelated desktop entry already exists: {desktop}")
    if icon.exists() or icon.is_symlink():
        if icon.is_symlink() or "<!-- NiimStudio local install -->" not in icon.read_text():
            raise ValueError(f"Unrelated icon already exists: {icon}")
    if source and not replace_source:
        raise ValueError(
            f"A source-checkout launcher exists ({source}). Rerun with --replace-source to replace only its launcher/menu entry; the checkout will be kept"
        )


def snapshot(path):
    if path.is_symlink():
        return "link", os.readlink(path)
    if path.exists():
        if not path.is_file():
            raise ValueError(f"Expected a file, not a directory: {path}")
        return "file", path.read_bytes()
    return "missing", None


def desktop_contents(root):
    executable = str(root / "current/scripts/niimstudio")
    if any(character in executable for character in "\n\r"):
        raise ValueError("Install paths must not contain newlines")
    for character in ("\\", '"', "`", "$"):
        executable = executable.replace(character, "\\" + character)
    executable = executable.replace("%", "%%")
    return f'''[Desktop Entry]
Type=Application
Name=NiimStudio
Comment=Local NIIMBOT label designer and printer
Exec="{executable}"
Icon=io.github.niimstudio.App
Terminal=false
Categories=Graphics;
Keywords=NIIMBOT;labels;printer;Bluetooth;
StartupNotify=true
X-NiimStudio-Managed=true
X-NiimStudio-Install={root}
'''.encode()


def refresh_desktop(paths):
    if shutil.which("update-desktop-database"):
        subprocess.run(["update-desktop-database", str(paths["desktop"].parent)], check=False)


def install(archive, checksums, replace_source=False):
    digest = verify_archive(archive, checksums)
    paths = locations()
    root = paths["root"]
    owned_root(root)
    integration_owned(paths, replace_source)
    with install_lock(root):
        integration_owned(paths, replace_source)
        releases = root / "releases"
        if releases.is_symlink():
            raise ValueError("Release directory must not be a symlink")
        releases.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".stage-", dir=root) as staging:
            candidate = Path(staging)
            manifest = extract_release(archive, candidate)
            target = releases / f"{manifest['version']}-{digest[:16]}"
            if target.is_symlink():
                raise ValueError("Release target must not be a symlink")
            if target.exists():
                # Reuse only byte-identical contents, not a possibly edited old release.
                if any(path.is_symlink() for path in target.rglob("*")) or {
                    path.relative_to(target) for path in target.rglob("*")
                } != {path.relative_to(candidate) for path in candidate.rglob("*")}:
                    raise ValueError("Installed release file list was modified")
                for file in candidate.rglob("*"):
                    if file.is_file():
                        installed = target / file.relative_to(candidate)
                        if (
                            installed.is_symlink()
                            or not installed.is_file()
                            or installed.read_bytes() != file.read_bytes()
                        ):
                            raise ValueError("Installed release was modified; refusing to overwrite it")
            else:
                shutil.copytree(candidate, target)
            changes = {
                paths["launcher"]: (None, str(root / "current/scripts/niimstudio")),
                paths["desktop"]: (desktop_contents(root), None),
                paths["icon"]: ((target / f"packaging/{ICON}").read_bytes(), None),
                root / "current": (None, str(target)),
            }
            previous = {path: snapshot(path) for path in changes}
            try:
                for path, (content, link) in changes.items():
                    atomic_file(path, content, link)
            except OSError:
                for path, (kind, value) in previous.items():
                    if kind == "missing":
                        path.unlink(missing_ok=True)
                    else:
                        atomic_file(path, value if kind == "file" else None, value if kind == "link" else None)
                raise
    refresh_desktop(paths)
    print(f"Installed NiimStudio {manifest['version']}. Open NiimStudio from your app menu.")
    print(
        f"Command: {paths['launcher']}\nUpdate: {paths['launcher']} --update\nUninstall: {paths['launcher']} --uninstall"
    )
    if str(paths["launcher"].parent) not in os.environ.get("PATH", "").split(os.pathsep):
        print("~/.local/bin is not in PATH. Use the app menu or the full command above; no shell profile was changed.")


def uninstall():
    paths = locations()
    root = paths["root"]
    if not (root / MARKER).is_file():
        raise ValueError("No managed installation found; source checkouts are not removed")
    with install_lock(root):
        integration_owned(paths)
        releases = root / "releases"
        if releases.is_symlink():
            raise ValueError("Refusing to remove a symlinked releases directory")
        removable = []
        if releases.is_dir():
            for release in releases.iterdir():
                if (
                    release.is_dir()
                    and not release.is_symlink()
                    and re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?-[a-f0-9]{16}", release.name)
                ):
                    if read_json(release / MANIFEST).get("product") != "niimstudio":
                        raise ValueError("Unrecognized release contents; uninstall canceled")
                    removable.append(release)
        # Do not remove an icon that the user replaced after installation.
        current = root / "current"
        expected_icon = current / f"packaging/{ICON}"
        if (
            paths["icon"].is_file()
            and expected_icon.is_file()
            and paths["icon"].read_bytes() != expected_icon.read_bytes()
        ):
            raise ValueError("Installed icon was modified; refusing to remove it")
        for key in ("launcher", "desktop", "icon"):
            paths[key].unlink(missing_ok=True)
        current.unlink(missing_ok=True)
        if releases.is_dir():
            for release in removable:
                shutil.rmtree(release)
            try:
                releases.rmdir()
            except OSError:
                print(f"Preserved unrecognized files under {releases}")
        (root / MARKER).unlink()
    (root / ".install.lock").unlink(missing_ok=True)
    try:
        root.rmdir()
    except OSError:
        print(f"Preserved unrecognized files under {root}")
    refresh_desktop(paths)
    print("NiimStudio uninstalled. Saved labels, drafts, settings and source checkouts were kept.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("install", "uninstall", "version", "update"))
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--checksums", type=Path)
    parser.add_argument("--replace-source", action="store_true")
    args, extra = parser.parse_known_args()
    if args.command == "version":
        root = Path(__file__).resolve().parents[1]
        print("NiimStudio " + read_json(root / (MANIFEST if (root / MANIFEST).exists() else "package.json"))["version"])
        return
    if os.geteuid() == 0:
        parser.error("Run as your normal user, not root")
    if sys.platform != "linux":
        parser.error("Linux is required")
    if args.command == "update":
        root = locations()["root"]
        owned_root(root)
        installer = root / "current/install.sh"
        if not installer.is_file():
            parser.error("No managed install found; update your source checkout instead")
        raise SystemExit(subprocess.call(["bash", str(installer), *extra]))
    if extra:
        parser.error(f"Unknown arguments: {' '.join(extra)}")
    try:
        if args.command == "install":
            if args.archive is None or args.checksums is None:
                parser.error("--archive and --checksums are required")
            install(args.archive, args.checksums, args.replace_source)
        else:
            uninstall()
    except (OSError, ValueError, tarfile.TarError) as error:
        parser.exit(1, f"NiimStudio: {error}\n")


if __name__ == "__main__":
    main()
