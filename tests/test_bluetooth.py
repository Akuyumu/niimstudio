import unittest
from unittest.mock import MagicMock, patch

from gi.repository import GLib
from niimstudio.bluetooth import CHARACTERISTIC, DEVICE, SERVICE_UUID, BluetoothTransport, is_printer, unpack


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
