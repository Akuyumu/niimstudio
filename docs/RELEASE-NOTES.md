# NiimStudio v0.2.0-rc.1 — release candidate

**Opt-in prerelease, not a stable update.** Published v0.1.3 and its ordinary update
channel are unchanged. **Vibe-coded / built with AI assistance. MIT licensed**,
preserving NiimBlue, NiimBlueLib and bundled dependency notices.

## Highlights

- **B1 Pro Bluetooth works without pairing:** refresh BLE discovery, prefer the
  known NIIMBOT characteristic, and retry one transient local-abort/timeout.
  The user confirms connection through the app; three consecutive agent-run native
  connect/handshake/heartbeat/disconnect cycles also passed. No PIN is guessed.
- **Connect, not two competing buttons:** Pair is offered only for a device whose
  connection reports an authentication failure. Cancellation/retry remain available.
- **Settings:** power/connection sounds, sleep modes and reconnect preference.
  Unavailable settings are hidden. Writes are read back: small green confirmations
  for matches, persistent errors for failures, unknown controls hidden until refresh.
  Temporary preference notices expire. Settings cannot change during printing.
- **Correct B1 Pro roll height:** the supplied firmware-2.12 reply reports 30 mm /
  354 px with a separate 6 mm / 70 px gap. The old library unconditionally subtracted
  the latter and displayed 24 mm / 284 px. A narrow upstream-derived compatibility
  fix now preserves the 30 mm height for B1 Pro; no SKU→size guesses or cloud lookup.
- **Override detected size** offers compatible presets as an explicit Manual
  choice. It affects the canvas/print preview, not printer calibration, and clears
  on reconnect or changed roll/report. Use printer detection restores automatic mode.
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

## Install explicitly (native default)

```bash
curl -fsSL https://raw.githubusercontent.com/Akuyumu/niimstudio/v0.2.0-rc.1/install.sh | bash -s -- --version v0.2.0-rc.1
```

For Flatpak, explicitly add `--flatpak`; it is never selected or installed by
default. Native installs require the documented system GTK/WebKit dependencies,
offered with consent. This does not move an existing development checkout or
replace its launcher without the separate `--replace-source` consent.

Ordinary stable installs never receive this candidate through Update now or the
latest-release installer. Candidate users can be offered the final 0.2.0 stable
release later, but not an automatic downgrade to 0.1.3 or another candidate.
Back up/export important labels before opting into prerelease software.

## Verification and limits

Unit/lint/types/build/audit, actual GTK/WebKit dark/light/software-rendering smoke,
restart and immediate-close draft persistence, independent QR/barcode decoding,
and native/Flatpak package validation are required before publication. Release
candidate publishing is a separate prerelease-only workflow; stable publication
still requires accepted commits on main and a numeric stable version tag.

**Not claimed:** a verified physical USB/BLE print, power-cycle recovery, mid-print
radio-loss recovery, every printer/firmware, or universal Linux compatibility.
The supplied roll reply is regression-tested; the user should confirm the corrected
50×30 mm reading after restart and inspect the first physical label before batches.
Sleep mode 4 still means **never or 60 minutes**, depending on firmware; its meaning
has not been verified on this B1 Pro. Explicit pairing prompts remain unverified.
Checksums provide download integrity, not independent signing.
