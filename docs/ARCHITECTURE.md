# Architecture

## Why this stack

GTK4 + Libadwaita provide the native window, dialogs, printer chooser, pairing
prompts, and file exports. WebKitGTK 6 embeds the existing Svelte/Fabric label
editor. This is deliberately a hybrid app, not a pure-GTK canvas rewrite.
Quickshell is well suited to a future launcher/status widget, but the label
editor should remain an independently testable desktop application.

NiimBlue already implements text/fonts, images, QR codes, barcodes, vectors,
templates, batch variables, and thermal post-processing. Keeping it avoids
releasing a visually polished editor with fewer working features. Keep the
native adapter separate so future NiimBlue updates remain practical.

## Data flow

The home screen is the label editor itself: centered label, one inline selection
formatting row, and a bottom content strip. Templates open in a searchable
slide-out `<dialog>` sidebar with native browser focus trapping and Escape
handling. Saving uses a compact name dialog; it never requires a separate home
dashboard. Advanced upstream controls remain available behind More properties.

The header's left panel icon opens Templates; Save as template is explicit.
The native More menu filters the shared tool registry to ArUco and the two import
tools; exposed text/image/code/shape tools are not repeated. Native AppModal
disables fades and subscribes before showing (immediate lifecycle events); the
sidebar uses a plain dim layer without a blur/slide animation. Browser-reference
modals keep their existing animation behavior. `--software-rendering` sets only
the current process's WebKit acceleration policy; it is not persisted and never
disables sandboxing. Overlay regression tests sample real editor/viewport geometry.

Launch and quit are deliberately staged. `scripts/niimstudio` selects a system
interpreter and delegates to `scripts/launch.py`, which chooses the system WebKit or
the optional extracted runtime without importing GI on the launcher path. That
runtime mounts a cached, signature-validated symlink view (`runtime_view.py`) into a
private bwrap namespace; a lock keeps views used by another running instance and
only two generated views are retained. The window is presented before the deferred
navigation so the compositor can paint the themed shell while WebKit starts.
`ready` returns the palette immediately; font enumeration arrives later as a
`fonts` event. `close-request` flushes the draft through
`window.__niimstudioPrepareClose` and destroys the window only after a successful
save (2 s timeout, retry-safe); printing still requires confirmation. Sidebar
validation is cached and invalidated by writes and cross-window storage events; the
stock dialog is retained after first use. `scripts/benchmark-lifecycle` and
`scripts/test-close` verify these paths with a synthetic profile.
`CodeEditor.svelte` validates content and provides live QR/Code 128/EAN-13 previews
before adding an object. Selected codes expose Edit content and double-click
editing. New QR objects include a serialized four-module quiet zone; legacy QR
objects retain their original positioning. Rounded stock uses matching canvas
and CSS geometry. A one-time migration rounds the old default draft, not saved
templates; rectangular and circular presets remain available in Label stock.

`src/desktop/media.ts` validates reported media and projects presets at the known
printer resolution. `StockSetup.svelte` replaces raw desktop size/DPI/direction
controls: reported media configures an untouched canvas; existing artwork gets a
confirmation. Non-reporting stock uses fixed-size cards, with head-width filtering.
Reported pixel dimensions take precedence when consistent with millimeters; head
width maps to canvas height for left feed and width for top feed. Head pixels are
byte-aligned. No product-code size database or speculative shape inference is used.
The session's confirmed stock is cleared on disconnect or lost media information;
Preview blocks unknown profiles, unconfirmed stock, and mismatched dimensions.
CSS rounding in Preview does not modify the underlying encoded image.

1. The bundled editor requests a connection through a WebKit script handler.
2. GTK displays the device chooser. Only a device explicitly selected there can
   be opened; JavaScript cannot submit arbitrary device paths.
3. USB uses standard termios at 115200 baud. BLE uses BlueZ's D-Bus GATT APIs.
4. `NativeNiimbotClient` subclasses NiimBlueLib's abstract client. All packet
   parsing, printer negotiation, RFID, heartbeat, image encoding, and print-task
   selection stay in the pinned upstream protocol library.
5. Native transports exchange only raw byte arrays and disconnect events with
   the editor. BLE writes respect the discovered MTU and channel flags.

Device work runs on a single background executor. GTK changes and JavaScript
events return through GLib's main loop. Generation IDs discard stale transport
events. Disconnect and shutdown release the app's connection/discovery session.

## Pairing

The always-visible **Devices** button opens native linking/pairing. After a
successful protocol negotiation, a private, atomically written settings file at
`$XDG_CONFIG_HOME/niimstudio/settings.json` records the last selected device and
up to ten recent device descriptors, not credentials. Reconnect only resolves a
currently detected USB identity or a known BlueZ device. It never opens a device
path supplied directly by JavaScript or automatically calls Pair.

Startup and unexpected disconnects schedule retries at 2, 5, 10, 30, then at
most every 60 seconds. Each I/O attempt has its own deadline. Manual disconnect
pauses the retry loop until the next deliberate link or app launch. Retries wait
for an in-flight print to settle and never replay a print job. The Devices dialog
has an explicit reconnect preference. USB `/dev/serial/by-id` paths are preferred
when available. A new scan is required if a printer changes its Bluetooth address.

