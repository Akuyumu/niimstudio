import json
import unittest
from types import MethodType, SimpleNamespace
from unittest.mock import Mock, patch

from niimstudio.app import StudioApplication


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.app = SimpleNamespace(
            smoke=False,
            editor_ready=True,
            close_pending=False,
            close_prompt=False,
            close_generation=0,
            close_timer=None,
            printing=False,
            window=Mock(),
            webview=Mock(),
            close_save_failed=Mock(),
        )
        self.app.prepare_close = MethodType(StudioApplication.prepare_close, self.app)
        self.timer = patch("niimstudio.app.GLib.timeout_add", return_value=123).start()
        self.remove = patch("niimstudio.app.GLib.source_remove").start()
        self.addCleanup(patch.stopall)

    def complete(self, outcome):
        self.app.webview.call_async_javascript_function_finish.return_value.to_string.return_value = outcome
        callback = self.app.webview.call_async_javascript_function.call_args.args[-1]
        callback(self.app.webview, Mock())

    def test_normal_close_flushes_before_destroying_without_prompt(self):
        with patch("niimstudio.app.Adw.AlertDialog") as dialog:
            self.assertTrue(StudioApplication.confirm_close(self.app, self.app.window))
            dialog.assert_not_called()
        self.app.window.destroy.assert_not_called()
        self.complete("true")
        self.app.window.destroy.assert_called_once()
        self.app.close_save_failed.assert_not_called()

    def test_close_before_editor_mount_has_nothing_to_flush(self):
        self.app.prepare_close()
        self.complete("unavailable")
        self.app.window.destroy.assert_called_once()
        self.app.close_save_failed.assert_not_called()

    def test_save_failure_keeps_window(self):
        self.app.prepare_close()
        self.complete("false")
        self.app.window.destroy.assert_not_called()
        self.app.close_save_failed.assert_called_once()

    def test_save_timeout_keeps_window(self):
        self.app.prepare_close()
        self.timer.call_args.args[1]()
        self.app.window.destroy.assert_not_called()
        self.app.close_save_failed.assert_called_once()

    def test_duplicate_close_does_not_start_another_flush(self):
        StudioApplication.confirm_close(self.app, self.app.window)
        StudioApplication.confirm_close(self.app, self.app.window)
        self.app.webview.call_async_javascript_function.assert_called_once()

    def test_late_response_cannot_complete_a_retried_close(self):
        self.app.prepare_close()
        previous = self.app.webview.call_async_javascript_function.call_args.args[-1]
        self.timer.call_args.args[1]()
        self.app.prepare_close()
        previous(self.app.webview, Mock())
        self.app.window.destroy.assert_not_called()
        self.assertTrue(self.app.close_pending)

    def test_printing_still_requires_confirmation(self):
        self.app.printing = True
        with patch("niimstudio.app.Adw.AlertDialog") as dialog:
            StudioApplication.confirm_close(self.app, self.app.window)
            dialog.return_value.present.assert_called_once_with(self.app.window)
            self.app.webview.call_async_javascript_function.assert_not_called()

    def test_close_before_editor_load_does_not_wait_for_javascript(self):
        self.app.editor_ready = False
        self.app.prepare_close()
        self.app.window.destroy.assert_called_once()
        self.app.webview.call_async_javascript_function.assert_not_called()


class ReconnectPreferenceTests(unittest.TestCase):
    def request(self, enabled, save_error=None):
        app = SimpleNamespace(smoke=False, history=Mock(auto_reconnect=True), reply=Mock(), send=Mock())
        app.history.save.side_effect = save_error
        value = Mock()
        value.to_json.return_value = json.dumps({"id": 7, "op": "setReconnectPolicy", "enabled": enabled})
        StudioApplication.on_message(app, None, value)
        return app

    def test_settings_save_reconnect_preference_without_touching_the_printer(self):
        app = self.request(False)
        self.assertFalse(app.history.auto_reconnect)
        app.history.save.assert_called_once()
        app.reply.assert_called_once_with(7, {"enabled": False})
        app.send.assert_called_once_with({"event": "reconnect-policy", "enabled": False})

    def test_failed_preference_save_restores_previous_value(self):
        app = self.request(False, OSError("full disk"))
        self.assertTrue(app.history.auto_reconnect)
        app.send.assert_not_called()
        self.assertIsInstance(app.reply.call_args.kwargs["error"], OSError)

    def test_preference_requires_a_boolean(self):
        app = self.request("false")
        app.history.save.assert_not_called()
        app.send.assert_not_called()
        self.assertIsInstance(app.reply.call_args.kwargs["error"], ValueError)
