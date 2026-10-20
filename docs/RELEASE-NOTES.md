# NiimStudio v0.1.2

Patch release adding an in-app update path. **Vibe-coded / built with AI
assistance. MIT licensed**, preserving NiimBlue, NiimBlueLib and dependency
notices. v0.1.0 and v0.1.1 remain unchanged.

## Changes

- Managed native installs now check the public release feed once per launch
  (after the first usable frame). When a newer release exists, a slim bar above
  the footer shows **Update now**. It downloads the same checksum-verified bundle
  as `niimstudio --update`, then offers **Restart**.
- The in-app update uses `--no-deps`: it never installs system packages, asks for
  sudo, or changes desktop/driver settings. Source checkouts and Flatpak are not
  self-updated; the bar and the check are skipped for them.
- The check is one HTTPS request to the public GitHub API with the app version as
  its user agent. No labels, printer details, or usage data are sent.
  `NIIMSTUDIO_NO_UPDATE_CHECK=1` disables it for managed installs.
- README and the install guide now include an **Updating** section for native and
  Flatpak paths, with the terminal fallback.
- GUI smoke now covers the update bar and its dismissal. Unit tests cover version
  comparison, managed-install detection, the offline path, fixed API/user agent,
  the pinned `--no-deps` command, and the opt-out.

## Install or update

```bash
curl -fsSL https://raw.githubusercontent.com/Akuyumu/niimstudio/v0.1.2/install.sh | bash -s -- --version v0.1.2
```

Native users can also run `~/.local/bin/niimstudio --update`, or use **Update now**
in the app. Close the app before a terminal update. Flatpak app bundles are updated
by rerunning the installer; ordinary `flatpak update` updates only shared runtimes.

## Verification and remaining limits

Unit/types/lint/build/audit, actual GTK/WebKit UI (including the update bar),
restart and immediate-close persistence, and exported-package install/reinstall/
upgrade/rollback/data retention are release gates on native Ubuntu and x86-64/ARM64
Flatpak. The update download is exercised by the installer tests, not by publishing
a release from a test run.

The in-app check needs network access; offline launches simply skip it silently.
It is not a background updater, does not install while the app is closed, and does
not update Flatpak/shared runtimes. **Physical printing, pairing and real roll
auto-detection remain unverified.** No universal printer/distro/kernel support is
claimed. App checksums are integrity checks, not independent signatures.
