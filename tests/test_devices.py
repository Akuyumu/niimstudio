import unittest
from types import MethodType, SimpleNamespace
from unittest.mock import Mock, patch

from niimstudio.app import StudioApplication
from niimstudio.connection_errors import connection_tip
from niimstudio.devices import DeviceChooser, offer_pairing


class DeviceFeedbackTests(unittest.TestCase):
    def chooser(self):
        chooser = SimpleNamespace(
            closed=False,
            failure="",
            busy=True,
            usb=Mock(),
            ble=Mock(),
            status=Mock(),
            authentication_failures=set(),
            connecting_device=None,
            refresh=Mock(),
        )
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

    def test_pair_is_not_a_default_duplicate_of_connect(self):
        device = {"kind": "bluetooth", "id": "/ble", "paired": False}
        self.assertFalse(offer_pairing(device, set()))
        self.assertTrue(offer_pairing(device, {"/ble"}))
        self.assertFalse(offer_pairing({**device, "paired": True}, {"/ble"}))
        self.assertFalse(offer_pairing({**device, "classic_only": True}, {"/ble"}))
        self.assertFalse(offer_pairing({**device, "kind": "serial"}, {"/ble"}))

    def test_only_explicit_auth_failure_exposes_pair_on_that_device(self):
        chooser = self.chooser()
        chooser.connecting_device = "/ble"
        for error in ("Timeout was reached", "le-connection-abort-by-local", "AuthenticationCanceled"):
            DeviceChooser.connection_failed(chooser, error)
            self.assertEqual(chooser.authentication_failures, set())
        DeviceChooser.connection_failed(chooser, "org.bluez.Error.AuthenticationFailed")
        self.assertEqual(chooser.authentication_failures, {"/ble"})
        chooser.refresh.assert_called_once()

    def test_failed_preference_save_restores_history_and_switch(self):
        chooser = self.chooser()
        chooser.history = Mock(auto_reconnect=True)
        chooser.history.save.side_effect = OSError("full disk")
        chooser.policy_changed = Mock()
        chooser.reconnect_handler = 9
        switch = Mock()
        switch.get_active.return_value = False
        DeviceChooser.reconnect_changed(chooser, switch, None)
        self.assertTrue(chooser.history.auto_reconnect)
        switch.set_active.assert_called_once_with(True)
        switch.handler_block.assert_called_once_with(9)
        switch.handler_unblock.assert_called_once_with(9)
        chooser.policy_changed.assert_not_called()
        self.assertIn("previous preference was kept", chooser.failure)

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
        chooser.signature = repr(([], [], []))
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
            connect_request=None,
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
        self.app.open_device = MethodType(StudioApplication.open_device, self.app)
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

    def test_cancel_connection_replies_both_requests_and_closes_pending_transport(self):
        app = SimpleNamespace(
            smoke=False,
            connecting=True,
            chooser=None,
            transport=Mock(),
            connect_request=321,
            generation=4,
            run_task=Mock(),
            reply=Mock(),
        )
        StudioApplication.cancel_connection(app, 400)
        self.assertFalse(app.connecting)
        self.assertIsNone(app.connect_request)
        self.assertIsNone(app.transport)
        self.assertEqual(app.generation, 5)
        app.reply.assert_any_call(321, cancelled=True)
        app.reply.assert_any_call(400, {"cancelled": True})
        app.run_task.assert_called_once()

    def test_cancel_connection_does_not_disturb_manual_chooser(self):
        app = SimpleNamespace(connecting=True, chooser=Mock(), transport=None, connect_request=321, reply=Mock())
        StudioApplication.cancel_connection(app, 400)
        app.reply.assert_called_once_with(400, {"cancelled": False})
        self.assertTrue(app.connecting)

    def test_cancelled_attempt_ignores_late_selected_device(self):
        app = SimpleNamespace(
            smoke=False,
            connecting=False,
            chooser=None,
            transport=None,
            connect_request=None,
            generation=0,
            window=Mock(),
            history=Mock(),
            reply=Mock(),
            run_task=Mock(),
            send=Mock(),
            ensure_bluez=Mock(),
        )
        app.open_device = MethodType(StudioApplication.open_device, app)
        with patch("niimstudio.app.BluetoothTransport") as transport:
            StudioApplication.choose_printer(app, 500, automatic=True)
            _resolve, selected, _unavailable = app.run_task.call_args.args
            StudioApplication.cancel_connection(app, 501)
            selected({"id": "/ble", "name": "B1 Pro", "kind": "bluetooth"})
            transport.assert_not_called()
        self.assertFalse(app.connecting)
        self.assertIsNone(app.transport)

    def test_choose_device_keeps_current_transport_and_stores_pending_selection(self):
        existing = Mock()
        chooser = Mock(closed=False)
        app = SimpleNamespace(
            smoke=False,
            connecting=False,
            chooser=None,
            transport=existing,
            pending_device=None,
            reply=Mock(),
            run_task=Mock(),
            history=Mock(),
            window=Mock(),
            send=Mock(),
            ensure_bluez=Mock(),
        )
        device = {"kind": "bluetooth", "id": "/ble", "name": "B1 Pro", "address": "private"}
        with patch("niimstudio.app.DeviceChooser", return_value=chooser) as make:
            StudioApplication.choose_printer_only(app, 600)
            selected = make.call_args.args[3]
            selected(device)
        self.assertIs(app.transport, existing)
        self.assertIsNone(app.chooser)
        self.assertFalse(app.connecting)
        self.assertEqual(app.pending_device, {"kind": "bluetooth", "id": "/ble", "name": "B1 Pro"})
        app.reply.assert_called_once_with(600, {"device": app.pending_device})
        chooser.connection_succeeded.assert_called_once()

    def test_connect_pending_uses_native_selection_and_rejects_an_active_transport(self):
        device = {"kind": "bluetooth", "id": "/ble", "name": "B1 Pro"}
        app = SimpleNamespace(
            smoke=False,
            connecting=False,
            chooser=None,
            transport=None,
            connect_request=None,
            pending_device=device,
            generation=0,
            reply=Mock(),
            run_task=Mock(),
            send=Mock(),
            ensure_bluez=Mock(),
            selected_device=None,
        )
        app.open_device = MethodType(StudioApplication.open_device, app)
        with patch("niimstudio.app.BluetoothTransport", return_value=Mock()) as transport:
            StudioApplication.connect_pending(app, 601)
        self.assertTrue(app.connecting)
        self.assertEqual(app.connect_request, 601)
        self.assertIsNone(app.pending_device)
        transport.assert_called_once()
        app.run_task.assert_called_once()

        blocked = SimpleNamespace(connecting=False, chooser=None, transport=Mock(), pending_device=device, reply=Mock())
        StudioApplication.connect_pending(blocked, 602)
        blocked.reply.assert_called_once_with(
            602, error="Disconnect the current printer before connecting the selected one"
        )
        self.assertEqual(blocked.pending_device, device)
