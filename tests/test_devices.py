import unittest
from types import MethodType, SimpleNamespace
from unittest.mock import Mock, patch

from niimstudio.app import StudioApplication
from niimstudio.connection_errors import connection_tip
from niimstudio.devices import DeviceChooser


class DeviceFeedbackTests(unittest.TestCase):
    def chooser(self):
        chooser = SimpleNamespace(closed=False, failure="", busy=True, usb=Mock(), ble=Mock(), status=Mock())
        chooser.set_status = MethodType(DeviceChooser.set_status, chooser)
        chooser.show_failure = MethodType(DeviceChooser.show_failure, chooser)
        return chooser

    def test_failure_keeps_retry_enabled_and_preserves_cause_and_tip(self):
        chooser = self.chooser()
        DeviceChooser.connection_failed(chooser, "org.bluez.Error.AuthenticationRejected")
        self.assertFalse(chooser.busy)
        chooser.ble.set_sensitive.assert_called_with(True)
        self.assertIn("Connection failed", chooser.failure)
        self.assertIn("AuthenticationRejected", chooser.failure)
        self.assertIn("Try Pair", chooser.failure)
        self.assertNotIn("0000", chooser.failure)

    def test_pairing_not_supported_suggests_connect_without_pairing(self):
        self.assertIn("without pairing", connection_tip("org.bluez.Error.NotSupported"))

    def test_classic_tip_explains_pairing_will_not_enable_ble(self):
        self.assertIn("Pairing the classic entry will not enable BLE", connection_tip("classic Serial Port"))

    def test_connection_selection_keeps_window_for_result(self):
        chooser = self.chooser()
        chooser.hardware_enabled = True
        chooser.busy = False
        chooser.on_selected = Mock()
        chooser.close = Mock()
        DeviceChooser.select(chooser, {"id": "/ble", "kind": "bluetooth", "name": "B1 Pro"})
        self.assertTrue(chooser.busy)
        chooser.close.assert_not_called()
        chooser.on_selected.assert_called_once()
        chooser.ble.set_sensitive.assert_called_with(False)

    def test_refresh_does_not_replace_a_failure_with_generic_instructions(self):
        chooser = self.chooser()
        chooser.failure = "Pairing failed: fixture. Try Connect without pairing."
        chooser.busy = False
        chooser.refreshing = False
        chooser.show_all = Mock()
        chooser.signature = repr(([], []))
        chooser.scan_owned = []
        chooser.scan_pending = False
        chooser.run_task = Mock()
        DeviceChooser.refresh(chooser)
        ready = chooser.run_task.call_args.args[1]
        ready(([], [], None))
        chooser.status.set_description.assert_called_with(chooser.failure)

    def test_cancel_pairing_bypasses_the_blocked_worker_and_keeps_ui_busy_until_completion(self):
        chooser = self.chooser()
        chooser.agent = Mock(device="/ble")
        chooser.bluez = Mock()
        chooser.cancel_pair_button = Mock()
        chooser.pair_cancel_requested = False
        DeviceChooser.cancel_pairing(chooser)
        self.assertTrue(chooser.pair_cancel_requested)
        self.assertTrue(chooser.busy)
        self.assertEqual(chooser.bluez.bus.call.call_args.args[3], "CancelPairing")
        DeviceChooser.finish_pairing(chooser, RuntimeError("Canceled"))
        self.assertFalse(chooser.busy)
        self.assertIn("Pairing canceled", chooser.failure)
        self.assertIn("without pairing", chooser.failure)
        self.assertNotIn("failed", chooser.failure)

    def test_cancel_before_queued_pair_starts_does_not_send_pair(self):
        chooser = self.chooser()
        chooser.hardware_enabled = True
        chooser.busy = False
        chooser.agent = Mock()
        chooser.bluez = Mock()
        chooser.cancel_pair_button = Mock()
        chooser.run_task = Mock()
        chooser.finish_pairing = MethodType(DeviceChooser.finish_pairing, chooser)
        DeviceChooser.pair(chooser, {"id": "/ble", "name": "B1 Pro"})
        work, finished, _failed = chooser.run_task.call_args.args
        DeviceChooser.cancel_pairing(chooser)
        work()
        finished(None)
        chooser.bluez.call.assert_not_called()
        self.assertFalse(chooser.busy)


class ConnectionAttemptTests(unittest.TestCase):
    def setUp(self):
        self.app = SimpleNamespace(
            smoke=False,
            connecting=False,
            chooser=None,
            transport=None,
            generation=0,
            window=Mock(),
            history=Mock(),
            reply=Mock(),
            run_task=Mock(),
            send=Mock(),
            ensure_bluez=Mock(),
        )
        self.device = {"id": "/ble", "name": "B1 Pro", "kind": "bluetooth"}
        self.transport = Mock()
        self.chooser = Mock(closed=False)
        with patch("niimstudio.app.DeviceChooser", return_value=self.chooser) as make:
            StudioApplication.choose_printer(self.app, 123)
            self.select = make.call_args.args[3]
            self.cancel = make.call_args.args[4]

    def start(self):
        with patch("niimstudio.app.BluetoothTransport", return_value=self.transport):
            self.select(self.device)
        return self.app.run_task.call_args.args

    def test_failed_transport_stays_in_picker_and_can_retry(self):
        _work, _opened, failed = self.start()
        failed(RuntimeError("fixture timeout"))
        self.chooser.connection_failed.assert_called_once()
        self.app.reply.assert_not_called()
        _work, opened, _failed = self.start()
        opened(None)
        self.chooser.connection_succeeded.assert_called_once()
        self.app.reply.assert_called_once_with(123, {"name": "B1 Pro", "kind": "bluetooth"})

    def test_cancel_during_open_rejects_late_success(self):
        _work, opened, _failed = self.start()
        self.cancel()
        opened(None)
        self.app.reply.assert_called_once_with(123, cancelled=True)
        self.chooser.connection_succeeded.assert_not_called()
        self.assertIsNone(self.app.transport)

    def test_cancel_during_open_rejects_late_failure(self):
        _work, _opened, failed = self.start()
        self.cancel()
        failed(RuntimeError("late failure"))
        self.app.reply.assert_called_once_with(123, cancelled=True)
        self.chooser.connection_failed.assert_not_called()
