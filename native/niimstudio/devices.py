"""A focused GTK printer chooser with bounded discovery and optional pairing."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk

from .bluetooth import DEVICE
from .pairing import PairingAgent
from .serial_transport import discover_serial


class DeviceChooser(Adw.Window):
    def __init__(
        self, parent, bluez, run_task, on_selected, on_cancel, history=None, policy_changed=None, hardware_enabled=True
    ):
        super().__init__(
            title="Select a printer", transient_for=parent, modal=True, default_width=620, default_height=580
        )
        self.bluez = bluez
        self.hardware_enabled = hardware_enabled
        self.run_task = run_task
        self.on_selected = on_selected
        self.on_cancel = on_cancel
        self.scan_owned = []
        self.closed = False
        self.busy = False
        self.refreshing = False
        self.scan_pending = False
        self.agent = None
        self.rows = []
        self.signature = None
        self.connect("close-request", self._closed)

        layout = Adw.ToolbarView()
        header = Adw.HeaderBar()
        layout.add_top_bar(header)
        page = Adw.PreferencesPage()
        self.message = Adw.PreferencesGroup(
            title="Your label printers",
            description="Connect over USB or Bluetooth LE. Keep the printer on and close other printing apps.",
        )
        self.message.set_margin_top(12)
        self.show_all = Gtk.CheckButton(label="Show all Bluetooth devices")
        self.show_all.connect("toggled", lambda _button: self.refresh())
        self.message.add(self.show_all)
        if history is not None:
            reconnect = Gtk.Switch(active=history.auto_reconnect, valign=Gtk.Align.CENTER)
            row = Adw.ActionRow(
                title="Reconnect automatically", subtitle="Try the last linked printer when it becomes available"
            )
            row.add_suffix(reconnect)
            row.set_activatable_widget(reconnect)
            self.message.add(row)

            def preference_changed(switch, _property):
                history.auto_reconnect = switch.get_active()
                try:
                    history.save()
                    if policy_changed:
                        policy_changed(history.auto_reconnect)
                except OSError as error:
                    self.set_status(f"Could not save reconnect preference: {error}")

            reconnect.connect("notify::active", preference_changed)
        scan = Gtk.Button(label="Scan for printers", icon_name="view-refresh-symbolic")
        scan.connect("clicked", lambda _button: self.start_scan())
        scan.set_sensitive(hardware_enabled)
        self.message.set_header_suffix(scan)
        page.add(self.message)
        self.usb = Adw.PreferencesGroup(title="USB", description="USB serial devices detected on this computer")
        self.ble = Adw.PreferencesGroup(
            title="Bluetooth LE", description="Pairing is optional for many NIIMBOT printers."
        )
        page.add(self.usb)
        page.add(self.ble)
        self.status = Adw.PreferencesGroup(description="Checking connected devices…")
        page.add(self.status)
        layout.set_content(page)
        self.set_content(layout)
        self.timer = GLib.timeout_add_seconds(2, self.refresh)
        self.refresh()

    def set_status(self, text):
        if not self.closed:
            self.status.set_description(text)

    def refresh(self):
        if self.closed:
            return GLib.SOURCE_REMOVE
        if self.busy or self.refreshing:
            return GLib.SOURCE_CONTINUE
        self.refreshing = True
        show_all = self.show_all.get_active()

        def discover():
            usb = discover_serial()
            try:
                return usb, self.bluez.discover(show_all) if self.bluez else [], None
            except Exception as error:
                return usb, [], str(error)

        def ready(result):
            self.refreshing = False
            if self.closed:
                return
            usb, ble, error = result
            signature = repr((usb, ble))
            if signature != self.signature:
                self.signature = signature
                for group, row in self.rows:
                    group.remove(row)
                self.rows = []
                for device in [*usb, *ble]:
                    group = self.usb if device["kind"] == "serial" else self.ble
                    subtitle = (
                        device["id"]
                        if device["kind"] == "serial"
                        else (f"{device['address']} · {'Paired' if device['paired'] else 'Not paired'}")
                    )
                    row = Adw.ActionRow(title=device["name"], subtitle=subtitle, use_markup=False)
                    if device["kind"] == "bluetooth" and not device["paired"]:
                        pair = Gtk.Button(label="Pair", valign=Gtk.Align.CENTER)
                        pair.set_sensitive(self.hardware_enabled)
                        pair.connect("clicked", lambda _button, d=device: self.pair(d))
                        row.add_suffix(pair)
                    connect = Gtk.Button(label="Connect", valign=Gtk.Align.CENTER)
                    connect.set_sensitive(self.hardware_enabled)
                    connect.add_css_class("suggested-action")
                    connect.connect("clicked", lambda _button, d=device: self.select(d))
                    row.add_suffix(connect)
                    group.add(row)
                    self.rows.append((group, row))
            if error:
                self.set_status(f"Bluetooth unavailable: {error}. USB is still usable.")
            elif not usb and not ble:
                self.set_status(
                    "No printers found yet. Plug in a USB data cable or scan for a nearby Bluetooth printer."
                )
            elif not self.scan_owned and not self.scan_pending:
                self.set_status("Choose a printer, or scan to find nearby Bluetooth devices.")

        self.run_task(discover, ready, lambda error: (setattr(self, "refreshing", False), self.set_status(str(error))))
        return GLib.SOURCE_CONTINUE

    def start_scan(self):
        if not self.hardware_enabled:
            return
        if self.busy or self.scan_owned or self.scan_pending:
            return
        if self.bluez is None:
            self.set_status("Bluetooth is unavailable. Check that the BlueZ service is running.")
            return
        self.scan_pending = True
        self.set_status("Scanning for 25 seconds… Turn your printer on and keep it nearby.")

        def started(owned):
            self.scan_pending = False
            if self.closed:
                self.run_task(lambda: self.bluez.stop_scan(owned))
                return
            self.scan_owned = owned
            GLib.timeout_add_seconds(25, self.stop_scan)
            self.refresh()

        def failed(error):
            self.scan_pending = False
            self.set_status(str(error))

        self.run_task(self.bluez.start_scan, started, failed)

    def stop_scan(self):
        owned, self.scan_owned = self.scan_owned, []
        if owned:
            self.run_task(lambda: self.bluez.stop_scan(owned))
            self.set_status("Scan complete. Select a printer or scan again.")
        return GLib.SOURCE_REMOVE

    def pair(self, device):
        if not self.hardware_enabled:
            return
        if self.busy:
            return
        try:
            if self.agent is None:
                self.agent = PairingAgent(self.bluez, self)
            self.agent.device = device["id"]
        except Exception as error:
            self.set_status(f"Could not start pairing: {error}")
            return
        self.busy = True
        self.set_status(f"Pairing with {device['name']}… Respond to any pairing-code prompt.")

        def finished(_result):
            self.busy = False
            self.agent.cancel()
            self.agent.device = None
            self.set_status("Paired. You can now connect to the printer.")
            self.refresh()

        def failed(error):
            self.busy = False
            self.agent.cancel()
            self.agent.device = None
            self.set_status(f"Pairing failed: {error}. Some BLE printers work with Connect without pairing.")

        self.run_task(lambda: self.bluez.call(device["id"], DEVICE, "Pair", timeout=60000), finished, failed)

    def select(self, device):
        if not self.hardware_enabled:
            return
        if self.busy:
            return
        self.on_cancel = None
        self._cleanup()
        self.close()
        self.on_selected(device)

    def _cleanup(self):
        if self.closed:
            return
        self.closed = True
        GLib.source_remove(self.timer)
        self.stop_scan()
        if self.agent:
            if self.busy and self.agent.device:
                # Async cancel must not queue behind the pending Pair call.
                self.bluez.bus.call(
                    "org.bluez", self.agent.device, DEVICE, "CancelPairing", None, None, 0, 5000, None, None
                )
            self.agent.close()

    def _closed(self, _window):
        self._cleanup()
        if self.on_cancel:
            self.on_cancel()
            self.on_cancel = None
        return False
