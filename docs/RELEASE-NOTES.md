# NiimStudio v0.1.1

Patch release focused on overlay stability and a cleaner insertion menu.
**Vibe-coded / built with AI assistance. MIT licensed**, preserving NiimBlue,
NiimBlueLib and dependency notices. The v0.1.0 release remains unchanged.

## Changes

- Removed native dialog fades, sidebar slide animation and backdrop blur to
  reduce graphics-stack-dependent overlay flicker. Dialog lifecycle listeners
  are registered before showing, including immediate/non-animated dialogs.
- **More** now contains only ArUco, Import ZPL and Import PDF. Text, images,
  QR/barcodes and shapes stay on the exposed toolbar without duplicate entries.
- Added optional `--software-rendering` for a one-launch WebKit fallback, without
  changing desktop/driver settings or disabling sandboxing.
- Added repeated overlay open/close checks for stable viewport/editor geometry,
  backdrop cleanup, motion-free native overlays and non-duplicated More tools.
- Simplified the shared object picker and removed unused animation CSS; refreshed
  CI actions for Node 24. Generated development/test files remain out of releases.
- Kept uninstall commands at the end of Quick start; updates/removal preserve data.
- Faster app start: the optional extracted runtime reuses a validated library view
  instead of rebuilding thousands of links per launch; one interpreter check
  replaces the previous pair; no JavaScript is evaluated in a blank WebView; and
  the themed window is presented before WebKit navigation starts. Installed font
  enumeration now runs after the first editor frame.
- Faster app close: closing an idle app no longer shows a confirmation dialog.
  Pending edits are flushed first, and the window stays open with a clear choice
  if that flush fails. Active printing still asks before disconnecting.
- Cached template validation and reused native stock/modal instances keep panel
  opens from re-reading and rebuilding their contents.

## Measured performance

Median of six warm launches on the development machine (WebKitGTK 2.54.1,
synthetic local profile, same build script, measured from process start):

| Interaction | v0.1.0 | v0.1.1 | Change |
| --- | ---: | ---: | ---: |
| Window shown | 1285 ms | 645 ms | −50% |
| Editor ready to use | 1720 ms | 1140 ms | −34% |
| Quit to process exit | 207 ms | 67 ms | −68% |
| Full quit + relaunch | 1927 ms | 1207 ms | −37% |
| Sidebar open, 128 templates (JS/DOM ready) | 11 ms | 2 ms | −82% |
| Label-stock dialog open (JS/DOM ready) | 6 ms | 1 ms | −83% |

Where the remaining launch time goes: GTK/PyGObject import, WebKit process and
page startup, and the first Fabric/Svelte render. Those are now the floor for this
embedding; these figures are not a promise for every GPU, desktop, or cold start.


## Install or update

```bash
curl -fsSL https://raw.githubusercontent.com/Akuyumu/niimstudio/v0.1.1/install.sh | bash -s -- --version v0.1.1
```

Close the app before updating. Existing native users can also run
`~/.local/bin/niimstudio --update`. Flatpak app updates use the installer; ordinary
`flatpak update` updates the shared runtimes, not GitHub app bundles.

No Git, Node/npm, AUR, or source build is needed. The installer selects a native
bundle or x86-64/ARM64 Flatpak; package/repository setup requires consent.
[Install/uninstall and software-rendering details](https://github.com/Akuyumu/niimstudio/blob/v0.1.1/docs/INSTALLING.md).

## Verification and remaining limits

Unit/types/lint/build/audit, actual GTK/WebKit UI, repeat overlay interactions,
restart persistence, and exported-package install/reinstall/upgrade/rollback/data
retention are release gates on native Ubuntu and x86-64/ARM64 Flatpak. Omarchy
smoke tests cover normal GTK/Omarchy themes and the software-rendering fallback.

We could not directly observe the reported GPU-specific flicker; the overlay
changes are conservative mitigations and still need confirmation on that device.
**Physical printing, pairing and real roll auto-detection remain unverified.**
No universal printer/distro/kernel support or proprietary-app feature parity is
claimed. Flatpak has broad device access for direct serial, not general home
access. App checksums are integrity checks, not independent signatures.
