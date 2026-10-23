"""GTK4 shell and a narrow, offline-only bridge to the bundled label editor."""

import base64
import json
import logging
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import unquote, urlsplit

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("WebKit", "6.0")
gi.require_version("Soup", "3.0")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk, Soup, WebKit  # noqa: E402

from . import __version__
from .bluetooth import BluetoothTransport, BlueZ
from .devices import DeviceChooser
from .history import DeviceHistory
from .lifecycle import enabled, mark
from .serial_transport import SerialTransport, discover_serial
from .theme import gtk_css, gtk_palette, read_palette
from .updates import fetch_latest, managed_root, run_update, updates_enabled

LOG = logging.getLogger("niimstudio")
mark("gtk_imported")
ROOT = Path(__file__).resolve().parents[2]
ORIGIN = "niimstudio://app/"
MIME_TYPES = {
    ".html": "text/html",
    ".js": "text/javascript",
    ".mjs": "text/javascript",
    ".css": "text/css",
    ".json": "application/json",
    ".webmanifest": "application/manifest+json",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
    ".woff": "font/woff",
    ".wasm": "application/wasm",
}


def asset_path(uri, root):
    parsed = urlsplit(uri)
    if parsed.scheme != "niimstudio" or parsed.netloc != "app":
        raise ValueError("Invalid application origin")
    path = (root / unquote(parsed.path).lstrip("/")).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError("Unknown application asset")
    return path


def validate_message(message):
    if not isinstance(message, dict) or type(message.get("id")) is not int or message["id"] < 1:
        raise ValueError("Invalid bridge message")
    if message.get("op") not in {
        "ready",
        "workspaceReady",
        "updateApp",
        "quit",
        "testUpdate",
        "connect",
        "chooseDevice",
        "connectPending",
        "cancelConnect",
        "disconnect",
        "write",
        "save",
        "status",
        "log",
        "remember",
        "knownDevice",
        "setReconnectPolicy",
        "testSnapshot",
        "testDismissDevices",
    }:
        raise ValueError("Unknown bridge operation")
    return message


def configure_rendering(settings):
    """A reversible, per-process fallback; never disable WebKit's sandbox."""
    mode = os.environ.get("NIIMSTUDIO_RENDERER", "auto")
    if mode == "software":
        settings.set_hardware_acceleration_policy(WebKit.HardwareAccelerationPolicy.NEVER)
    elif mode != "auto":
        LOG.warning("Unknown NIIMSTUDIO_RENDERER value; using the default renderer")
    return "software" if mode == "software" else "auto"


