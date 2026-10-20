# Status — 2026-10-20

## Implemented

- Native GTK4/Libadwaita desktop app with bundled NiimBlue editor and no server.
- Direct-to-editor home, centered label, inline formatting, bottom insert strip,
  searchable pop-out template sidebar, and compact named-template save dialog.
- Top-left sidebar trigger, explicit Save as template, rounded stock preview,
  live code-entry dialogs and visible Edit content for selected codes.
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

## Automated verification

- 28 Python tests: real pseudoterminal USB round trips/disconnects; mocked BlueZ
  fragmentation, service discovery, notifications, and cleanup; mocked pairing
  agents/prompts; palette safety/GTK compositing, bridge validation, and device history.
- 13 Node tests: CSV safety, print validation, undo, reconnect, every printable
  Code 128 character, EAN-13 check digits, and typed cancellation behavior.
- Actual GTK/WebKit smoke profile: editor objects, image import, serialization,
  undo/redo, preview/encoding, palette application, draft storage, native chooser,
  invalid-save protection, quota rollback, template drawer/search/save, and the
  formatting buttons, link entry/editing, invalid EAN rejection, code-insert
  cancellation, and native chooser cancellation without an error toast. No physical printing.
- Independent ZXing-C++ decoding of real Fabric-rendered QR URL, Code 128 URL,
  the corrected `$)` patterns, and EAN-13 output.
- Actual separate-process restart restores the saved draft (including QR quiet
  zone and edited barcode data) and named templates from an isolated profile.
- The same GUI flows pass in Omarchy/Nord and forced system-GTK light mode;
  this tests the fallback on this host, not every Linux distribution's desktop.
- Svelte/TypeScript checking, ESLint, production build, npm dependency audit.

## Still needs real hardware / user acceptance

No USB printer or matching known BLE printer was present during development.
USB/BLE printing, BlueZ pairing prompts with real hardware, battery/RFID accuracy,
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
  Quickshell widget, multi-printer queue, signed downloadable releases, Flatpak,
  or an Arch PKGBUILD.
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
5. The public repository is an early source release, not a claim of complete
   hardware verification. Next add packaged releases and a tested support matrix.
