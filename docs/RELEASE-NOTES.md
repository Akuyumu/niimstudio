# NiimStudio v0.1.3

Installer routing fix. **Vibe-coded / built with AI assistance. MIT licensed**,
preserving NiimBlue, NiimBlueLib and dependency notices. Earlier releases remain
unchanged.

## Changes

- **Native is the only default route.** The installer no longer selects, downloads,
  or installs Flatpak when native requirements are missing. It prompts to install
  the native packages instead, and stops without changes if you decline.
- **Flatpak is a separate, explicit route** (`--flatpak`). Its own dependencies and
  GNOME runtime are only touched when you choose that route. Choosing it is a
  deliberate decision because of the runtime size.
- If a Flatpak installation already exists, a default run now stops and asks you to
  update it with `--flatpak` or remove it before switching to native. It no longer
  silently follows the Flatpak route.
- Native/Flatpak conflict checks are unchanged on their explicit routes: they never
  install both by surprise, and label data is preserved.
- Documentation now states the routes separately, including the Arch/Omarchy fact
  that `webkitgtk-6.0` is one normal 38 MiB package in `extra` (GTK4 API sibling of
  the 4.1 engine already used by GTK3 apps), offered with consent.
- Installer tests now assert that default mode stays native, never invokes Flatpak
  install/remote commands, and stops with an explicit `--flatpak` instruction when
  a Flatpak exists.

## Install or update (native)

```bash
curl -fsSL https://raw.githubusercontent.com/Akuyumu/niimstudio/v0.1.3/install.sh | bash -s -- --version v0.1.3
```

Flatpak is explicit:

```bash
curl -fsSL https://raw.githubusercontent.com/Akuyumu/niimstudio/v0.1.3/install.sh | bash -s -- --version v0.1.3 --flatpak
```

Native users can also use **Update now** in the app or
`~/.local/bin/niimstudio --update`; Flatpak users rerun the installer with
`--flatpak`. Both keep labels, drafts and settings.

## Verification and remaining limits

Unit/types/lint/build/audit, actual GTK/WebKit UI, installer routing tests, restart
and immediate-close persistence, and exported-package install/reinstall/upgrade/
rollback/data retention are release gates on native Ubuntu and x86-64/ARM64
Flatpak. Automatic native dependency installation still requires an interactive
confirmation (or `--yes`) and sudo; the in-app updater remains non-privileged and
uses `--no-deps`.

**Physical printing, pairing and real roll auto-detection remain unverified.** No
universal printer/distro/kernel support is claimed. Checksums are integrity checks,
not independent signatures.
