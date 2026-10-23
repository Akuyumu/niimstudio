import tempfile
import unittest
from pathlib import Path

from niimstudio.app import asset_path, validate_message


class BridgeSecurityTests(unittest.TestCase):
    def test_assets_cannot_escape_bundled_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "dist"
            root.mkdir()
            index = root / "index.html"
            index.write_text("safe")
            secret = Path(directory) / "secret"
            secret.write_text("not public")
            (root / "escape").symlink_to(secret)
            self.assertEqual(asset_path("niimstudio://app/index.html", root), index)
            for uri in [
                "niimstudio://app/../secret",
                "niimstudio://app/%2e%2e/secret",
                "niimstudio://app/escape",
                "https://example.com/index.html",
                "niimstudio://evil/index.html",
            ]:
                with self.subTest(uri=uri), self.assertRaises(ValueError):
                    asset_path(uri, root)

    def test_bridge_only_has_documented_operations(self):
        self.assertEqual(validate_message({"id": 1, "op": "connect"})["op"], "connect")
        self.assertEqual(validate_message({"id": 1, "op": "cancelConnect"})["op"], "cancelConnect")
        for message in [{"id": True, "op": "write"}, {"id": 0, "op": "connect"}, {"id": 2, "op": "exec"}, [], None]:
            with self.subTest(message=message), self.assertRaises(ValueError):
                validate_message(message)