The chooser can connect directly to BLE devices that do not require a bond, or
pair first. A temporary `org.bluez.Agent1` with KeyboardDisplay capabilities is
registered by the same D-Bus connection that requests pairing. It handles PIN,
numeric passkey, and confirmation prompts only for the selected device. It
never requests the default-agent role, guesses PINs, removes bonds, or edits
Omarchy's Bluetooth plugin.

## Security and offline behavior

The editor is served from a private `niimstudio://app/` scheme, not an HTTP
server. Asset paths are bounded to `dist/`, including symlink/traversal checks.
Remote pages cannot navigate into the privileged WebView. External links
require confirmation and open in the normal browser. The bridge has a fixed
operation allowlist and no command execution or arbitrary file-read API.

CSP forbids eval and remote scripts/frames. CSV parsing uses d3's row tokenizer
instead of its Function-generating object parser. The only allowed external
fetch destination is `https://api.labelary.com` for the upstream, user-initiated
ZPL rendering feature. That feature sends the submitted ZPL to that service;
ordinary label design and printing do not require a network connection.

File exports use a native save dialog. Saved labels and the debounced current
draft live in WebKit's app-specific local storage. Quota errors trigger library
rollback. JSON and PNG exports remain the portable backup mechanism. There is
no cloud account, telemetry, CUPS service, or background daemon.

## Omarchy theme sync

Read `$XDG_STATE_HOME/omarchy/current/theme/colors.toml` (default
`~/.local/state/...`) with an older `~/.config/omarchy/current/...` fallback.
Validate color literals before using them. Polling every two seconds handles
Omarchy replacing the entire theme directory, unlike monitoring only the old
file inode. Apply palettes to both the app's GTK CSS provider and WebView CSS
variables. Never tint the printable black-on-white label canvas.

No theme hooks, theme changes, shell restarts, or packaged Omarchy file edits
are necessary. With no Omarchy palette, the app leaves GTK/Libadwaita in its
default appearance mode and samples the native window, text, accent, and card
colors for the embedded editor. Translucent GTK colors are composited against
the window background. `NIIMSTUDIO_THEME=gtk` forces that path even on Omarchy.

`scripts/system-python` selects a system interpreter with GI rather than assuming
the `/usr/bin/python` alias exists. Source installs target modern Linux desktops
(GTK 4.12+, Libadwaita 1.5+, WebKitGTK 6, Python 3.11+, Node 22.18+ for building).

## Project map

`install.sh` selects a native release when a compatible system runtime exists,
otherwise Flatpak. It verifies SHA-256 before invoking the release installer or
Flatpak. `managed_install.py` installs immutable versioned app directories and
atomically switches a `current` link, with conflict checks, an install lock and
integration rollback. App data lives elsewhere and is never purged on uninstall.
`package-release.py` includes prebuilt dist/Python, explicit project files and
dependency license texts; it excludes source checkout metadata and private data.

`packaging/flatpak/` wraps that same prebuilt app in GNOME Platform 49. The sandbox
uses GTK portals and scoped Omarchy theme reads, BlueZ D-Bus, and broad device
permission required for direct serial. It does not grant general home access.
The release workflow builds native + both Flatpak architectures and gates public
assets on installed-app GUI smoke tests. Shared runtimes use Flathub signatures;
the app bundle uses GitHub checksums, not independent signing. Flatpak app updates
rerun the installer; there is no hosted app OSTree update repository yet.

| Path | Purpose |
| --- | --- |
| `native/niimstudio/app.py` | GTK lifecycle, bounded asset serving/bridge, native export, smoke profiles |
| `native/niimstudio/theme.py`, `history.py` | Validated palette sampling; private atomic reconnect preferences |
| `native/niimstudio/devices.py`, `pairing.py` | Native chooser, bounded discovery, application-scoped BlueZ agent |
| `native/niimstudio/bluetooth.py`, `serial_transport.py` | BLE GATT/MTU and termios byte transports |
| `src/desktop/` | NiimStudio layout/dialogs, native client/bridge, retry controller, isolated UI tests |
| `src/components/`, `src/fabric-object/`, `src/utils/` | Label engine, object types, persistence, encoding/preview helpers |
| `scripts/`, `packaging/` | Portable launcher, user-local install, tests, icon, Arch-only runtime fallback |
| `tests/`, `docs/` | Unit/regression tests, support status, setup, attribution, screenshots |

The browser engine reference remains runnable with `npm run dev`. Legacy mobile,
Tauri, Docker and Gitea files are upstream references, not supported NiimStudio
release targets. See CONTRIBUTING.md for the build/restart and screenshot loop.

## Runtime and packaging

Prefer system `webkitgtk-6.0`. An optional local runtime downloads the package
from configured Arch repositories, verifies its detached signature with the
system pacman keyring, and extracts it under ignored `.runtime/`. A small
Bubblewrap mount namespace presents compiled-in helper paths under `/usr/lib`
for this app only. Host files are not modified; WebKit's own sandbox stays on.
This is a local development convenience, not the eventual release packaging.

Distributable releases should use a reviewed Arch PKGBUILD or Flatpak and track
security updates of WebKit and the JavaScript dependencies. Do not publish an
archive of the local runtime or claim that all NIIMBOT models have been tested.
