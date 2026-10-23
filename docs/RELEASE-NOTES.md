# NiimStudio v0.3.0

Stable release. **Vibe-coded / built with AI assistance. MIT licensed**, preserving
NiimBlue, NiimBlueLib and bundled dependency notices. The previous stable v0.2.0
remains available and unchanged.

## Highlights

- **Auto-connect is bounded:** startup and unexpected-disconnect retries stop after
  five attempts instead of looping indefinitely.
- **Visible and cancellable:** the header shows `Auto-connecting…` or
  `Retrying in Ns` with an explicit **Cancel** action. Cancel opens Devices and
  safely abandons the pending connection attempt.
- **Changing printers does not disconnect first:** opening Devices while connected
  leaves the current print link active. Closing the chooser keeps it; selecting a
  different printer switches only after that explicit choice.
- **Forget an auto-connect printer:** Devices now shows the remembered target with a
  **Forget** action. It removes that printer name, including its USB/BLE variants,
  stops automatic retries for it, and keeps any current connection open.
- **Fit view by default:** the editor measures the available stage instead of using
  a fixed 200% zoom, keeping the whole label and its true proportions visible.
  Fit updates when the window width or height changes.
- **Better navigation:** the large bordered stage is the viewing area. Ctrl+scroll
  zooms, and **Space + left-drag** moves the label—even when it is fully visible and
  there is empty space around it. Fit recenters it.
- **No misleading crop border:** the redundant dotted viewport outline is gone. A
  caption notes when the current zoom shows only part of the label.
- **Includes v0.2.0's printer work:** unpaired B1 Pro Bluetooth connection, verified
  sound/sleep settings, corrected 50 × 30 mm stock height, explicit manual stock
  override, and the simpler print preview.
- Release preparation also preserves failed-preference rollback, print-lock recovery,
  oversized-offset validation, and display-only zoom/export separation.

## Install or update

New native install:

```bash
curl -fsSL https://raw.githubusercontent.com/Akuyumu/niimstudio/v0.3.0/install.sh | bash -s -- --version v0.3.0
```

Flatpak is explicit:

```bash
curl -fsSL https://raw.githubusercontent.com/Akuyumu/niimstudio/v0.3.0/install.sh | bash -s -- --version v0.3.0 --flatpak
```

Native is the default. Flatpak is never selected or installed automatically.
Native installs require the documented system GTK/WebKit dependencies, offered with
consent. The installer does not move a development checkout or replace its launcher
without separate `--replace-source` consent.

Existing managed native installs can use **Update now** or
`~/.local/bin/niimstudio --update`. Explicit v0.2.0/0.2.0-rc.1 installs can update to
this newer stable release. Flatpak users rerun the installer with `--flatpak`.
Saved labels, drafts and settings are preserved. Back up/export important labels
before major updates.

## Verification and limits

Unit/lint/types/build/audit, actual GTK/WebKit dark/light/software-rendering smoke,
restart and immediate-close draft persistence, independent QR/barcode decoding, and
installed native plus x86-64/ARM64 Flatpak package validation pass. Release assets
are checksummed, and the published bundle is re-downloaded and installed in an
isolated HOME.

A user confirmed successful physical B1 Pro prints over **both USB and Bluetooth LE**.
Release automation itself performs no physical print.

**Still not claimed:** real pairing prompts, power-cycle recovery, mid-print
radio-loss recovery, every printer/firmware, or universal Linux compatibility.
Inspect the first physical label before batches. Sleep mode 4 still means **never or
60 minutes**, depending on firmware. Checksums provide download integrity, not
independent signing.
