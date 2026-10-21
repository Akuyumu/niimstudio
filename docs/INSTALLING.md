# Installing NiimStudio v0.2.0

## One command

```bash
curl -fsSL https://raw.githubusercontent.com/Akuyumu/niimstudio/main/install.sh | bash
```

Needs `curl` and Bash on a Linux desktop. Open **NiimStudio** from your app menu
after installation. No Git, Node.js, npm, pip, AUR, or source checkout is required.
The installer never launches the app, connects a printer, or prints a test label.
**Run as your normal user, not with sudo.** Only explicitly approved system-package
installation uses sudo. There are no new `.deb`/`.rpm` repositories to configure.

## How the script chooses a format

**Native is the only default.** Flatpak is a separate, explicit route selected with
`--flatpak`; the script never selects, downloads, or installs Flatpak on its own.

| Environment | Default |
| --- | --- |
| Existing NiimStudio user Flatpak | Stop: use `--flatpak` to update it, or remove it to switch |
| Existing native/source launcher | Keep the native route; source replacement needs opt-in |
| Python 3.11+, PyGObject, GTK 4.12+, Libadwaita 1.5+, WebKitGTK 6 and usable sandbox namespaces | Small prebuilt native bundle |
| Native runtime missing/too old | Prompt to install the listed native packages (with consent) |

On Arch/Omarchy, `webkitgtk-6.0` is a normal 38 MiB package in `extra` (its GTK4,
Libadwaita, libsoup3, GStreamer and Mesa dependencies are generally already
installed). It is the GTK4 API version of the WebKit engine, sibling to the 4.1
package used by GTK3 apps. The installer never installs it without confirmation;
`--no-deps` stops instead.

Flatpak bundles cover **x86-64 and ARM64** and include a maintained GNOME runtime.
Choose that route explicitly when you want the runtime included, when your distro
does not provide compatible native packages, or when host policy blocks native
WebKit sandbox namespaces. It does **not** mean every old kernel, 32-bit system,
container, headless server, or distribution has been tested. Unsupported systems
stop with instructions rather than pretending installation succeeded. Native
bundles are architecture-neutral but require the correct system Python/GI/native
libraries for that architecture.

