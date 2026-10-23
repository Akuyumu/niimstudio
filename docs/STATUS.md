# Status — 2026-10-23

## Stable/development separation

- `main` is the accepted stable source line. v0.3.0 incorporates the validated
  reconnect, device-switching and canvas-navigation work from `dev`; the previous
  stable v0.2.0 remains available as an immutable release.
- Both branches run checks. A release-policy gate requires a stable numeric tag,
  matching web/native versions and a commit already on `main` before packaging.
  The updater explicitly rejects drafts/prereleases as well as non-stable tags.
- Managed installs and immutable published assets are independent of development
  builds; install validation failures preserve the previous baseline. Source users
  can pin a release tag in a separate checkout. v0.2.0-rc.1 and v0.3.0 were validated
  through the same package gates before stable publication.

## After v0.3.0 (unreleased)

- B21S uses a 384-pixel/203-DPI printable head but documents 20–50 mm label widths.
  The media picker had treated printable width as physical width, hiding 50×30 mm
  stock, and auto-detection rejected a reported 50 mm roll for the same reason.
- Audited every model in the pinned NIIMBOT library against its hardware
  configuration. Physical stock width is now derived from the documented head
  class (12→15, 24→25, 48/50→50, 56→60, 72→75, 80→82, 104→108 mm) with confirmed
  per-model exceptions. This exposes 50 mm stock on all 2-inch models, 60 mm stock
  on K2, and the larger presets on 3-/4-inch printers; the printable raster remains
  capped at the reported head width with an edge-margin notice.
- Unknown future models fall back to the nearest documented head class rather than
  losing the physical-media allowance. B21S and the other newly covered models still
  need user confirmation that auto-detection succeeds with their actual printer
  replies; no physical print was performed for this audit.

## v0.3.0

- Automatic reconnect is capped at five attempts with 2/5/10/30-second gaps
  instead of retrying indefinitely.
- The header now shows `Auto-connecting…` or `Retrying in Ns` with an explicit
  **Cancel** action during automatic reconnects. Either Cancel or Devices stops the
  pending attempt and opens the chooser, so another printer can be selected.
- Devices stays enabled during automatic attempts; it is disabled only while a print
  job is active. The native `cancelConnect` operation invalidates queued callbacks,
  closes only the pending transport, and replies to both pending requests safely.
- After the fifth failure, a persistent error explains that automatic reconnect
  stopped and offers Open Devices / retry.
- The editor now opens at a computed fit zoom (capped at 200%) rather than a fixed
  200%. Window/label-size changes refit only while Fit mode remains active; manual
  zoom stays manual. The zoom control returns to Fit and uses a fitting icon.
- Opening Devices while connected no longer tears down the current link. The
  chooser opens over the live connection; cancel keeps it, and selecting a device
  explicitly switches only after a native, opaque pending selection is consumed.
  No arbitrary device path is accepted from JavaScript.
- Devices shows the current auto-connect target with a Forget action. It removes the
  printer name and its USB/BLE variants from history, stops targeting it for automatic
  reconnect, and leaves a currently connected printer connected.
- The large stage is the pan area, with no extra dotted viewport border. A
  “Zoomed in: Space+drag to see the full label” caption appears when content extends
  beyond the stage. Space+left-drag moves even a fully visible label within the empty
  stage space; Ctrl+scroll zooms and Fit recenters.

## v0.2.0 release review

- The user confirms Bluetooth now connects in the application. Pair is no longer
  a default row action: it appears only after that device's explicit authentication
  failure, not after timeouts or canceled authentication. Connect is the normal path.
- The user supplied the actual B1 Pro 2.12 paper fields: totalHeight=30/354px,
  gapHeight=6/70px, but parsed paperHeight=24/284px. This proves the 24mm display
  came from unconditional subtraction in the pinned library, not a 24mm raw height.
  A narrow B1 Pro compatibility backport follows upstream commit
  `45ef990007e5ba3b257a9a81332e75ffcdf7b442`: retain totalHeight as sticker height.
  Other models keep their existing interpretation; the protocol remains pinned.
- Explicit manual override is available in the detected-stock dialog. It is scoped
  to the current connection/roll/report/profile, visibly labelled Manual, respected
  by print validation, and expires on a changed roll/report or reconnect. It is not
  silently persisted as an automatic override of future reports.
- Review fixed reconnect-preference save rollback, task-factory exceptions leaving
  printing locked, and validation of the actual offset-adjusted raster before a job
  starts. New GUI regressions cover failures, override/restore/expiry and the 30mm fix.
