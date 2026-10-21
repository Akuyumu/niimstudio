import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from niimstudio.updates import (
    fetch_latest,
    managed_root,
    update_command,
    updates_enabled,
    version_tuple,
)


class VersionTests(unittest.TestCase):
    def test_versions_require_three_numeric_parts(self):
        self.assertEqual(version_tuple("v0.1.2"), (0, 1, 2))
        self.assertEqual(version_tuple(" 1.20.300 "), (1, 20, 300))
        for value in ("", "0.1", "0.1.2-rc1", "v1.2.3.4", "latest", None):
            with self.subTest(value=value):
                self.assertIsNone(version_tuple(value))

    def test_update_check_uses_a_fixed_api_and_user_agent(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({"tag_name": "v0.2.0"}).encode()
        with patch("urllib.request.urlopen", return_value=response) as opened:
            self.assertEqual(fetch_latest("0.1.2"), {"version": "0.2.0", "tag": "v0.2.0"})
        request = opened.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.github.com/repos/Akuyumu/niimstudio/releases/latest")
        self.assertEqual(request.get_header("User-agent"), "NiimStudio/0.1.2")

    def test_same_or_older_releases_do_not_offer_an_update(self):
        for tag in ("v0.1.2", "v0.1.1", "v0.0.9"):
            response = MagicMock()
            response.__enter__.return_value.read.return_value = json.dumps({"tag_name": tag}).encode()
            with self.subTest(tag=tag), patch("urllib.request.urlopen", return_value=response):
                self.assertIsNone(fetch_latest("0.1.2"))

    def test_installed_candidate_can_upgrade_to_final_but_not_downgrade_or_follow_candidates(self):
        for data, expected in [
            ({"tag_name": "v0.1.3"}, None),
            ({"tag_name": "v0.2.0"}, {"version": "0.2.0", "tag": "v0.2.0"}),
            ({"tag_name": "v0.2.0-rc.2", "prerelease": True}, None),
            ({"tag_name": "v0.2.0-rc.2"}, None),
        ]:
            response = MagicMock()
            response.__enter__.return_value.read.return_value = json.dumps(data).encode()
            with self.subTest(data=data), patch("urllib.request.urlopen", return_value=response):
                self.assertEqual(fetch_latest("0.2.0-rc.1"), expected)

    def test_drafts_and_prereleases_never_reach_stable_users(self):
        for metadata in ({"draft": True}, {"prerelease": True}, {"tag_name": "v0.2.0-rc1"}):
            response = MagicMock()
            response.__enter__.return_value.read.return_value = json.dumps({"tag_name": "v0.2.0", **metadata}).encode()
            with self.subTest(metadata=metadata), patch("urllib.request.urlopen", return_value=response):
                self.assertIsNone(fetch_latest("0.1.2"))

    def test_update_command_is_pinned_and_does_not_install_packages(self):
        command = update_command("/tmp/niimstudio", "v0.2.0")
        self.assertIn("--version", command)
        self.assertIn("v0.2.0", command)
        self.assertIn("--yes", command)
        self.assertIn("--no-deps", command)
        self.assertTrue(command[1].endswith("scripts/managed_install.py"))


class ManagedInstallTests(unittest.TestCase):
    def test_source_checkouts_and_flatpak_are_not_self_updatable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertIsNone(managed_root(root))

            (root / "release.json").write_text(json.dumps({"product": "niimstudio", "version": "0.1.2"}))
            self.assertEqual(managed_root(root), root)
            self.assertIsNone(managed_root(root, {"FLATPAK_ID": "io.github.niimstudio.App"}))
            (root / "release.json").write_text(json.dumps({"product": "other", "version": "0.1.2"}))
            self.assertIsNone(managed_root(root))
            (root / "release.json").write_text("not json")
            self.assertIsNone(managed_root(root))

    def test_explicit_candidate_install_is_recognized_without_accepting_unknown_dev_versions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for version, expected in (("0.2.0-rc.1", root), ("0.2.0-dev", None)):
                (root / "release.json").write_text(json.dumps({"product": "niimstudio", "version": version}))
                self.assertEqual(managed_root(root), expected)

    def test_update_check_can_be_disabled(self):
        self.assertTrue(updates_enabled({}))
        self.assertFalse(updates_enabled({"NIIMSTUDIO_NO_UPDATE_CHECK": "1"}))

    def test_update_check_is_silent_when_offline(self):
        with patch("urllib.request.urlopen", side_effect=OSError("offline")):
            with self.assertRaises(OSError):
                fetch_latest("0.1.2")


if __name__ == "__main__":
    unittest.main()
