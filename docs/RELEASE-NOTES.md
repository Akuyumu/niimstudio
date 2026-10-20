# NiimStudio v0.1.0

First early Linux desktop release, made for Omarchy with native GTK appearance
fallback on other modern desktops. **Vibe-coded / built with AI assistance. MIT
licensed**, with NiimBlue/NiimBlueLib attribution and dependency notices included.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/Akuyumu/niimstudio/v0.1.0/install.sh | bash -s -- --version v0.1.0
```

No Git, Node/npm, AUR, or source build required. The script selects a native bundle
when the runtime is available, or offers x86-64/ARM64 Flatpak with a GNOME runtime
for broader distro compatibility. Missing package/repository setup requires consent. See
[installation details](https://github.com/Akuyumu/niimstudio/blob/v0.1.0/docs/INSTALLING.md).

## Included

- Local editor, templates, autosaved drafts, text/images/shapes, editable QR/barcodes.
- Rounded stock previews and validated automatic media setup with a simple fallback picker.
- Native USB/BLE chooser, optional pairing prompts, remembered-device reconnect.
- Thermal print preview, batch handling, native exports, live Omarchy palette sync.
- Prebuilt user-local installer, checksum verification, explicit updates and data-preserving uninstall.
- Native portable bundle and Flatpak bundles for x86-64 and ARM64.

## Verification limits

Automated transport/encoding/media/install tests, actual GTK/WebKit UI smoke tests,
restart persistence and independent QR/barcode decoding pass. CI builds/tests on
Ubuntu; actual desktop smoke tests ran on Omarchy. **Real printer output, physical
pairing and real roll auto-detection remain unverified**: no suitable device was
available. This is not a claim of full proprietary NIIMBOT-app parity or universal
model/distro support. See docs/STATUS.md and docs/HARDWARE.md before a first print.

The native bundle uses system GTK/WebKit; Flatpak supplies a shared GNOME runtime
but still needs host device permissions/desktop portals. Flatpak device access is
broad for direct USB serial, while general home access is not granted. App updates
come from rerunning the installer; `flatpak update` updates shared runtimes, not
GitHub app bundles. This is not a promise of every Linux/kernel/printer combination.
Checksums are integrity checks, not independent signatures. User data is kept.
