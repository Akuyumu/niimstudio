"""BlueZ transport: no browser Bluetooth flags or root daemon required."""

import threading
import time

from gi.repository import Gio, GLib

SERVICE_UUID = "e7810a71-73ae-499d-8c15-faa9aef0c3f2"
CHANNEL_UUID = "bef8d6c9-9c21-4c9e-b632-bd58c1009f9f"
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
        self.discovery_owners = {}
        self.le_filters = set()

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
                self.acquire_scan(path)
                owned.append(path)
            except GLib.Error as error:
                errors.append(str(error))
        if not owned:
            raise RuntimeError(
                errors[0] if errors else "No powered Bluetooth adapter. Turn Bluetooth on in Omarchy first."
            )
        return owned

    def acquire_scan(self, adapter, le_only=False):
        if adapter in self.discovery_owners:
            self.discovery_owners[adapter] += 1
            return
        if le_only:
            self.call(
                adapter,
                ADAPTER,
                "SetDiscoveryFilter",
                GLib.Variant("(a{sv})", ({"Transport": GLib.Variant("s", "le")},)),
            )
            self.le_filters.add(adapter)
        try:
            self.call(adapter, ADAPTER, "StartDiscovery")
        except Exception:
            if adapter in self.le_filters:
                self.le_filters.remove(adapter)
                try:
                    self.call(adapter, ADAPTER, "SetDiscoveryFilter", GLib.Variant("(a{sv})", ({},)))
                except GLib.Error:
                    pass
            raise
        self.discovery_owners[adapter] = 1

    def start_connection_scan(self, device):
        """Refresh a cached LE address before Connect, as Bleak does. No bond changes."""
        properties = self.objects().get(device, {}).get(DEVICE, {})
        adapter = properties.get("Adapter") or device.rsplit("/dev_", 1)[0]
        fresh = threading.Event()

        def changed(_bus, _sender, _path, _interface, _signal, parameters):
            interface, values, _invalid = unpack(parameters)
            if interface == DEVICE and any(
                key in values for key in ("RSSI", "ManufacturerData", "ServiceData", "AdvertisingData")
            ):
                fresh.set()

        subscription = self.bus.signal_subscribe(
            "org.bluez",
            "org.freedesktop.DBus.Properties",
            "PropertiesChanged",
            device,
            None,
            Gio.DBusSignalFlags.NONE,
            changed,
        )
        try:
            self.acquire_scan(adapter, le_only=True)
            # GIO dispatches on the app's main context; the connection worker is
            # allowed to wait without blocking GTK or its pairing agent.
            fresh.wait(5)
            return [adapter]
        finally:
            self.bus.signal_unsubscribe(subscription)

    def stop_scan(self, owned):
        # Release only this app's discovery sessions, not another app's scan.
        for path in owned:
            owners = self.discovery_owners.get(path, 0)
            if owners > 1:
                self.discovery_owners[path] = owners - 1
                continue
            if not owners:
                continue
            del self.discovery_owners[path]
            try:
                self.call(path, ADAPTER, "StopDiscovery")
            except GLib.Error:
                pass
            if path in self.le_filters:
                self.le_filters.remove(path)
                try:
                    self.call(path, ADAPTER, "SetDiscoveryFilter", GLib.Variant("(a{sv})", ({},)))
                except GLib.Error:
                    pass


class BluetoothTransport:
    def __init__(self, bluez, on_data, on_disconnect, on_progress=None):
        self.bluez = bluez
        self.on_data = on_data
        self.on_disconnect = on_disconnect
        self.on_progress = on_progress or (lambda _message: None)
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
        scan = []
        try:
            self.on_progress("Refreshing the printer's Bluetooth LE advertisement…")
            scan = self.bluez.start_connection_scan(device)
            self.on_progress("Opening Bluetooth LE link… This can take up to 25 seconds.")
            try:
                for attempt in range(2):
                    try:
                        self.bluez.call(device, DEVICE, "Connect", timeout=25000)
                        break
                    except Exception as error:
                        transient = "le-connection-abort-by-local" in str(error) or (
                            isinstance(error, GLib.Error)
                            and any(word in str(error).lower() for word in ("timeout", "timed out"))
                        )
                        if attempt or not transient:
                            raise
                        # A timed-out D-Bus call may leave a controller request
                        # pending. Cancel only our target before one bounded retry.
                        self.bluez.call(device, DEVICE, "Disconnect", timeout=5000)
                        self.on_progress("Bluetooth link was interrupted. Retrying once without pairing…")
                        time.sleep(0.5)
            except Exception as error:
                raise RuntimeError(
                    f"Bluetooth link connection failed before GATT service discovery: {error}. "
                    "No NIIMBOT handshake or printer command was sent."
                ) from error
            self.on_progress("Bluetooth link opened. Waiting for printer services…")
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
            combined = [
                (path, p) for path, p in channels if {"notify", "write-without-response"}.issubset(p.get("Flags", []))
            ]
            tx = next(((path, p) for path, p in combined if p.get("UUID", "").lower() == CHANNEL_UUID), None)
            tx = tx or next(iter(combined), None)
            tx = tx or next(((path, p) for path, p in channels if "write-without-response" in p.get("Flags", [])), None)
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
            self.on_progress("Printer service found. Enabling Bluetooth responses…")
            self.bluez.call(self.notify_channel, CHARACTERISTIC, "StartNotify")
        except Exception:
            self.close()
            raise
        finally:
            if scan:
                self.bluez.stop_scan(scan)

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
