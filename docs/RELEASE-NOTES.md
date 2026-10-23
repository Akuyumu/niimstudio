# NiimStudio v0.3.1

Stable patch release. **Vibe-coded / built with AI assistance. MIT licensed**,
preserving NiimBlue, NiimBlueLib and bundled dependency notices. The previous
stable v0.3.0 remains available and unchanged.

## Highlights

- **Every supported Niimbot model now uses its documented physical media width**
  instead of treating the printable head as the whole roll. The pinned library
  covers 77 models: 12→15 mm, 24→25 mm, 48/50→50 mm, 56→60 mm, 72→75 mm,
  80→82 mm and 104→108 mm head/media classes, plus confirmed model exceptions.
- **B21S 50 × 30 mm stock is restored and auto-detection works.** The user
  confirmed the fix after the v0.3.0 report. B21S has a 48 mm printable head but
  supports 50 mm rolls, so the canvas shows the 48 mm printable area with edge
  margins.
- **More stock choices are correctly exposed:** all 2-inch models get 50 mm rolls,
  K2 gets 60 × 40 mm, and 3-/4-inch models get their larger presets. Invalid
  presets remain hidden rather than being offered as a guess.
- **Reported rolls auto-detect without widening the printhead.** Physical stock is
  matched against documented media bounds; the raster is still capped at the actual
  head width and byte-aligned. Print Preview shows when the roll has non-printable
  edges.
- **Unknown future library models inherit the nearest documented head class,** so a
  new model does not silently regress to head-only filtering. Confirmed exceptions
  include B1 SE (54 mm), M3/EP3M (78 mm), B31 (77 mm) and T2S (107 mm).

## Install or update

New native install:

```bash
curl -fsSL https://raw.githubusercontent.com/Akuyumu/niimstudio/v0.3.1/install.sh | bash -s -- --version v0.3.1
```

Flatpak is explicit:

```bash
curl -fsSL https://raw.githubusercontent.com/Akuyumu/niimstudio/v0.3.1/install.sh | bash -s -- --version v0.3.1 --flatpak
```

Native is the default. Flatpak is never selected or installed automatically.
Native installs require the documented system GTK/WebKit dependencies, offered with
consent. The installer does not move a development checkout or replace its launcher
without separate `--replace-source` consent.

Existing managed native installs can use **Update now** or
`~/.local/bin/niimstudio --update`. Existing v0.3.0 installations can update to this
newer stable release. Flatpak users rerun the installer with `--flatpak`.
Saved labels, drafts and settings are preserved. Back up/export important labels
before major updates.

## Verification and limits

Unit/lint/types/build/audit, actual GTK/WebKit dark/light/software-rendering smoke,
restart and immediate-close draft persistence, independent QR/barcode decoding, and
installed native plus x86-64/ARM64 Flatpak package validation pass. Release assets
are checksummed, and the published bundle is re-downloaded and installed in an
isolated HOME.

The B21S media fix is user-confirmed. Physical printing has been confirmed by a user
on a B1 Pro over **both USB and Bluetooth LE**; release automation itself performs no
physical print, and the broader model coverage is based on Niimbot's documented model
configuration and product specifications.

**Still not claimed:** physical printing on every newly covered model, real pairing
prompts, power-cycle recovery, mid-print radio-loss recovery, every printer/firmware
combination, or universal Linux compatibility. Inspect the first physical label
before batches. Sleep mode 4 still means **never or 60 minutes**, depending on
firmware. Checksums provide download integrity, not independent signing.
