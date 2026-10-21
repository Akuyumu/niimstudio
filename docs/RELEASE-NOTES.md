# NiimStudio v0.2.0

Stable release. **Vibe-coded / built with AI assistance. MIT licensed**, preserving
NiimBlue, NiimBlueLib and bundled dependency notices. The previously published
v0.1.3 remains available and unchanged.

## Highlights

- **B1 Pro Bluetooth works without pairing:** refresh BLE discovery, prefer the
  known NIIMBOT characteristic, and retry one transient local-abort/timeout.
  The user confirms connection through the app; three consecutive agent-run native
  connect/handshake/heartbeat/disconnect cycles also passed. No PIN is guessed.
- **Connect is the normal action:** Pair appears only for a device whose connection
  reports an authentication failure. Cancellation and retry remain available.
- **Settings:** power/connection sounds, sleep modes and reconnect preference.
  Unavailable settings are hidden. Writes are read back: small green confirmations
  for matches, persistent errors for failures, unknown controls hidden until refresh.
  Temporary preference notices expire. Settings cannot change during printing.
- **Correct B1 Pro roll height:** the supplied firmware-2.12 reply reports 30 mm /
  354 px with a separate 6 mm / 70 px gap. The previous interpretation unconditionally
  subtracted the latter and displayed 24 mm / 284 px. A narrow upstream-derived
  compatibility fix preserves the 30 mm height for B1 Pro; there are no SKU→size
  guesses or cloud lookups.
- **Override detected size** offers compatible presets as an explicit Manual
  choice. It affects the canvas/print preview, not printer calibration, and clears
  on reconnect or a changed roll/report. **Use printer detection** restores automatic mode.
- **50×30 mm stock is available:** physical label width and printable width are
  separate. The reported head width is used, with explicit non-printable margin
  guidance; incompatible presets are hidden.
- **Simpler printing:** normal preview shows Copies and Print. Collapsed Advanced
  controls have plain-language hover explanations; native protocol selection is automatic.
- **Sharper editing:** zoom redraws at display resolution without changing document
  coordinates or print/export pixels. Font names use the available toolbar width;
  header controls align and Devices uses a compact printer icon.
- Final review fixed failed reconnect-save rollback, print-task setup exceptions
  leaving controls locked, and offsets exceeding the printable raster width.

## Install or update

New native install:

```bash
curl -fsSL https://raw.githubusercontent.com/Akuyumu/niimstudio/v0.2.0/install.sh | bash -s -- --version v0.2.0
```

For Flatpak, explicitly add `--flatpak`; it is never selected or installed by
default. Native installs require the documented system GTK/WebKit dependencies,
offered with consent. The installer does not move a development checkout or replace
its launcher without separate `--replace-source` consent.

Existing managed native installs can use **Update now** or
`~/.local/bin/niimstudio --update`. Explicit v0.2.0-rc.1 installs can update to
this final stable release. Flatpak users rerun the installer with `--flatpak`.
Saved labels, drafts and settings are preserved. Back up/export important labels
before major updates.

## Verification and limits

Unit/lint/types/build/audit, actual GTK/WebKit dark/light/software-rendering smoke,
restart and immediate-close draft persistence, independent QR/barcode decoding,
and installed native plus x86-64/ARM64 Flatpak package validation pass. Release
assets are checksummed, and the published bundle is re-downloaded and installed in
an isolated HOME.

**Not claimed:** a verified physical USB/BLE print, power-cycle recovery, mid-print
radio-loss recovery, every printer/firmware, or universal Linux compatibility.
The supplied roll reply is regression-tested; inspect the first physical label
before batches. Sleep mode 4 still means **never or 60 minutes**, depending on
firmware; its meaning has not been verified on this B1 Pro. Explicit pairing prompts
remain unverified. Checksums provide download integrity, not independent signing.
