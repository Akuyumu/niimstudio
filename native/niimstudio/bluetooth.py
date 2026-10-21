"""BlueZ transport: no browser Bluetooth flags or root daemon required."""

import time

from gi.repository import Gio, GLib

SERVICE_UUID = "e7810a71-73ae-499d-8c15-faa9aef0c3f2"
DEVICE = "org.bluez.Device1"
ADAPTER = "org.bluez.Adapter1"
CHARACTERISTIC = "org.bluez.GattCharacteristic1"
SERIAL_PORT_UUID = "00001101-0000-1000-8000-00805f9b34fb"


def classic_only(properties):
    uuids = {str(value).lower() for value in properties.get("UUIDs", [])}
    # No UUIDs yet is normal for an undiscovered BLE device; don't exclude it.
    return SERIAL_PORT_UUID in uuids and SERVICE_UUID not in uuids


def unpack(value):
    if isinstance(value, GLib.Variant):
        return unpack(value.unpack())
    if isinstance(value, dict):
        return {key: unpack(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [unpack(item) for item in value]
    return value


def is_printer(properties):
    name = properties.get("Name", properties.get("Alias", "")).upper()
    return SERVICE_UUID in properties.get("UUIDs", []) or name.startswith(
        ("NIIM", "B1", "B2", "B3", "B4", "D1", "D2", "M2", "K2", "P1", "N1")
    )


class BlueZ:
    def __init__(self):
        self.bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)

    def call(self, path, interface, method, parameters=None, timeout=10000):
        result = self.bus.call_sync(
            "org.bluez",
            path,
            interface,
            method,
            parameters,
            None,
            Gio.DBusCallFlags.NONE,
            timeout,
            None,
        )
        return unpack(result)

    def objects(self):
        return self.call("/", "org.freedesktop.DBus.ObjectManager", "GetManagedObjects")[0]

    def discover(self, show_all=False):
        objects = self.objects()
        devices = []
        for path, interfaces in objects.items():
            props = interfaces.get(DEVICE)
            if props and (show_all or (is_printer(props) and not classic_only(props))):
                devices.append(
                    {
                        "id": path,
                        "kind": "bluetooth",
                        "name": props.get("Alias", props.get("Name", props.get("Address", "Bluetooth device"))),
                        "address": props.get("Address", ""),
                        "paired": props.get("Paired", False),
                        "classic_only": classic_only(props),
                        "ble_confirmed": SERVICE_UUID in props.get("UUIDs", []),
                        "rssi": props.get("RSSI", -999),
                    }
                )
        return sorted(devices, key=lambda d: (not d["paired"], -d["rssi"], d["name"]))

    def start_scan(self):
        owned = []
        errors = []
        for path, interfaces in self.objects().items():
            props = interfaces.get(ADAPTER)
            if props is None or not props.get("Powered"):
                continue
            try:
                self.call(path, ADAPTER, "StartDiscovery")
                owned.append(path)
            except GLib.Error as error:
                errors.append(str(error))
        if not owned:
            raise RuntimeError(
                errors[0] if errors else "No powered Bluetooth adapter. Turn Bluetooth on in Omarchy first."
            )
        return owned

    def stop_scan(self, owned):
        # Release only this app's discovery sessions, not another app's scan.
        for path in owned:
            try:
                self.call(path, ADAPTER, "StopDiscovery")
            except GLib.Error:
                pass


class BluetoothTransport:
    def __init__(self, bluez, on_data, on_disconnect):
        self.bluez = bluez
        self.on_data = on_data
        self.on_disconnect = on_disconnect
        self.device = None
        self.channel = None
        self.notify_channel = None
        self.subscription = None
        self.chunk_size = 20
        self.write_type = "command"

    def open(self, device):
        properties = self.bluez.objects().get(device, {}).get(DEVICE, {})
        if classic_only(properties):
            raise RuntimeError("This is the classic Bluetooth Serial Port entry, not the NIIMBOT Bluetooth LE entry.")
        self.device = device
        try:
            self.bluez.call(device, DEVICE, "Connect", timeout=25000)
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                objects = self.bluez.objects()
                if objects.get(device, {}).get(DEVICE, {}).get("ServicesResolved"):
                    break
                time.sleep(0.15)
            else:
                raise TimeoutError("Bluetooth services were not resolved. Close the phone's NIIMBOT app and retry.")

            services = {
                path
                for path, interfaces in objects.items()
                if interfaces.get("org.bluez.GattService1", {}).get("Device") == device
                and interfaces["org.bluez.GattService1"].get("UUID") == SERVICE_UUID
            }
            channels = [
                (path, interfaces[CHARACTERISTIC])
                for path, interfaces in objects.items()
                if CHARACTERISTIC in interfaces and interfaces[CHARACTERISTIC].get("Service") in services
            ]
            # Same preferred combination as NiimBlue; also allow split TX/RX.
            tx = next(((path, p) for path, p in channels if "write-without-response" in p.get("Flags", [])), None)
            if tx is None:
                tx = next(((path, p) for path, p in channels if "write" in p.get("Flags", [])), None)
            rx = next(
                ((path, p) for path, p in channels if "notify" in p.get("Flags", []) and tx and path == tx[0]), None
            )
            rx = rx or next(((path, p) for path, p in channels if "notify" in p.get("Flags", [])), None)
            if not tx or not rx:
                raise RuntimeError(
                    "No NIIMBOT BLE write/notify channel found. Try USB or check this model's protocol support."
                )
            self.channel, props = tx
            self.notify_channel = rx[0]
            self.chunk_size = max(20, min(int(props.get("MTU", 23)) - 3, 512))
            self.write_type = "command" if "write-without-response" in props.get("Flags", []) else "request"
            self.subscription = self.bluez.bus.signal_subscribe(
                "org.bluez",
                "org.freedesktop.DBus.Properties",
                "PropertiesChanged",
                None,
                None,
                Gio.DBusSignalFlags.NONE,
                self._properties_changed,
            )
            self.bluez.call(self.notify_channel, CHARACTERISTIC, "StartNotify")
        except Exception:
            self.close()
            raise

    def _properties_changed(self, connection, sender, path, interface, signal, parameters):
        iface, changed, _invalidated = unpack(parameters)
        if path == self.notify_channel and iface == CHARACTERISTIC and "Value" in changed:
            self.on_data(bytes(changed["Value"]))
        if path == self.device and iface == DEVICE and changed.get("Connected") is False:
            self.on_disconnect("Bluetooth printer disconnected")

    def write(self, data):
        if self.channel is None:
            raise ConnectionError("Bluetooth printer is disconnected")
        for start in range(0, len(data), self.chunk_size):
            chunk = list(data[start : start + self.chunk_size])
            self.bluez.call(
                self.channel,
                CHARACTERISTIC,
                "WriteValue",
                GLib.Variant(
                    "(aya{sv})",
                    (chunk, {"type": GLib.Variant("s", self.write_type)}),
                ),
            )

    def close(self):
        if self.subscription is not None:
            self.bluez.bus.signal_unsubscribe(self.subscription)
            self.subscription = None
        if self.device:
            try:
                self.bluez.call(self.device, DEVICE, "Disconnect", timeout=5000)
            except GLib.Error:
                pass
        self.device = self.channel = self.notify_channel = None