- Candidate tags have a separate dev-ancestry/version gate and the same package
  matrix as stable releases. Publication is always prerelease and never latest;
  candidate installs can later be offered final stable, without downgrading to a
  previous stable version.
- **Post-release acceptance:** the user confirmed successful physical B1 Pro
  prints over **both USB and Bluetooth LE** after v0.2.0. Pairing prompts, batch
  behavior and fault recovery remain separate checklist items.

## v0.2.0 settings and roll-read work

- Top-right Settings replaces the native printer dropdown's everyday controls.
  Sound and idle timeout use existing NiimBlueLib commands with read-back
  verification. Opening settings changes no printer values; controls lock during
   printing and unknown settings are hidden. Small inline confirmations replace
   duplicate success banners; temporary app-preference notices expire after 3.5 s.
   Failed read-back shows the actual value, or hides an unknown value until refresh.
- Sleep mode 4 means never **or** 60 minutes depending on firmware. This is explicit
  in the UI, not claimed as a verified B1 Pro disable-sleep setting. Sound/sleep
  writes have synthetic verification only.
- Reconnect preference and read-only printer/roll details are available there.
  Details omit serial numbers, UUIDs and artwork. USB links show a USB icon.
- Media-query errors are preserved. RFID identity is distinguished from a size
  report. Optional, user-confirmed size presets are remembered by model/product
  code, labelled Saved roll rather than Auto, and can be changed. A conflicting
  parsed report cannot be bypassed by a saved preset.
- Vite's development dependency is updated to 7.3.7 for current advisories.

## v0.2.0 Bluetooth feedback

- Known classic-only entries are hidden by default. Show all Bluetooth devices
  reveals them, disabled and explained under Bluetooth, never USB. Unknown BLE
  services remain eligible rather than being assumed unsupported.
- Keeps the chooser open during a transport attempt, with progress and persistent
  error/tip/retry on failure. Pairing failures survive the two-second refresh.
  Negotiation failures in the editor have a persistent, dismissible error and
  an Open Devices / retry action. Cancellation remains quiet.
- Pairing has a visible Cancel pairing button that bypasses the occupied worker;
  cancel-before-start cannot accidentally send a queued Pair request. Instructions
  recommend Connect first rather than implying a PIN is always needed.
- Rejects unsuccessful protocol handshakes instead of displaying a false success;
  ignores callbacks from a canceled attempt. No PIN is guessed or pairing forced.
- Tests cover classic filtering, preserved failure messages, retry/cancel races,
  targeted tips, and the visible editor error/dismissal. Two authorized BLE-only
  diagnostics timed out before GATT discovery, with no pairing/print commands.
  Those early diagnostics were superseded by the real connection tests below.

## v0.2.0 BLE validation and UI feedback

- A fresh-advertisement/native link probe observed `le-connection-abort-by-local`;
  an independent Bleak 3.0.2 probe successfully resolved services and notifications
  without pairing. Baseline native transport passed two of three handshakes.
- Added a fresh LE discovery window and one bounded transient retry, with shared
  discovery ownership, progress and preferred NiimBlue characteristic selection.
  The updated native transport passed **3/3 consecutive real B1 Pro cycles**:
  connect, pinned-library handshake, three heartbeat reads, disconnect. Firmware
  2.12/protocol 5 reported 576 head pixels. No print/settings-write/calibration/
  pairing/reset commands were sent. USB was untouched. Details: HARDWARE.md.
- The stock picker now distinguishes physical media width from printable width.
  B1 Pro 50×30/50×50 mm presets are available with explicit edge-margin notices;
  incompatible presets are hidden. Reported head width takes precedence over the
  static fallback. No speculative SKU or model-based loaded-roll size is inferred.
- The user saw a real 50×24 mm size response for an identified 50×30 mm roll.
  The actual paper-info fields subsequently confirmed a software subtraction bug
  (fixed in the v0.2.0 release review above). A conflicting report must not silently
  replace an explicitly chosen physical size, even on a blank canvas.
- Native preview shows Copies and Print; technical controls are collapsed under
  Advanced with plain-language hover descriptions. Protocol selection is automatic.
  Header Devices uses a compact printer icon; automatic reconnect now has a visible
  status/cancel control and stops after five attempts.
- Zoom redraws the canvas at display resolution rather than enlarging its bitmap;
  tests verify pointer alignment and byte-identical unzoomed export pixels. The
  font picker grows with the formatting bar, instead of clipping the font name.

## v0.1.3 patch

