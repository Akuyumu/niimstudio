"""An application-scoped BlueZ agent; never replaces Omarchy's default agent."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk

AGENT_PATH = "/io/github/niimstudio/Agent"
AGENT_XML = """<node><interface name="org.bluez.Agent1">
<method name="Release"/>
<method name="Cancel"/>
<method name="RequestPinCode"><arg type="o" direction="in"/><arg type="s" direction="out"/></method>
<method name="RequestPasskey"><arg type="o" direction="in"/><arg type="u" direction="out"/></method>
<method name="DisplayPinCode"><arg type="o" direction="in"/><arg type="s" direction="in"/></method>
<method name="DisplayPasskey"><arg type="o" direction="in"/><arg type="u" direction="in"/><arg type="q" direction="in"/></method>
<method name="RequestConfirmation"><arg type="o" direction="in"/><arg type="u" direction="in"/></method>
<method name="RequestAuthorization"><arg type="o" direction="in"/></method>
<method name="AuthorizeService"><arg type="o" direction="in"/><arg type="s" direction="in"/></method>
</interface></node>"""


class PairingAgent:
    def __init__(self, bluez, parent):
        self.bluez = bluez
        self.parent = parent
        self.device = None
        self.dialog = None
        self.pending = None
        self.registration = bluez.bus.register_object(
            AGENT_PATH,
            Gio.DBusNodeInfo.new_for_xml(AGENT_XML).interfaces[0],
            self._method,
            None,
            None,
        )
        try:
            bluez.call(
                "/org/bluez",
                "org.bluez.AgentManager1",
                "RegisterAgent",
                GLib.Variant("(os)", (AGENT_PATH, "KeyboardDisplay")),
            )
        except Exception:
            bluez.bus.unregister_object(self.registration)
            raise

    def _method(self, connection, sender, path, interface, method, parameters, invocation):
        args = parameters.unpack()
        if method in ("Release", "Cancel"):
            self.cancel()
            invocation.return_value(None)
            return
        if not args or args[0] != self.device:
            invocation.return_dbus_error("org.bluez.Error.Rejected", "No pairing was requested for this device")
            return
        if method == "AuthorizeService":
            invocation.return_value(None)
            return
        self.cancel()
        self.pending = invocation
        entry = None
        if method in ("RequestPinCode", "RequestPasskey"):
            title = "Enter the printer’s pairing code"
            body = "Use the PIN supplied with your printer. NiimStudio does not guess PINs."
            entry = Gtk.Entry(placeholder_text="PIN or passkey", activates_default=True)
            if method == "RequestPasskey":
                entry.set_input_purpose(Gtk.InputPurpose.DIGITS)
                entry.set_max_length(6)
        elif method in ("RequestConfirmation", "DisplayPasskey", "DisplayPinCode"):
            title = "Confirm Bluetooth pairing"
            code = f"{args[1]:06d}" if method != "DisplayPinCode" else args[1]
            body = f"Check this code on your printer: {code}"
        else:
            title = "Allow Bluetooth pairing?"
            body = "Only continue if this is the printer you selected."

        dialog = Adw.AlertDialog(heading=title, body=body)
        self.dialog = dialog
        if entry:
            dialog.set_extra_child(entry)
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("pair", "Pair")
        dialog.set_response_appearance("pair", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("pair")
        dialog.set_close_response("cancel")

        def response(_dialog, selected):
            current = self.pending
            self.pending = None
            self.dialog = None
            if current is None:
                return
            if selected != "pair":
                current.return_dbus_error("org.bluez.Error.Canceled", "Pairing canceled")
            elif method == "RequestPinCode":
                text = entry.get_text().strip()
                if not text or len(text) > 16:
                    current.return_dbus_error("org.bluez.Error.Rejected", "PIN must contain 1–16 characters")
                else:
                    current.return_value(GLib.Variant("(s)", (text,)))
            elif method == "RequestPasskey":
                text = entry.get_text().strip()
                if not text.isascii() or not text.isdigit() or len(text) > 6:
                    current.return_dbus_error("org.bluez.Error.Rejected", "Passkey must be 1–6 digits")
                else:
                    current.return_value(GLib.Variant("(u)", (int(text),)))
            else:
                current.return_value(None)

        dialog.connect("response", response)
        dialog.present(self.parent)

    def cancel(self):
        if self.pending:
            self.pending.return_dbus_error("org.bluez.Error.Canceled", "Pairing canceled")
            self.pending = None
        if self.dialog:
            self.dialog.close()
            self.dialog = None

    def close(self):
        self.cancel()
        try:
            self.bluez.call(
                "/org/bluez", "org.bluez.AgentManager1", "UnregisterAgent", GLib.Variant("(o)", (AGENT_PATH,))
            )
        except GLib.Error:
            pass
        self.bluez.bus.unregister_object(self.registration)
