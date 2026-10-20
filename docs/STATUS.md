# Status — 2026-10-20

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

- 69 Python tests: real pseudoterminal USB round trips/disconnects; mocked BlueZ
  fragmentation, service discovery, notifications, and cleanup; mocked pairing
  agents/prompts; palette safety/GTK compositing, bridge validation, and device history.
- Installer tests cover checksum failure, traversal/links, update rollback,
  idempotence, conflicts, source migration, concurrent runs, data preservation,
  and a mock-network Flatpak bootstrap. Real bundle install/uninstall runs in an
  isolated HOME with spaces. Release CI also exercises installed GUI builds.
- Ubuntu CI exercises the actual installed native app and real Flatpak GUI on
  x86-64 and ARM64. Exported Flatpak bundles are installed/reinstalled with a
  retained-data fixture before publishing, not merely built as manifests.
- 21 Node tests: CSV safety, print validation, undo, reconnect, every printable
  Code 128 character, EAN-13, cancellation, media validation, head-width/rotation
  mapping, resolution priority, and safe preset conversion.
- Actual GTK/WebKit smoke profile: editor objects, image import, serialization,
  undo/redo, preview/encoding, palette application, draft storage, native chooser,
  invalid-save protection, quota rollback, template drawer/search/save, and the
  formatting buttons, link entry/editing, invalid EAN rejection, code-insert
  cancellation, and native chooser cancellation without an error toast. No physical printing.
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

No USB printer or matching known BLE printer was present during development.
USB/BLE printing, BlueZ pairing prompts with real hardware, battery/RFID accuracy
and automatic sizing from real media reports,
reconnect behavior under printer faults, and representative real-media results
need the checklist in `HARDWARE.md`. Mock tests are not substitutes for these.
Theme parsing and initial application are automated-tested; a live desktop
theme switch should be included in user acceptance without changing the theme
silently during development.

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

1. Verify a real B1 Pro over USB, then BLE, using one small label at a time.
2. Fix device-specific problems based on packet logs, preserving protocol reuse.
3. Validate label stock profiles, saved-library/restart workflows, and batch UX.
4. Add native backup/restore, test imported PDFs, improve accessible tool labels,
   and refine the template drawer from actual usage feedback.
5. The packaged release is early software, not complete hardware verification.
   Grow the tested support matrix and consider a signed Flatpak update repository.