- Installer default is native only. Auto mode no longer selects, downloads, or
  installs Flatpak; missing native packages are offered with consent, and an
  existing Flatpak stops the default run with an explicit `--flatpak` instruction.
  Flatpak remains a separate opt-in route with its own runtime and dependencies.
- Tests assert default-native routing, no Flatpak install/remote calls, and the
  existing-Flatpak stop. Docs describe the routes separately.
- README/help call out `webkitgtk-6.0` on Arch/Omarchy as a normal 38 MiB package
  (GTK4 API sibling of the installed 4.1 engine), not an unavailable dependency.

## v0.1.2 patch

- Managed native installs check the public GitHub release feed once per launch
  (after the first frame). A footer bar offers a checksum-verified update using
  the existing installer with `--no-deps`, then a restart. Flatpak and source
  checkouts are skipped; `NIIMSTUDIO_NO_UPDATE_CHECK=1` opts out. Only the app
  version is sent as a user agent; no labels, printer data, or telemetry.
- README and the install guide document the in-app and terminal update paths.
- GUI smoke covers the bar/dismissal; unit tests cover version comparison,
  managed-install detection, offline behavior, the fixed API/user agent, and the
  pinned non-privileged update command.

## v0.1.1 patch

- Native overlays use no fade/slide or backdrop blur, avoiding unnecessary GPU
  compositing during panel opening. Optional per-launch software rendering is
  available without changing desktop settings or disabling the WebKit sandbox.
- More contains only ArUco/ZPL/PDF; exposed toolbar tools are not duplicated.
- Actual GPU-specific flicker was reported but could not be directly observed;
  these compatibility mitigations still need confirmation on the affected device.
- Obsolete drawer-animation CSS and repeated picker markup were removed; CI
  actions use Node-24-compatible versions. Release contents remain allow-listed.
- Startup/close work: the extracted runtime reuses a locked, signature-validated
  library view; `scripts/launch.py` selects the interpreter/runtime without a
  throwaway GI import; the themed window is presented before WebKit navigation;
  fonts are enumerated after the first frame; template validation is cached; and
  idle close flushes the draft and exits without a dialog. Warm medians on this
  host: window 1285→645 ms, editor ready 1720→1140 ms, quit 207→67 ms.
  Remaining launch time is GTK/GI import, WebKit process/page startup and the
  first Fabric render; not hardware or cross-desktop guarantees.

## Implemented

- Native GTK4/Libadwaita desktop app with bundled NiimBlue editor and no server.
- Direct-to-editor home, centered label, inline formatting, bottom insert strip,
  searchable pop-out template sidebar, and compact named-template save dialog.
- Top-left sidebar trigger, explicit Save as template, rounded stock preview,
  live code-entry dialogs and visible Edit content for selected codes.
- Rounded print preview without changing encoded pixels; automatic stock sizing
  from valid media metadata, model/capability DPI and feed direction. Simple stock
  presets replace native raw size/DPI controls when detection is unavailable.
  Existing designs require confirmation, and unknown/mismatched stock cannot print.
- Native USB serial discovery and I/O; BlueZ BLE discovery and GATT transport.
- Optional application-scoped PIN/passkey/confirmation pairing.
- Remembered-device reconnect at startup and after unexpected disconnects,
  capped retry backoff, explicit stop on manual disconnect, and a Devices toggle.
- Live Omarchy palette updates for GTK and the embedded editor.
- Native GTK/Libadwaita light/dark/accent fallback on other modern Linux desktops;
  portable system-Python discovery rather than requiring an Arch-only alias.
- Native export dialogs, app-local persistence, autosaved draft, quota rollback.
- Upstream text/fonts, images, shapes, QR, barcodes, ArUco, templates, JSON/PNG
  import/export, CSV variables, print preview, thermal dithering and print tasks.
- Job/printhead checks; bounded USB/BLE operations and page-boundary batch stop.
- User-local launcher/desktop integration and an optional signed local runtime.
- v0.1.0 installer/release pipeline: native prebuilt bundle plus x86-64/ARM64
  Flatpak with GNOME runtime; one script chooses a format and verifies checksums.
  Explicit updates, source-launcher migration opt-in and data-preserving uninstall.

## Automated verification

- 111 Python tests: real pseudoterminal USB round trips/disconnects; mocked BlueZ
  fragmentation, service discovery, notifications, and cleanup; mocked pairing
  agents/prompts; palette safety/GTK compositing, bridge validation, and device history.
- Installer tests cover checksum failure, traversal/links, update rollback,
  idempotence, conflicts, source migration, concurrent runs, data preservation,
  and a mock-network Flatpak bootstrap. Real bundle install/uninstall runs in an
  isolated HOME with spaces. Release CI also exercises installed GUI builds.