With `--flatpak`, if Flatpak is missing, the script offers its normal distribution
package using apt, pacman, dnf, zypper, apk, or xbps where recognized. Other
distributions get [Flatpak setup instructions](https://flatpak.org/setup/), then
can rerun the same script. Flatpak must be supported/configured by the host; the
installer does not edit NixOS configuration or enable kernel features/system
services itself.

If host policy blocks native WebKit's sandbox namespaces, the native route stops
without changing that policy and points to the explicit Flatpak route. The
installer never disables WebKit sandboxing or changes sysctls. Release CI permits
namespaces only inside its disposable test VMs so it can exercise the real
sandboxed app.

## Inspect first or choose a format/version

This executes project code you choose to trust. For an inspect-before-running flow:

```bash
curl -fsSLo niimstudio-install.sh https://raw.githubusercontent.com/Akuyumu/niimstudio/v0.2.0/install.sh
less niimstudio-install.sh
bash niimstudio-install.sh --version v0.2.0
```

```bash
bash niimstudio-install.sh --flatpak           # explicit separate route; includes GNOME runtime
bash niimstudio-install.sh --native            # default: distro-native GTK/WebKit
bash niimstudio-install.sh --check             # no app install or package changes
bash niimstudio-install.sh --no-deps           # never install system packages
bash niimstudio-install.sh --install-deps      # explicitly authorize missing system packages
```

Default confirmation reads `/dev/tty`, so it works with piped input. With no
terminal it stops rather than assuming consent. `--yes` explicitly accepts the
otherwise-interactive package, runtime-repository and app-install prompts; use
only after reviewing this behavior. `--no-deps` does not prohibit downloading a
Flatpak runtime into your user Flatpak installation when `--flatpak` was chosen.
The script does not modify shell profiles, broad USB permissions, Bluetooth agents
or bonds. Package-manager maintainer scripts may perform their normal service setup.

### Download integrity and trust

The script verifies the selected release asset against `SHA256SUMS` over HTTPS.
Checksums detect corrupt/mismatched downloads; because the assets/checksums come
from the same GitHub project, they are **not independent signatures or protection
against repository compromise**. No TLS bypass is used. A failed checksum leaves
the installed app unchanged. A Flatpak runtime remote may already have been added
with permission before the app download fails; that remote is not removed silently.

## Flatpak: permissions, updates and removal

The script asks before adding the signed Flathub runtime repository under the
user-local name `niimstudio-runtime`. It is used for the GNOME runtime; NiimStudio's
app bundle comes from this project's GitHub release, not from a Flathub app listing.
This app bundle is checksum-verified, not independently signed. The shared runtime
is a larger first download (potentially hundreds of MB) and is shared by apps.

Sandbox permissions are deliberately documented: Wayland/X11, IPC, network for
optional user-selected Labelary rendering, device access for USB serial, system
BlueZ D-Bus access for BLE/pairing, and **read-only Omarchy theme directories**.
Direct serial access currently requires Flatpak's broad `--device=all`; this is
not a claim of a hardware-isolated sandbox. General home/host-filesystem access
is not granted; native export dialogs use the desktop file portal. Host USB
permissions, a working Bluetooth service/adapter, and desktop portals still apply.

```bash
flatpak run io.github.niimstudio.App --version
# Update the app: rerun the installer with --flatpak.
flatpak update --user                         # update installed shared runtimes
flatpak uninstall --user io.github.niimstudio.App
```

There is no background app updater or hosted app OSTree repository yet, so
`flatpak update` alone does **not** fetch new GitHub app bundles. Normal uninstall
keeps app data; do not pass `--delete-data` if you want to retain labels/settings.
The runtime remote and shared runtimes are not removed by app uninstall.

## Native: updates, migration and removal

### Stable releases versus development

Published releases are the normal user channel. Editing/building the development
checkout does not change an installed release. `main` is the stable source line;
`dev` is explicitly for testing unfinished changes. Stable updates only come from
published, non-prerelease version tags after package validation, never from `dev`.
Update notifications do not install anything until **Update now** is selected.
You can keep using an older release; a failed download/validation leaves the
current managed installation intact.

Release candidates use explicit tags such as **v0.2.1-rc.1** and are marked
prerelease, never latest stable. Opt in with the candidate's installer and
`--version v0.2.1-rc.1`; Flatpak still additionally requires `--flatpak`. This does
not change ordinary stable users' updates. A managed candidate can be offered its
final stable version later, but not older stable versions or subsequent candidates.
Back up/export important labels before testing prerelease software. Keep candidate
source checkouts separate from a pinned stable checkout.

For a stable **source checkout**, clone a release tag in a separate directory,
then follow the source build steps in README:

```bash
git clone --branch v0.2.0 --depth 1 https://github.com/Akuyumu/niimstudio.git niimstudio-stable
```

Do not switch or rebuild that directory while using it as your stable app. Keep
development in a different checkout/launcher. Published tags/assets must not be
moved or replaced; subsequent fixes get a new version. No software release can
guarantee all printers or drivers work, but ongoing development must not replace
the user's chosen baseline.

Native installs add a menu entry and `~/.local/bin/niimstudio` without editing
PATH. If that directory is not in PATH, use the app menu or the full command path.

```bash
niimstudio --version
niimstudio --update
niimstudio --uninstall
```

A managed native install checks the public release feed once per launch. When a
newer release exists, a slim bar above the footer offers **Update now**; the app
downloads the same checksum-verified bundle as `--update`, then offers **Restart**.
The update uses `--no-deps`, so it never installs system packages or asks for
sudo; if the new release needs a dependency that is missing, the terminal command
is the fallback. `NIIMSTUDIO_NO_UPDATE_CHECK=1` disables the launch check; the
version request carries no label or usage data. Source checkouts and Flatpak do
not self-update this way.

Close the app before updating from a terminal or uninstalling. Updates download
and verify a release before switching the active app. Previous releases are
retained, so running processes do not lose their assets. Native dependencies
remain maintained by your distribution. Native auto-install commands cover modern
Arch/Omarchy, Ubuntu, Debian and Fedora; other distros can use Flatpak or provide
the runtime themselves. Old distro packages are not automatically replaced with
third-party packages.

Managed code lives under `${XDG_DATA_HOME:-~/.local/share}/niimstudio-app/`, separate
from saved label data. Uninstall keeps drafts, labels, settings and source
checkouts, and leaves system dependencies installed. Unrelated launcher/menu/icon
files are not overwritten. If a source-checkout launcher exists, `--replace-source`
explicitly replaces **only its integration**, preserving the checkout and labels.

## Flickering or jitter on a particular graphics stack

v0.1.1 removes native overlay slide/fade effects and the sidebar backdrop blur.
If flickering persists, close **all** NiimStudio windows, then try one launch with
WebKit hardware acceleration disabled:

```bash
# Native:
~/.local/bin/niimstudio --software-rendering
# Or Flatpak:
flatpak run io.github.niimstudio.App --software-rendering
```

Equivalently, set `NIIMSTUDIO_RENDERER=software` for that process. A normal launch
returns to the platform renderer. No preference, driver setting, compositor rule,
or kernel configuration is changed; WebKit's sandbox remains enabled. Rendering
may be slower in this mode. Printer encoding and saved label data are unchanged.
The app is single-instance, so an already-running copy must be closed first.
These are compatibility mitigations, not proof of the original device-specific
cause; report whether normal or software mode still flickers, plus native/Flatpak
and the desktop/GPU if known. A recording is not required.

## Switching formats / data

The installer avoids creating conflicting native and Flatpak menu entries. Remove
the old format's integration before switching. It does not automatically copy or
merge libraries: native data is under `~/.local/share/niimstudio/` and
`~/.config/niimstudio/`, while Flatpak data/settings are under
`~/.var/app/io.github.niimstudio.App/`. Export/import JSON labels when migrating.
Both uninstall methods keep user data by default. Back up important labels first.

## Packaging references

v0.2.0 ships the native `tar.gz`, x86-64/ARM64 `.flatpak` bundles, `install.sh`,
and `SHA256SUMS`. Neither format includes private labels or proprietary NIIMBOT
assets; source/dependency licenses are retained. This is not an AppImage, `.deb`,
`.rpm`, or AUR release. The small installer + release download approach was
reviewed against [Zed](https://github.com/zed-industries/zed/blob/main/script/install.sh)
and [uv](https://docs.astral.sh/uv/getting-started/installation/); their code was
not copied. See CONTRIBUTING.md for isolated install tests and release builds.
