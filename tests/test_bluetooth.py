import unittest
from unittest.mock import MagicMock, patch

from gi.repository import GLib
from niimstudio.bluetooth import (
    ADAPTER,
    CHANNEL_UUID,
    CHARACTERISTIC,
    DEVICE,
    SERIAL_PORT_UUID,
    SERVICE_UUID,
    BluetoothTransport,
    BlueZ,
    classic_only,
    is_printer,
    unpack,
)


class BluetoothTests(unittest.TestCase):
    def setup_bluez(self, mtu=23, split=False):
        device = "/org/bluez/hci0/dev_00_11_22_33_44_55"
        service, tx, rx = device + "/service001", device + "/service001/char001", device + "/service001/char002"
        objects = {
            device: {DEVICE: {"ServicesResolved": True}},
            service: {"org.bluez.GattService1": {"Device": device, "UUID": SERVICE_UUID}},
            tx: {
                CHARACTERISTIC: {
                    "Service": service,
                    "Flags": ["write-without-response"] + ([] if split else ["notify"]),
                    "MTU": mtu,
                }
            },
        }
        if split:
            objects[rx] = {CHARACTERISTIC: {"Service": service, "Flags": ["notify"]}}
        bluez = MagicMock()
        bluez.objects.return_value = objects
        bluez.bus.signal_subscribe.return_value = 42
        return bluez, device, tx, rx

    def test_mtu_fragmentation_and_notifications(self):
        bluez, device, channel, _rx = self.setup_bluez()
        data, disconnected = [], []
        transport = BluetoothTransport(bluez, data.append, disconnected.append)
        transport.open(device)
        transport.write(bytes(range(45)))
        writes = [call for call in bluez.call.call_args_list if call.args[2] == "WriteValue"]
        self.assertEqual([len(unpack(call.args[3])[0]) for call in writes], [20, 20, 5])
        self.assertEqual(unpack(writes[0].args[3])[1], {"type": "command"})
        transport._properties_changed(None, None, channel, None, None, (CHARACTERISTIC, {"Value": [85, 85]}, []))
        self.assertEqual(data, [b"UU"])
        transport._properties_changed(None, None, device, None, None, (DEVICE, {"Connected": False}, []))
        self.assertEqual(len(disconnected), 1)
        transport.close()
        bluez.bus.signal_unsubscribe.assert_called_once_with(42)

    def test_negotiated_mtu_and_split_channels(self):
        bluez, device, tx, rx = self.setup_bluez(mtu=247, split=True)
        transport = BluetoothTransport(bluez, lambda _data: None, lambda _reason: None)
        transport.open(device)
        self.assertEqual(transport.channel, tx)
        self.assertEqual(transport.notify_channel, rx)
        self.assertEqual(transport.chunk_size, 244)
        transport.close()

    def test_failed_open_disconnects_and_cleans_up(self):
        bluez, device, _tx, _rx = self.setup_bluez()
        bluez.objects.return_value = {device: {DEVICE: {"ServicesResolved": True}}}
        transport = BluetoothTransport(bluez, lambda _data: None, lambda _reason: None)
        with self.assertRaisesRegex(RuntimeError, "No NIIMBOT"):
            transport.open(device)
        self.assertIsNone(transport.device)
        bluez.call.assert_any_call(device, DEVICE, "Disconnect", timeout=5000)

    def test_prefers_known_combined_channel_over_unrelated_write_only_characteristic(self):
        bluez, device, tx, _rx = self.setup_bluez()
        objects = bluez.objects.return_value
        other = device + "/service001/char999"
        objects[other] = {
            CHARACTERISTIC: {
                "Service": device + "/service001",
                "Flags": ["notify", "write-without-response"],
                "UUID": CHANNEL_UUID,
            }
        }
        objects[tx][CHARACTERISTIC]["Flags"] = ["write-without-response"]
        transport = BluetoothTransport(bluez, lambda _data: None, lambda _reason: None)
        transport.open(device)
        self.assertEqual(transport.channel, other)
        self.assertEqual(transport.notify_channel, other)

    def test_link_failure_reports_stage_and_never_writes_or_pairs(self):
        bluez, device, _tx, _rx = self.setup_bluez()

        def call(_path, _interface, method, *args, **kwargs):
            if method == "Connect":
                raise RuntimeError("link timeout")

        bluez.call.side_effect = call
        progress = []
        transport = BluetoothTransport(bluez, lambda _data: None, lambda _reason: None, progress.append)
        with self.assertRaisesRegex(RuntimeError, "before GATT service discovery.*link timeout"):
            transport.open(device)
        self.assertEqual([call.args[2] for call in bluez.call.call_args_list], ["Connect", "Disconnect"])
        self.assertEqual(len(progress), 2)

    def test_transient_local_abort_retries_once_then_resolves_services(self):
        bluez, device, _tx, _rx = self.setup_bluez()
        attempts = []

        def call(_path, _interface, method, *args, **kwargs):
            if method == "Connect":
                attempts.append(method)
                if len(attempts) == 1:
                    raise RuntimeError("org.bluez.Error.Failed: le-connection-abort-by-local")

        bluez.call.side_effect = call
        progress = []
        transport = BluetoothTransport(bluez, lambda _data: None, lambda _reason: None, progress.append)
        with patch("niimstudio.bluetooth.time.sleep"):
            transport.open(device)
        self.assertEqual(len(attempts), 2)
        self.assertTrue(any("Retrying once without pairing" in message for message in progress))
        bluez.start_connection_scan.assert_called_once_with(device)
        bluez.stop_scan.assert_called_once()

    def test_transient_retry_is_bounded_and_authentication_is_not_retried(self):
        for error, expected in [("le-connection-abort-by-local", 2), ("AuthenticationRejected", 1)]:
            bluez, device, _tx, _rx = self.setup_bluez()

            def call(_path, _interface, method, *args, **kwargs):
                if method == "Connect":
                    raise RuntimeError(error)

            bluez.call.side_effect = call
            transport = BluetoothTransport(bluez, lambda _data: None, lambda _reason: None)
            with patch("niimstudio.bluetooth.time.sleep"), self.assertRaisesRegex(RuntimeError, "before GATT"):
                transport.open(device)
            self.assertEqual(sum(call.args[2] == "Connect" for call in bluez.call.call_args_list), expected)
            self.assertFalse(
                any(call.args[2] in ("Pair", "WriteValue", "RemoveDevice") for call in bluez.call.call_args_list)
            )
            bluez.stop_scan.assert_called_once()

    def test_scan_ownership_is_shared_between_chooser_and_connection(self):
        bluez = BlueZ.__new__(BlueZ)
        bluez.discovery_owners = {}
        bluez.le_filters = set()
        bluez.call = MagicMock()
        adapter = "/org/bluez/hci0"
        bluez.acquire_scan(adapter, le_only=True)
        bluez.acquire_scan(adapter)
        self.assertEqual(sum(call.args[2] == "StartDiscovery" for call in bluez.call.call_args_list), 1)
        bluez.stop_scan([adapter])
        self.assertFalse(any(call.args[2] == "StopDiscovery" for call in bluez.call.call_args_list))
        bluez.stop_scan([adapter])
        bluez.call.assert_any_call(adapter, ADAPTER, "StopDiscovery")
        self.assertEqual(bluez.discovery_owners, {})
        self.assertEqual(bluez.le_filters, set())
        before = bluez.call.call_count
        bluez.stop_scan([adapter])
        self.assertEqual(bluez.call.call_count, before)

    def test_failed_scan_restores_filter_without_stopping_someone_elses_scan(self):
        bluez = BlueZ.__new__(BlueZ)
        bluez.discovery_owners = {}
        bluez.le_filters = set()

        def call(_path, _interface, method, *args, **kwargs):
            if method == "StartDiscovery":
                raise RuntimeError("scan failed")

        bluez.call = MagicMock(side_effect=call)
        with self.assertRaisesRegex(RuntimeError, "scan failed"):
            bluez.acquire_scan("/adapter", le_only=True)
        self.assertEqual(bluez.discovery_owners, {})
        self.assertEqual(bluez.le_filters, set())
        self.assertFalse(any(call.args[2] == "StopDiscovery" for call in bluez.call.call_args_list))
        self.assertEqual(sum(call.args[2] == "SetDiscoveryFilter" for call in bluez.call.call_args_list), 2)

    def test_connection_scan_waits_for_fresh_target_advertisement_and_unsubscribes(self):
        bluez = BlueZ.__new__(BlueZ)
        bluez.bus = MagicMock()
        bluez.bus.signal_subscribe.return_value = 7
        bluez.objects = MagicMock(return_value={"/target": {DEVICE: {"Adapter": "/adapter"}}})
        bluez.acquire_scan = MagicMock()
        with patch("niimstudio.bluetooth.threading.Event") as event:
            self.assertEqual(bluez.start_connection_scan("/target"), ["/adapter"])
            event.return_value.wait.assert_called_once_with(5)
            callback = bluez.bus.signal_subscribe.call_args.args[-1]
            callback(None, None, "/target", None, None, (DEVICE, {"Connected": False}, []))
            event.return_value.set.assert_not_called()
            callback(None, None, "/target", None, None, (DEVICE, {"RSSI": -50}, []))
            event.return_value.set.assert_called_once()
        bluez.acquire_scan.assert_called_once_with("/adapter", le_only=True)
        bluez.bus.signal_unsubscribe.assert_called_once_with(7)

    def test_service_discovery_has_a_deadline(self):
        bluez, device, _tx, _rx = self.setup_bluez()
        bluez.objects.return_value = {device: {DEVICE: {"ServicesResolved": False}}}
        transport = BluetoothTransport(bluez, lambda _data: None, lambda _reason: None)
        with patch("niimstudio.bluetooth.time.monotonic", side_effect=[0, 21]):
            with self.assertRaises(TimeoutError):
                transport.open(device)

    def test_variant_and_discovery_filter(self):
        self.assertEqual(
            unpack(GLib.Variant("(aya{sv})", ([1, 2], {"mtu": GLib.Variant("q", 23)}))), [[1, 2], {"mtu": 23}]
        )
        self.assertTrue(is_printer({"Name": "B1_PRO-123"}))
        self.assertTrue(is_printer({"Name": "Unusual printer", "UUIDs": [SERVICE_UUID]}))
        self.assertFalse(is_printer({"Name": "Keyboard"}))

    def test_classic_entry_is_rejected_without_connecting_or_disconnecting(self):
        bluez, device, _tx, _rx = self.setup_bluez()
        bluez.objects.return_value = {device: {DEVICE: {"UUIDs": [SERIAL_PORT_UUID]}}}
        transport = BluetoothTransport(bluez, lambda _data: None, lambda _reason: None)
        with self.assertRaisesRegex(RuntimeError, "classic Bluetooth"):
            transport.open(device)
        bluez.call.assert_not_called()

    def test_unknown_and_dual_mode_entries_are_not_assumed_classic_only(self):
        self.assertFalse(classic_only({}))
        self.assertFalse(classic_only({"UUIDs": [SERIAL_PORT_UUID, SERVICE_UUID]}))
        self.assertTrue(classic_only({"UUIDs": [SERIAL_PORT_UUID]}))

    def test_discovery_hides_classic_unless_show_all_but_keeps_unknown_ble(self):
        from types import SimpleNamespace

        from niimstudio.bluetooth import BlueZ

        bluez = SimpleNamespace(
            objects=lambda: {
                "/classic": {DEVICE: {"Name": "B1 Pro", "UUIDs": [SERIAL_PORT_UUID]}},
                "/ble": {DEVICE: {"Name": "B1 Pro"}},
            }
        )
        devices = {item["id"]: item for item in BlueZ.discover(bluez)}
        self.assertNotIn("/classic", devices)
        self.assertFalse(devices["/ble"]["classic_only"])
        all_devices = {item["id"]: item for item in BlueZ.discover(bluez, show_all=True)}
        self.assertTrue(all_devices["/classic"]["classic_only"])
