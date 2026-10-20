import unittest
from unittest.mock import MagicMock, patch

from gi.repository import GLib
from niimstudio.pairing import PairingAgent


class PairingTests(unittest.TestCase):
    def make_agent(self):
        bluez = MagicMock()
        agent = PairingAgent(bluez, MagicMock())
        agent.device = "/org/bluez/hci0/dev_00_11_22_33_44_55"
        return agent, bluez

    def test_agent_is_scoped_and_does_not_replace_desktop_agent(self):
        agent, bluez = self.make_agent()
        methods = [call.args[2] for call in bluez.call.call_args_list]
        self.assertEqual(methods, ["RegisterAgent"])
        agent.close()
        self.assertEqual(bluez.call.call_args.args[2], "UnregisterAgent")

    def test_requests_for_unselected_devices_are_rejected(self):
        agent, _bluez = self.make_agent()
        invocation = MagicMock()
        agent._method(None, None, None, None, "RequestAuthorization", GLib.Variant("(o)", ("/other",)), invocation)
        self.assertEqual(invocation.return_dbus_error.call_args.args[0], "org.bluez.Error.Rejected")

    def respond(self, method, text="1234", selected="pair", extra=()):
        agent, _bluez = self.make_agent()
        invocation = MagicMock()
        with patch("niimstudio.pairing.Gtk.Entry") as entry, patch("niimstudio.pairing.Adw.AlertDialog") as dialog:
            entry.return_value.get_text.return_value = text
            parameters = GLib.Variant("(ou)" if extra else "(o)", (agent.device, *extra))
            agent._method(None, None, None, None, method, parameters, invocation)
            callback = dialog.return_value.connect.call_args.args[1]
            callback(dialog.return_value, selected)
        return invocation

    def test_pin_response_is_returned_as_string(self):
        invocation = self.respond("RequestPinCode", "0000")
        self.assertEqual(invocation.return_value.call_args.args[0].unpack(), ("0000",))

    def test_numeric_passkey_is_returned_as_uint(self):
        invocation = self.respond("RequestPasskey", "001234")
        self.assertEqual(invocation.return_value.call_args.args[0].unpack(), (1234,))

    def test_invalid_passkey_is_rejected(self):
        invocation = self.respond("RequestPasskey", "1234567")
        self.assertEqual(invocation.return_dbus_error.call_args.args[0], "org.bluez.Error.Rejected")

    def test_rejecting_confirmation_cancels_pairing(self):
        invocation = self.respond("RequestConfirmation", selected="cancel", extra=(123456,))
        self.assertEqual(invocation.return_dbus_error.call_args.args[0], "org.bluez.Error.Canceled")