class StudioApplication(Adw.Application):
    def __init__(self, smoke=False):
        super().__init__(
            application_id="io.github.niimstudio.App",
            flags=Gio.ApplicationFlags.NON_UNIQUE if smoke else Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.smoke = smoke
        self.window = None
        self.chooser = None
        self.bluez = None
        self.transport = None
        self.connecting = False
        self.connect_request = None
        self.pending_device = None
        self.generation = 0
        self.shutting_down = False
        self.editor_ready = False
        self.close_pending = False
        self.close_generation = 0
        self.close_prompt = False
        self.close_timer = None
        self.update_checked = False
        self.update_started = False
        self.selected_device = None
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="niimstudio-io")
        self.palette = None
        self.theme_source = None
        self.theme_signature = None
        self.css = Gtk.CssProvider()
        self.connect("activate", self.activate_window)
        self.connect("shutdown", self.shutdown_app)

    def run_task(self, function, on_success=None, on_error=None):
        if self.shutting_down:
            return
        future = self.executor.submit(function)

        def complete(done):
            try:
                result = done.result()
            except Exception as error:
                LOG.info("Device operation failed: %s", error)
                if on_error:
                    GLib.idle_add(deliver, on_error, error)
            else:
                if on_success:
                    GLib.idle_add(deliver, on_success, result)

        def deliver(callback, value):
            if not self.shutting_down:
                callback(value)
            return GLib.SOURCE_REMOVE

        future.add_done_callback(complete)

    def activate_window(self, _app):
        if self.window:
            self.window.present()
            return
        self.window = Adw.ApplicationWindow(
            application=self, title="NiimStudio", default_width=1380, default_height=900
        )
        mark("window_created")
        self.window.connect("close-request", self.confirm_close)
        layout = Adw.ToolbarView()
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title="NiimStudio", subtitle="Local label workspace"))
        about = Gtk.Button(icon_name="help-about-symbolic", tooltip_text="About NiimStudio")
        about.connect("clicked", self.about)
        header.pack_end(about)
        layout.add_top_bar(header)
        self.window.set_content(layout)

        data = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "niimstudio"
        cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "niimstudio"
        if self.smoke:
            import tempfile

            self.smoke_dir = tempfile.TemporaryDirectory(prefix="niimstudio-smoke-")
            profile = Path(os.environ.get("NIIMSTUDIO_TEST_PROFILE", self.smoke_dir.name)).resolve()
            marker = profile / ".niimstudio-test-profile"
            unsafe = profile == data.resolve() or profile.is_relative_to(data.resolve())
            unsafe = unsafe or (profile.is_dir() and any(profile.iterdir()) and not marker.is_file())
            if unsafe:
                LOG.error("A smoke profile must be empty or marked as synthetic; never use real application data")
                self.smoke_failed = True
                self.quit()
                return
            profile.mkdir(parents=True, exist_ok=True)
            marker.write_text("Synthetic NiimStudio test data only\n")
            data, cache = profile / "data", profile / "cache"
        self.history = DeviceHistory(profile / "settings.json" if self.smoke else None)
        data.mkdir(parents=True, exist_ok=True, mode=0o700)
        cache.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.network = WebKit.NetworkSession.new(str(data), str(cache))
        context = WebKit.WebContext.new()
        context.register_uri_scheme("niimstudio", self.serve_asset)
        security = context.get_security_manager()
        security.register_uri_scheme_as_secure("niimstudio")
        security.register_uri_scheme_as_cors_enabled("niimstudio")
        manager = WebKit.UserContentManager.new()
        manager.register_script_message_handler("studio", None)
        manager.connect("script-message-received::studio", self.on_message)
        manager.add_script(
            WebKit.UserScript.new(
                f"window.__NIIMSTUDIO_NATIVE__ = true; window.__NIIMSTUDIO_SMOKE__ = {str(self.smoke).lower()}; window.__NIIMSTUDIO_DEMO__ = {str(self.smoke and bool(os.environ.get('NIIMSTUDIO_DEMO'))).lower()}; window.__NIIMSTUDIO_RESTART_VERIFY__ = {str(self.smoke and bool(os.environ.get('NIIMSTUDIO_RESTART_VERIFY'))).lower()}; window.__NIIMSTUDIO_BENCHMARK__ = {str(self.smoke and bool(os.environ.get('NIIMSTUDIO_BENCHMARK'))).lower()}; window.__NIIMSTUDIO_LIFECYCLE_MODE__ = {json.dumps(os.environ.get('NIIMSTUDIO_LIFECYCLE_MODE', '') if self.smoke else '')};",
                WebKit.UserContentInjectedFrames.TOP_FRAME,
                WebKit.UserScriptInjectionTime.START,
                None,
                None,
            )
        )
        self.webview = WebKit.WebView(web_context=context, network_session=self.network, user_content_manager=manager)
        mark("webview_created")
        settings = self.webview.get_settings()
        configure_rendering(settings)
        settings.set_enable_developer_extras(bool(os.environ.get("NIIMSTUDIO_DEBUG")))
        settings.set_enable_write_console_messages_to_stdout(bool(os.environ.get("NIIMSTUDIO_DEBUG")) or self.smoke)
        settings.set_enable_page_cache(False)
        self.webview.connect("decide-policy", self.decide_policy)
        self.webview.connect("load-failed", self.load_failed)
        self.webview.connect("web-process-terminated", self.process_terminated)
        if enabled():
            self.webview.connect("load-changed", lambda _view, event: mark("load_" + event.value_nick))
        layout.set_content(self.webview)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), self.css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        self.sync_theme()
        mark("theme_synced")
        self.theme_timer = GLib.timeout_add_seconds(2, self.sync_theme)
        self.window.present()
        mark("window_presented")
        # Let the compositor paint the themed window before WebKit's first
        # process launch, which can block this thread on a busy machine.
        GLib.idle_add(self.begin_load)
        if self.smoke:
            GLib.timeout_add_seconds(75, self.smoke_timeout)

    def begin_load(self):
        if not self.shutting_down:
            mark("load_uri")
            self.webview.load_uri(ORIGIN + "index.html")
            mark("load_uri_returned")
        return GLib.SOURCE_REMOVE

    def serve_asset(self, request):
        started = time.monotonic_ns()
        try:
            path = asset_path(request.get_uri(), ROOT / "dist")
            data = path.read_bytes()
            # Static map: avoid initializing the system MIME database on the
            # UI thread while the first editor frame is loading.
            mime = MIME_TYPES.get(path.suffix.lower(), "application/octet-stream")
            stream = Gio.MemoryInputStream.new_from_bytes(GLib.Bytes.new(data))
            response = WebKit.URISchemeResponse.new(stream, len(data))
            response.set_content_type(mime)
            headers = Soup.MessageHeaders.new(Soup.MessageHeadersType.RESPONSE)
            headers.append("Content-Type", mime)
            headers.append("Access-Control-Allow-Origin", "*")
            headers.append(
                "Content-Security-Policy",
                (
                    "default-src 'self' niimstudio: data: blob:; script-src 'self' niimstudio:; "
                    "style-src 'self' niimstudio: 'unsafe-inline'; img-src 'self' niimstudio: data: blob:; "
                    "font-src 'self' niimstudio: data:; connect-src 'self' niimstudio: data: blob: https://api.labelary.com; "
                    "worker-src 'self' niimstudio: blob:; object-src 'none'; frame-src 'none'; base-uri 'none'"
                ),
            )
            headers.append("X-Content-Type-Options", "nosniff")
            response.set_http_headers(headers)
            request.finish_with_response(response)
            mark("asset", name=path.name, bytes=len(data), ms=round((time.monotonic_ns() - started) / 1e6, 1))
        except (OSError, ValueError) as error:
            LOG.warning("Cannot serve bundled asset: %s", error)
            request.finish_error(
                GLib.Error.new_literal(Gio.io_error_quark(), "Asset not found", Gio.IOErrorEnum.NOT_FOUND)
            )

    def decide_policy(self, _view, decision, kind):
        if kind in (WebKit.PolicyDecisionType.NAVIGATION_ACTION, WebKit.PolicyDecisionType.NEW_WINDOW_ACTION):
            uri = decision.get_navigation_action().get_request().get_uri()
            if uri.startswith(ORIGIN) and kind != WebKit.PolicyDecisionType.NEW_WINDOW_ACTION:
                decision.use()
            else:
                decision.ignore()
                # External content is never loaded into a privileged editor view.
                if uri.startswith("https://"):
                    dialog = Adw.AlertDialog(heading="Open external link?", body=uri)
                    dialog.add_response("cancel", "Cancel")
                    dialog.add_response("open", "Open in browser")
                    dialog.set_close_response("cancel")
                    dialog.connect(
                        "response",
                        lambda _d, response: (
                            Gio.AppInfo.launch_default_for_uri(uri, None) if response == "open" else None
                        ),
                    )
                    dialog.present(self.window)
            return True
        return False

    def evaluate(self, script):
        if not self.shutting_down:
            self.webview.evaluate_javascript(script, -1, None, ORIGIN, None, None, None)

    def send(self, message):
        self.evaluate(f"window.__niimstudioReceive?.({json.dumps(message, ensure_ascii=True)});")

    def reply(self, request_id, value=None, error=None, cancelled=False):
        self.send({"id": request_id, "value": value, "error": str(error) if error else None, "cancelled": cancelled})

    def send_font_families(self):
        if self.shutting_down:
            return GLib.SOURCE_REMOVE
        families = sorted(
            family.get_name() for family in self.window.get_pango_context().get_font_map().list_families()
        )
        self.send({"event": "fonts", "families": families})
        return GLib.SOURCE_REMOVE

    def ensure_bluez(self):
        """BlueZ is only needed once the user connects or reconnects."""
        if self.bluez is None:
            self.bluez = BlueZ()
        return self.bluez

    def check_updates(self):
        if self.smoke or self.update_started or not updates_enabled() or managed_root(ROOT) is None:
            return GLib.SOURCE_REMOVE

        def work():
            try:
                info = fetch_latest(__version__)
            except Exception as error:  # Offline checks are silent, never intrusive.
                LOG.info("Update check skipped: %s", error)
                return
            if info:
                GLib.idle_add(self.offer_update, info)

        threading.Thread(target=work, name="niimstudio-update-check", daemon=True).start()
        return GLib.SOURCE_REMOVE

    def offer_update(self, info):
        if not self.shutting_down and not self.update_started:
            self.send({"event": "update", "version": info["version"], "tag": info["tag"]})
        return GLib.SOURCE_REMOVE

    def start_update(self, request_id, tag):
        root = managed_root(ROOT)
        if self.smoke:
            self.reply(request_id, error="Updates are unavailable in smoke tests")
            return
        if root is None:
            self.reply(request_id, error="This copy is not a managed native install. See docs/INSTALLING.md.")
            return
        if not isinstance(tag, str) or not tag or len(tag) > 40 or any(c not in "0123456789.v-+" for c in tag):
            self.reply(request_id, error="Invalid release tag")
            return
        if self.update_started:
            self.reply(request_id, error="An update is already running")
            return
        self.update_started = True
        self.reply(request_id, {"started": True})

        def work():
            try:
                ok, message = run_update(root, tag)
            except Exception as error:
                ok, message = False, str(error)
            event = {"event": "updateProgress", "state": "ready" if ok else "failed", "version": tag.lstrip("v")}
            if not ok:
                event["message"] = message or "The update did not finish."
                self.update_started = False
            GLib.idle_add(self.send, event)

        threading.Thread(target=work, name="niimstudio-update", daemon=True).start()

    def on_message(self, _manager, value):
        try:
            raw = value.to_json(0)
            if len(raw) > 90 * 1024 * 1024:
                raise ValueError("Bridge message is too large")
            request = validate_message(json.loads(raw))
        except (ValueError, TypeError, AttributeError) as error:
            LOG.warning("Rejected bridge message: %s", error)
            return
        request_id, operation = request["id"], request["op"]
        try:
            if self.smoke and operation in {"write", "remember"}:
                raise RuntimeError("Hardware access is disabled in smoke tests")
            if operation.startswith("test") and not self.smoke:
                raise RuntimeError("Test operations are unavailable in a normal workspace")
            if operation == "ready":
                mark("bridge_ready")
                self.editor_ready = True
                self.reply(request_id, {"palette": self.palette, "version": __version__})
                # Font enumeration is large and only populates the font picker;
                # keep it off the path to the first usable editor frame.
                GLib.idle_add(self.send_font_families)
            elif operation == "workspaceReady":
                mark("workspace_ready")
                if os.environ.get("NIIMSTUDIO_LIFECYCLE_TRACE"):
                    print("LIFECYCLE_TIMINGS=" + json.dumps(request.get("timings", {})), flush=True)
                self.reply(request_id)
                if self.smoke and os.environ.get("NIIMSTUDIO_LIFECYCLE_BENCHMARK"):
                    self.smoke_failed = request.get("verified") is False

                    def close_benchmark():
                        mark("close_requested")
                        self.window.close()
                        return GLib.SOURCE_REMOVE

                    GLib.timeout_add(100, close_benchmark)
                elif self.smoke:
                    # The editor hook exists only after mount; schedule from the
                    # readiness handshake rather than guessing from `ready`.
                    self.smoke_test()
                elif not self.update_checked:
                    self.update_checked = True
                    # Keep the first frame and startup work ahead of any network.
                    GLib.timeout_add(1500, self.check_updates)
            elif operation == "updateApp":
                self.start_update(request_id, request.get("tag"))
            elif operation == "quit":
                self.reply(request_id)
                self.prepare_close()
            elif operation == "testUpdate":
                self.reply(request_id, True)
                self.send({"event": "update", "version": "9.9.9", "tag": "v9.9.9"})
            elif operation == "connect":
                self.choose_printer(request_id, automatic=request.get("automatic") is True)
            elif operation == "chooseDevice":
                self.choose_printer_only(request_id)
            elif operation == "connectPending":
                self.connect_pending(request_id)
            elif operation == "cancelConnect":
                self.cancel_connection(request_id)
            elif operation == "knownDevice":
                self.reply(request_id, self.history.info())
            elif operation == "setReconnectPolicy":
                enabled = request.get("enabled")
                if type(enabled) is not bool:
                    raise ValueError("Reconnect policy must be true or false")
                previous = self.history.auto_reconnect
                self.history.auto_reconnect = enabled
                try:
                    self.history.save()
                except OSError:
                    self.history.auto_reconnect = previous
                    raise
                self.reply(request_id, {"enabled": enabled})
                self.send({"event": "reconnect-policy", "enabled": enabled})
            elif operation == "testDismissDevices":
                opened = self.chooser is not None
                if opened:
                    self.chooser.close()
                self.reply(request_id, opened)
            elif operation == "testSnapshot":
                self.capture_test_view(request_id, request.get("name"))
            elif operation == "remember":
                if self.transport is None or self.selected_device is None or self.connecting:
                    raise ConnectionError("No successfully opened printer to remember")
                self.history.remember(self.selected_device)
                self.reply(request_id)
            elif operation == "disconnect":
                self.disconnect_transport(request_id)
            elif operation == "write":
                data = request.get("data")
                if (
                    not isinstance(data, list)
                    or not 0 < len(data) <= 65536
                    or any(type(b) is not int or not 0 <= b <= 255 for b in data)
                ):
                    raise ValueError("Invalid transport bytes")
                transport = self.transport
                if transport is None:
                    raise ConnectionError("Printer is disconnected")
                self.run_task(
                    lambda: transport.write(bytes(data)),
                    lambda _r: self.reply(request_id),
                    lambda error: self.reply(request_id, error=error),
                )
            elif operation == "save":
                self.save_file(request_id, request)
            elif operation == "status":
                self.printing = request.get("printing") is True
                self.reply(request_id)
            elif operation == "log":
                LOG.info("Editor: %s", str(request.get("message", ""))[:4000])
                self.reply(request_id)
        except Exception as error:
            self.reply(request_id, error=error)

    def choose_printer(self, request_id, automatic=False):
        if self.smoke and automatic:
            self.reply(request_id, error="Automatic printer connections are disabled in smoke tests")
            return
        if self.connecting or self.chooser or self.transport:
            self.reply(request_id, error="A printer connection is already active or in progress")
            return
        self.connecting = True
        self.connect_request = request_id

        def canceled():
            self.connecting = False
            self.chooser = None
            if self.connect_request == request_id:
                self.connect_request = None
            self.generation += 1
            transport, self.transport = self.transport, None
            if transport:
                self.run_task(transport.close)
            self.reply(request_id, cancelled=True)

        def selected(device):
            self.open_device(request_id, device)

        if automatic:

            def resolve():
                try:
                    bluez = self.ensure_bluez()
                    objects = bluez.objects()
                except GLib.Error:
                    objects = {}
                return self.history.resolve_last(discover_serial(), objects)

            def unavailable(error):
                if self.connect_request != request_id:
                    return
                self.connect_request = None
                self.connecting = False
                self.reply(request_id, error=error)

            self.run_task(resolve, selected, unavailable)
        else:
            try:
                bluez = self.ensure_bluez()
            except GLib.Error as error:
                LOG.info("Bluetooth is unavailable: %s", error)
                bluez = None
            self.chooser = DeviceChooser(
                self.window,
                bluez,
                self.run_task,
                selected,
                canceled,
                history=self.history,
                policy_changed=lambda enabled: self.send({"event": "reconnect-policy", "enabled": enabled}),
                hardware_enabled=not self.smoke,
            )
            self.chooser.present()

    def open_device(self, request_id, device):
        if self.connect_request != request_id:
            return
        if self.smoke:
            self.connect_request = None
            self.reply(request_id, error="Hardware access is disabled in smoke tests")
            self.connecting = False
            return
        self.generation += 1
        generation = self.generation

        def data_received(data):
            GLib.idle_add(self.transport_event, generation, {"event": "data", "data": list(data)})

        def disconnected(reason):
            GLib.idle_add(self.transport_event, generation, {"event": "disconnect", "reason": reason})

        def progress(message):
            def display():
                if generation == self.generation and self.chooser and not self.chooser.closed:
                    self.chooser.set_status(message)
                return GLib.SOURCE_REMOVE

            GLib.idle_add(display)

        transport = (
            SerialTransport(data_received, disconnected)
            if device["kind"] == "serial"
            else BluetoothTransport(self.ensure_bluez(), data_received, disconnected, progress)
        )
        self.transport = transport
        self.selected_device = device

        def opened(_value):
            if generation != self.generation:
                return
            self.connecting = False
            if self.connect_request == request_id:
                self.connect_request = None
            if self.chooser:
                self.chooser.connection_succeeded()
                self.chooser = None
            self.reply(request_id, {"name": device["name"], "kind": device["kind"]})

        def failed(error):
            if generation != self.generation:
                return
            self.connecting = False
            self.transport = None
            self.run_task(transport.close)
            if isinstance(error, PermissionError):
                error = RuntimeError(
                    "USB permission denied. See docs/HARDWARE.md for per-device udev access; do not run NiimStudio as root."
                )
            if self.chooser and not self.chooser.closed:
                self.chooser.connection_failed(error, device["kind"])
            else:
                if self.connect_request == request_id:
                    self.connect_request = None
                self.reply(request_id, error=error)

        self.run_task(lambda: transport.open(device["id"]), opened, failed)

    def choose_printer_only(self, request_id):
        """Choose a device without disturbing the currently connected transport."""
        if self.connecting or self.chooser:
            self.reply(request_id, error="A printer connection is already in progress")
            return

        def canceled():
            self.chooser = None
            self.reply(request_id, cancelled=True)

        def selected(device):
            chooser = self.chooser
            self.chooser = None
            self.pending_device = {key: device[key] for key in ("kind", "id", "name")}
            self.reply(request_id, {"device": self.pending_device})
            if chooser and not chooser.closed:
                chooser.connection_succeeded()

        try:
            bluez = self.ensure_bluez()
        except GLib.Error as error:
            LOG.info("Bluetooth is unavailable: %s", error)
            bluez = None
        self.chooser = DeviceChooser(
            self.window,
            bluez,
            self.run_task,
            selected,
            canceled,
            history=self.history,
            policy_changed=lambda enabled: self.send({"event": "reconnect-policy", "enabled": enabled}),
            hardware_enabled=not self.smoke,
        )
        self.chooser.present()

    def connect_pending(self, request_id):
        """Open the device returned by choose_printer_only. No path crosses JS unchecked."""
        device = self.pending_device
        if device is None:
            self.reply(request_id, error="No printer was selected")
            return
        if self.connecting or self.chooser or self.transport:
            self.reply(request_id, error="Disconnect the current printer before connecting the selected one")
            return
        self.pending_device = None
        self.connecting = True
        self.connect_request = request_id
        self.open_device(request_id, device)

    def cancel_connection(self, request_id):
        """Cancel a pending automatic connection so Devices can be opened."""
        if not self.connecting or self.chooser is not None:
            self.reply(request_id, {"cancelled": False})
            return
        pending, self.connect_request = self.connect_request, None
        self.connecting = False
        self.generation += 1
        transport, self.transport = self.transport, None
        if transport:
            self.run_task(transport.close)
        if pending is not None:
            self.reply(pending, cancelled=True)
        self.reply(request_id, {"cancelled": True})

    def transport_event(self, generation, event):
        if generation == self.generation and self.transport and not self.shutting_down:
            if event["event"] == "disconnect":
                transport, self.transport = self.transport, None
                self.run_task(transport.close)
            self.send(event)
        return GLib.SOURCE_REMOVE

    def disconnect_transport(self, request_id):
        transport, self.transport = self.transport, None
        self.generation += 1
        if transport:
            self.run_task(
                transport.close, lambda _r: self.reply(request_id), lambda error: self.reply(request_id, error=error)
            )
        else:
            self.reply(request_id)

    def save_file(self, request_id, request):
        encoded = request.get("base64")
        if not isinstance(encoded, str) or len(encoded) > 85 * 1024 * 1024:
            raise ValueError("Export exceeds 64 MiB")
        content = base64.b64decode(encoded, validate=True)
        filename = Path(str(request.get("filename", "label.json"))).name or "label.json"
        dialog = Gtk.FileDialog(title="Export label", initial_name=filename)

        def chosen(dialog, result):
            try:
                file = dialog.save_finish(result)
            except GLib.Error:
                self.reply(request_id, False)
                return
            self.run_task(
                lambda: file.replace_contents(content, None, False, Gio.FileCreateFlags.PRIVATE, None),
                lambda _r: self.reply(request_id, True),
                lambda error: self.reply(request_id, error=error),
            )

        dialog.save(self.window, None, chosen)

    def sync_theme(self):
        manager = Adw.StyleManager.get_default()
        palette = None if os.environ.get("NIIMSTUDIO_THEME") == "gtk" else read_palette(fallback=False)
        source = "omarchy" if palette is not None else "gtk"
        if source == "gtk":
            if self.theme_source != "gtk":
                self.css.load_from_string("")
                manager.set_color_scheme(Adw.ColorScheme.DEFAULT)
            palette = gtk_palette(self.window.get_style_context().lookup_color, manager.get_dark())
        signature = json.dumps((source, palette), sort_keys=True)
        if signature != self.theme_signature:
            if source == "omarchy":
                self.css.load_from_string(gtk_css(palette))
                manager.set_color_scheme(
                    Adw.ColorScheme.FORCE_LIGHT if palette["mode"] == "light" else Adw.ColorScheme.FORCE_DARK
                )
            self.palette = palette
            self.theme_source = source
            self.theme_signature = signature
            self.webview.set_background_color(self.background_color(palette["background"]))
            # The ready handshake supplies the initial palette. Evaluating JS in
            # the still-empty view starts a throwaway WebKit document/process.
            if self.editor_ready:
                self.send({"event": "theme", "palette": palette})
        return GLib.SOURCE_CONTINUE

    @staticmethod
    def background_color(color):
        rgba = Gdk.RGBA()
        rgba.parse(color)
        return rgba

    def about(self, _button):
        dialog = Adw.AboutDialog(
            application_name="NiimStudio",
            application_icon="printer-symbolic",
            version=__version__,
            developer_name="NiimStudio contributors",
            license_type=Gtk.License.MIT_X11,
            comments="A local-first NIIMBOT label workspace, made for Omarchy and other Linux desktops.\nPrinter communication is powered by NiimBlueLib. The label engine is based on MultiMote’s NiimBlue.\nNot affiliated with NIIMBOT.",
            website="https://github.com/Akuyumu/niimstudio",
        )
        dialog.add_credit_section(
            "Open-source foundations",
            ["MultiMote — NiimBlue and NiimBlueLib (MIT)", "Fabric.js, Svelte, GTK and WebKitGTK"],
        )
        dialog.present(self.window)

    def confirm_close(self, _window):
        if self.smoke and not os.environ.get("NIIMSTUDIO_LIFECYCLE_BENCHMARK"):
            return False
        if self.close_pending or self.close_prompt:
            return True
        if not getattr(self, "printing", False):
            self.prepare_close()
            return True
        self.close_prompt = True
        dialog = Adw.AlertDialog(
            heading="Close the label workspace?",
            body="A print job is in progress. Closing disconnects the printer and may leave a partial label.",
        )
        dialog.add_response("cancel", "Keep editing")
        dialog.add_response("close", "Close")
        dialog.set_close_response("cancel")

        def responded(_dialog, response):
            self.close_prompt = False
            if response == "close":
                self.prepare_close()

        dialog.connect("response", responded)
        dialog.present(self.window)
        return True

    def prepare_close(self):
        """Flush the last debounced edit before removing the window, never silently lose it."""
        if self.close_pending:
            return
        if not self.editor_ready:
            self.window.destroy()
            return
        self.close_pending = True
        self.close_generation += 1
        generation = self.close_generation

        def finished(view, result):
            if not self.close_pending or generation != self.close_generation:
                return
            if self.close_timer is not None:
                GLib.source_remove(self.close_timer)
            self.close_timer = None
            self.close_pending = False
            try:
                # "unavailable" means the editor never mounted, so there is no
                # pending work to lose; only an explicit false is a save failure.
                outcome = view.call_async_javascript_function_finish(result).to_string()
            except GLib.Error:
                outcome = "false"
            if outcome in {"true", "unavailable"}:
                mark("draft_flushed")
                self.window.destroy()
            else:
                self.close_save_failed()

        def expired():
            self.close_timer = None
            self.close_pending = False
            self.close_save_failed()
            return GLib.SOURCE_REMOVE

        self.close_timer = GLib.timeout_add(2000, expired)
        self.webview.call_async_javascript_function(
            'return window.__niimstudioPrepareClose?.() ?? "unavailable";',
            -1,
            None,
            None,
            ORIGIN,
            None,
            finished,
        )

    def close_save_failed(self):
        self.close_prompt = True
        dialog = Adw.AlertDialog(
            heading="The latest draft could not be saved",
            body="Keep editing and export your work, or close without saving the latest changes.",
        )
        dialog.add_response("cancel", "Keep editing")
        dialog.add_response("discard", "Close without saving")
        dialog.set_response_appearance("discard", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_close_response("cancel")

        def responded(_dialog, response):
            self.close_prompt = False
            if response == "discard":
                self.window.destroy()

        dialog.connect("response", responded)
        dialog.present(self.window)

    def load_failed(self, _view, _event, uri, error):
        LOG.error("Editor failed to load %s: %s", uri, error)
        return False

    def process_terminated(self, _view, reason):
        LOG.error("Embedded editor terminated: %s", reason)
        if self.smoke:
            self.smoke_failed = True
            self.quit()
            return
        dialog = Adw.AlertDialog(
            heading="The label editor stopped",
            body="Reopen NiimStudio. Your last autosaved draft and saved labels remain on this device.",
        )
        dialog.add_response("close", "Close")
        dialog.connect("response", lambda _d, _r: self.quit())
        dialog.present(self.window)

    def smoke_test(self):
        # Run after Svelte's onMount, then exercise the real embedded editor.
        GLib.timeout_add_seconds(2, self.finish_smoke)

    def capture_test_view(self, request_id, name):
        allowed = {
            "editor",
            "templates",
            "qr-dialog",
            "barcode-dialog",
            "print-preview",
            "stock-picker",
            "stock-detected",
            "connection-failure",
            "settings",
            "settings-failure",
            "settings-unavailable",
            "crisp-text",
            "auto-connect",
            "zoom-clipped",
            "print-advanced",
            "stock-compatible",
            "stock-fit-zoom",
            "stock-override",
            "stock-height-corrected",
            "stock-printable-area",
        }
        directory = os.environ.get("NIIMSTUDIO_TEST_ARTIFACTS")
        if name not in allowed or not directory:
            self.reply(request_id, False)
            return
        target = Path(directory)
        target.mkdir(parents=True, exist_ok=True)

        def captured(view, result):
            try:
                texture = view.get_snapshot_finish(result)
                texture.save_to_png(str(target / f"{name}.png"))
                self.reply(request_id, True)
            except GLib.Error as error:
                self.reply(request_id, error=error)

        def settled_capture():
            self.webview.get_snapshot(WebKit.SnapshotRegion.FULL_DOCUMENT, WebKit.SnapshotOptions.NONE, None, captured)
            return GLib.SOURCE_REMOVE

        GLib.timeout_add(250, settled_capture)

    def finish_smoke(self):
        script = """(async () => {
          const test = await window.__niimstudioSmokeTest();
          return JSON.stringify(test);
        })()"""

        def finished(view, result):
            try:
                value = view.call_async_javascript_function_finish(result)
                result = json.loads(value.to_string())
                artifacts = result.pop("artifacts", {})
                directory = os.environ.get("NIIMSTUDIO_TEST_ARTIFACTS")
                if directory:
                    target = Path(directory)
                    target.mkdir(parents=True, exist_ok=True)
                    for name in ("qr-url.png", "barcode-url.png", "barcode-special.png", "ean13.png"):
                        if name in artifacts:
                            (target / name).write_bytes(
                                base64.b64decode(artifacts[name].split(",", 1)[1], validate=True)
                            )
                print("SMOKE_RESULT=" + json.dumps(result), flush=True)
                self.smoke_failed = result.get("ok") is not True
                chooser = DeviceChooser(
                    self.window,
                    self.bluez,
                    self.run_task,
                    lambda _d: None,
                    lambda: None,
                    history=self.history,
                    hardware_enabled=False,
                )
                chooser.present()
                chooser.close()
                print("SMOKE_DEVICE_CHOOSER=ok", flush=True)
            except Exception as error:
                print("SMOKE_ERROR=" + str(error), flush=True)
                self.smoke_failed = True
            self.quit()

        def run():
            self.webview.call_async_javascript_function(
                "return await " + script, -1, None, None, ORIGIN, None, finished
            )

        snapshot_path = os.environ.get("NIIMSTUDIO_SNAPSHOT")
        if snapshot_path:

            def snapshot_finished(view, result):
                try:
                    Path(snapshot_path).parent.mkdir(parents=True, exist_ok=True)
                    texture = view.get_snapshot_finish(result)
                    texture.save_to_png(snapshot_path)
                except GLib.Error as error:
                    LOG.warning("Snapshot failed: %s", error)
                run()

            self.webview.get_snapshot(
                WebKit.SnapshotRegion.FULL_DOCUMENT, WebKit.SnapshotOptions.NONE, None, snapshot_finished
            )
        else:
            run()
        return GLib.SOURCE_REMOVE

    def smoke_timeout(self):
        if not self.shutting_down:
            print("SMOKE_ERROR=Editor did not become ready", flush=True)
            self.smoke_failed = True
            self.quit()
        return GLib.SOURCE_REMOVE

    def shutdown_app(self, _app):
        mark("shutdown")
        self.shutting_down = True
        if self.chooser:
            self.chooser._cleanup()
        if self.transport:
            self.executor.submit(self.transport.close)
        self.executor.shutdown(wait=False, cancel_futures=False)


def main():
    if Gtk.get_major_version() < 4 or (Gtk.get_major_version() == 4 and Gtk.get_minor_version() < 12):
        print("NiimStudio requires GTK 4.12 or newer.", file=sys.stderr)
        return 2
    if Adw.get_major_version() == 1 and Adw.get_minor_version() < 5:
        print("NiimStudio requires Libadwaita 1.5 or newer.", file=sys.stderr)
        return 2
    logging.basicConfig(
        level=logging.DEBUG if os.environ.get("NIIMSTUDIO_DEBUG") else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    smoke = "--smoke-test" in sys.argv
    app = StudioApplication(smoke=smoke)
    result = app.run([sys.argv[0]])
    return 1 if smoke and getattr(app, "smoke_failed", True) else result