- Ubuntu CI exercises the actual installed native app and real Flatpak GUI on
  x86-64 and ARM64. Exported Flatpak bundles are installed/reinstalled with a
  retained-data fixture before publishing, not merely built as manifests.
- 54 Node tests: settings/read-back, media reads, saved-roll identity, fit/clip zoom,
  connection
  troubleshooting tips, CSV safety, print validation, undo, reconnect, every printable
  Code 128 character, EAN-13, cancellation, media validation, all-library
  media-width classes, head-width/rotation mapping, resolution priority, and safe
  preset conversion.
- Actual GTK/WebKit smoke profile: editor objects, image import, serialization,
  undo/redo, preview/encoding, palette application, draft storage, native chooser,
  invalid-save protection, quota rollback, template drawer/search/save, and the
  formatting buttons, link entry/editing, invalid EAN rejection, code-insert
  cancellation, and native chooser cancellation without an error toast. The smoke
  profile performs no physical printing; separate user hardware confirmation is
  recorded below.
- Synthetic B1 Pro metadata exercises the stock picker, automatic empty-canvas
  setup, Auto badge, existing-design confirmation, resize undo/redo, mismatch and
  unknown-stock print guards, and visual-only rounded print-preview corners.
- Independent ZXing-C++ decoding of real Fabric-rendered QR URL, Code 128 URL,
  the corrected `$)` patterns, and EAN-13 output.
- Actual separate-process restart restores the saved draft (including QR quiet
  zone and edited barcode data) and named templates from an isolated profile.
- The same GUI flows pass in Omarchy/Nord and forced system-GTK light mode;
  this tests the fallback on this host, not every Linux distribution's desktop.
- Svelte/TypeScript checking, ESLint, production build, npm dependency audit.
- Repeated sidebar/stock-dialog tests sample viewport and editor geometry during
  opening/closing, check cleanup and absence of native blur/fades, and assert that
  More exposes only advanced tools. Renderer-policy tests cover safe opt-in/default.
- Real-process lifecycle checks cover immediate-close draft flush (before the
  debounce deadline) and restore in a new process. Unit tests cover runtime-view
  reuse/invalidation/pruning, close flush success, timeout and retry safety, and
  the printing confirmation. `npm run benchmark:lifecycle` records opt-in local
  markers without persistent telemetry or label content.

## Still needs real hardware / user acceptance

A B1 Pro's classic/BLE advertisements have been observed. The user confirms USB
connection, Bluetooth connection through the restarted GUI, and successful physical
prints over **both USB and Bluetooth LE**. Agent-run BLE link/handshake/heartbeat
cycles also pass. BlueZ pairing prompts with real hardware, battery/RFID accuracy,
automatic sizing from third-party media, batch/fault behavior, and representative
real-media results still need the checklist in `HARDWARE.md`. Mock tests are not
substitutes for these. Theme parsing and initial application are automated-tested;
a live desktop theme switch should be included in future acceptance without
changing the theme silently during development.

## Not claimed / not included

- Full feature parity with the proprietary NIIMBOT app. Its cloud account,
  commercial template/icon catalogs, paid content, and proprietary label formats
  are not reproduced.
- Classic Bluetooth SPP, CUPS driver/system-wide print queue, phone integration,
  Quickshell widget, multi-printer queue, independently signed app releases,
  AppImage, `.deb`/`.rpm`, or an Arch PKGBUILD. Flatpak is a GitHub-hosted bundle,
  not a Flathub app listing; its runtime comes from Flathub with permission.
- Automatic firmware updates, resets, Bluetooth bond removal, or USB permission
  changes. The inherited advanced firmware controls are not hardware-validated.
- Every upstream web-only feature in the native shell: remote template URLs,
  remote font downloads and browser/system-printer popup workflows are restricted
  by its offline/security policy. PDF import is inherited but needs its own
  representative-file tests. ZPL rendering uses Labelary online only when chosen.

## Next priorities

1. Exercise multiple copies, CSV batches, batch cancellation, and disconnect/reconnect
   behavior on the now-confirmed USB and BLE B1 Pro paths.
2. Fix device-specific problems based on user issue reports and redacted logs,
   preserving protocol reuse.
3. Validate label stock profiles, saved-library/restart workflows, and batch UX,
   including feedback from real users.
4. Add native backup/restore, test imported PDFs, improve accessible tool labels,
   and refine the template drawer from actual usage feedback.
5. The packaged release is early software, not complete hardware verification.
   Grow the tested support matrix and consider a signed Flatpak update repository.
