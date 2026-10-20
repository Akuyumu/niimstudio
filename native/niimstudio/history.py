"""Remember explicitly selected, successfully negotiated printers, not credentials."""

import json
import os
import tempfile
from pathlib import Path


class DeviceHistory:
    def __init__(self, path=None):
        self.path = (
            path or Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "niimstudio/settings.json"
        )
        self.auto_reconnect = True
        self.recent = []
        try:
            saved = json.loads(self.path.read_text())
            self.auto_reconnect = saved.get("autoReconnect", True) is True
            self.recent = [
                {key: device[key] for key in ("kind", "id", "name")}
                for device in saved.get("recent", [])[:10]
                if isinstance(device, dict)
                and device.get("kind") in ("serial", "bluetooth")
                and all(isinstance(device.get(key), str) for key in ("id", "name"))
            ]
        except (OSError, ValueError, TypeError, AttributeError):
            pass

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", dir=self.path.parent, prefix=".settings-", delete=False) as file:
                descriptor = Path(file.name)
                json.dump({"version": 1, "autoReconnect": self.auto_reconnect, "recent": self.recent}, file)
                file.flush()
                os.fsync(file.fileno())
            descriptor.replace(self.path)
        finally:
            if descriptor and descriptor.exists():
                descriptor.unlink()

    def remember(self, device):
        record = {key: device[key] for key in ("kind", "id", "name")}
        self.recent = [
            record,
            *(old for old in self.recent if (old["kind"], old["id"]) != (record["kind"], record["id"])),
        ][:10]
        self.save()

    def info(self):
        return {"enabled": self.auto_reconnect, "device": self.recent[0] if self.recent else None}

    def resolve_last(self, serial_devices, bluetooth_objects):
        if not self.auto_reconnect or not self.recent:
            raise ConnectionError("No remembered printer is available for automatic reconnect")
        record = self.recent[0]
        if record["kind"] == "serial":
            for device in serial_devices:
                if device["id"] == record["id"] and device["name"] == record["name"]:
                    return device
            raise ConnectionError("The remembered USB printer is not plugged in")
        if "org.bluez.Device1" not in bluetooth_objects.get(record["id"], {}):
            raise ConnectionError("The remembered Bluetooth printer is not known to BlueZ; open Devices to scan")
        return record.copy()
