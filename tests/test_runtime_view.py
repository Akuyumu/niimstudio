import os
import tempfile
import unittest
from pathlib import Path

from niimstudio.runtime_view import HOST_VIEW, OVERLAY_VIEW, runtime_view


class RuntimeViewTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.host = self.root / "host"
        self.host.mkdir()
        self.runtime = self.root / "runtime"
        self.overlay = self.runtime / "root/usr/lib"
        self.overlay.mkdir(parents=True)
        (self.host / "host.so").write_text("host")
        (self.overlay / "overlay.so").write_text("overlay")

    def test_reuses_view_without_recreating_links(self):
        with runtime_view(self.runtime, self.host) as first:
            inode = (first / "host.so").lstat().st_ino
        with runtime_view(self.runtime, self.host) as second:
            self.assertEqual(first, second)
            self.assertEqual(inode, (second / "host.so").lstat().st_ino)
            self.assertEqual((second / "host.so").readlink(), HOST_VIEW / "host.so")
            self.assertEqual((second / "overlay.so").readlink(), OVERLAY_VIEW / "overlay.so")

    def test_host_package_update_invalidates_view(self):
        with runtime_view(self.runtime, self.host) as first:
            pass
        (self.host / "new.so").write_text("new")
        with runtime_view(self.runtime, self.host) as second:
            self.assertNotEqual(first, second)
            self.assertTrue((second / "new.so").is_symlink())

    def test_nested_runtime_update_invalidates_view(self):
        nested = self.overlay / "nested"
        nested.mkdir()
        with runtime_view(self.runtime, self.host) as first:
            pass
        (nested / "new.so").write_text("new")
        with runtime_view(self.runtime, self.host) as second:
            self.assertNotEqual(first, second)
            self.assertEqual((second / "nested/new.so").readlink(), OVERLAY_VIEW / "nested/new.so")

    def test_overlay_overrides_host_and_keeps_symlinks(self):
        (self.overlay / "host.so").symlink_to("overlay.so")
        with runtime_view(self.runtime, self.host) as view:
            self.assertEqual((view / "host.so").readlink(), OVERLAY_VIEW / "host.so")

    def test_prunes_only_generated_unused_old_views(self):
        unrelated = self.runtime / "view-cache/unrelated"
        unrelated.mkdir(parents=True)
        (unrelated / "keep").write_text("user content")
        with runtime_view(self.runtime, self.host) as running:
            for index in range(4):
                (self.host / f"update{index}.so").write_text("update")
                with runtime_view(self.runtime, self.host):
                    self.assertTrue(running.is_dir())
        with runtime_view(self.runtime, self.host):
            self.assertFalse(running.exists())
        self.assertTrue((unrelated / "keep").is_file())
        views = [path for path in unrelated.parent.iterdir() if (path / ".niimstudio-view").is_file()]
        self.assertLessEqual(len(views), 2)

    def test_private_cache(self):
        with runtime_view(self.runtime, self.host) as view:
            self.assertEqual(os.stat(view.parent.parent).st_mode & 0o777, 0o700)
