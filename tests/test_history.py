import json
import stat
import tempfile
import unittest
from pathlib import Path

from niimstudio.history import DeviceHistory


class HistoryTests(unittest.TestCase):
    def test_remember_deduplicate_reload_and_private_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config/settings.json"
            history = DeviceHistory(path)
            first = {"kind": "serial", "id": "/dev/ttyACM0", "name": "B1 Pro", "password": "never-store"}
            second = {"kind": "bluetooth", "id": "/org/bluez/device", "name": "B1"}
            history.remember(first)
            history.remember(second)
            history.remember(first)
            loaded = DeviceHistory(path)
            self.assertEqual(len(loaded.recent), 2)
            self.assertEqual(loaded.info()["device"]["name"], "B1 Pro")
            self.assertNotIn("password", path.read_text())
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(list(path.parent.glob(".settings-*")), [])

    def test_usb_reconnect_only_uses_a_current_matching_device(self):
        history = DeviceHistory(Path("/nonexistent/settings.json"))
        device = {"kind": "serial", "id": "/dev/ttyACM0", "name": "B1 Pro"}
        history.recent = [device]
        self.assertEqual(history.resolve_last([device], {}), device)
        with self.assertRaises(ConnectionError):
            history.resolve_last([], {})
        with self.assertRaises(ConnectionError):
            history.resolve_last([{**device, "name": "Other device"}], {})

    def test_bluetooth_reconnect_cannot_use_an_arbitrary_object_path(self):
        history = DeviceHistory(Path("/nonexistent/settings.json"))
        history.recent = [{"kind": "bluetooth", "id": "/org/bluez/device", "name": "B1"}]
        with self.assertRaises(ConnectionError):
            history.resolve_last([], {"/org/bluez/device": {}})
        self.assertEqual(history.resolve_last([], {"/org/bluez/device": {"org.bluez.Device1": {}}})["name"], "B1")
        history.auto_reconnect = False
        with self.assertRaises(ConnectionError):
            history.resolve_last([], {"/org/bluez/device": {"org.bluez.Device1": {}}})

    def test_malformed_history_is_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            for contents in (
                "[",
                "null",
                '{"recent":null}',
                json.dumps({"recent": [{"kind": "shell", "id": "/bin/sh", "name": "x"}]}),
            ):
                path.write_text(contents)
                self.assertEqual(DeviceHistory(path).recent, [])

    def test_forget_removes_last_printer_name_and_usb_ble_variants(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            history = DeviceHistory(path)
            history.recent = [
                {"kind": "bluetooth", "id": "/ble", "name": "B1 Pro"},
                {"kind": "serial", "id": "/usb", "name": "B1 Pro"},
                {"kind": "serial", "id": "/other", "name": "Other"},
            ]
            self.assertTrue(history.forget_remembered())
            self.assertEqual([item["name"] for item in history.recent], ["Other"])
            self.assertEqual(DeviceHistory(path).info()["device"]["name"], "Other")
            self.assertTrue(history.forget_remembered())
            self.assertEqual(history.recent, [])
            self.assertFalse(history.forget_remembered())
