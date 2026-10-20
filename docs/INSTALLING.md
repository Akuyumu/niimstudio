# Installing NiimStudio v0.1.0

## One command

```bash
curl -fsSL https://raw.githubusercontent.com/Akuyumu/niimstudio/main/install.sh | bash
```

Needs `curl` and Bash on a Linux desktop. Open **NiimStudio** from your app menu
after installation. No Git, Node.js, npm, pip, AUR, or source checkout is required.
The installer never launches the app, connects a printer, or prints a test label.
**Run as your normal user, not with sudo.** Only explicitly approved system-package
installation uses sudo. There are no new `.deb`/`.rpm` repositories to configure.

## How the single script chooses a format

| Environment | Default |
| --- | --- |
| Existing NiimStudio user Flatpak | Update the Flatpak |
| Existing native/source launcher | Keep the native route; source replacement needs opt-in |
| Python 3.11+, PyGObject, GTK 4.12+, Libadwaita 1.5+, WebKitGTK 6 available | Small prebuilt native bundle |
| Native runtime missing/too old | Offer Flatpak, with a maintained GNOME runtime |

Flatpak bundles cover **x86-64 and ARM64**. A Flatpak-capable desktop is required;
that covers many older Ubuntu/Debian, Fedora, Arch/Omarchy, openSUSE and other
Linux desktops without replacing their GTK/WebKit packages. It does **not** mean
every old kernel, 32-bit system, container, headless server, or distribution has
been tested. Unsupported systems stop with instructions rather than pretending
installation succeeded. Native bundles are architecture-neutral but require the
correct system Python/GI/native libraries for that architecture.

If Flatpak is missing, the script offers its normal distribution package using
apt, pacman, dnf, zypper, apk, or xbps where recognized. Other distributions get
[Flatpak setup instructions](https://flatpak.org/setup/), then can rerun the same
script. Flatpak must be supported/configured by the host; the installer does not
edit NixOS configuration or enable kernel features/system services itself.

## Inspect first or choose a format/version

This executes project code you choose to trust. For an inspect-before-running flow:

```bash
curl -fsSLo niimstudio-install.sh https://raw.githubusercontent.com/Akuyumu/niimstudio/v0.1.0/install.sh
less niimstudio-install.sh
bash niimstudio-install.sh --version v0.1.0
```

```bash
bash niimstudio-install.sh --flatpak           # always use the bundled GNOME runtime
bash niimstudio-install.sh --native            # use/install distro-native GTK/WebKit
bash niimstudio-install.sh --check             # no app install or package changes
bash niimstudio-install.sh --no-deps           # never install system packages
bash niimstudio-install.sh --install-deps      # explicitly authorize missing system packages
```

Default confirmation reads `/dev/tty`, so it works with piped input. With no
terminal it stops rather than assuming consent. `--yes` explicitly accepts the
otherwise-interactive package, runtime-repository and app-install prompts; use
only after reviewing this behavior. `--no-deps` does not prohibit downloading a
Flatpak runtime into your user Flatpak installation. The script does not modify
shell profiles, broad USB permissions, Bluetooth agents or bonds. Package-manager
maintainer scripts may perform their normal service setup.

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

Native installs add a menu entry and `~/.local/bin/niimstudio` without editing
PATH. If that directory is not in PATH, use the app menu or the full command path.

```bash
niimstudio --version
niimstudio --update
niimstudio --uninstall
```

Close the app before updating/uninstalling. Updates download and verify a release
before switching the active app. Previous releases are retained, so running
processes do not lose their assets. Native dependencies remain maintained by your
distribution. Native auto-install commands cover modern Arch/Omarchy, Ubuntu,
Debian and Fedora; other distros can use Flatpak or provide the runtime themselves.
Old distro packages are not automatically replaced with third-party packages.

Managed code lives under `${XDG_DATA_HOME:-~/.local/share}/niimstudio-app/`, separate
from saved label data. Uninstall keeps drafts, labels, settings and source
checkouts, and leaves system dependencies installed. Unrelated launcher/menu/icon
files are not overwritten. If a source-checkout launcher exists, `--replace-source`
explicitly replaces **only its integration**, preserving the checkout and labels.

## Switching formats / data

The installer avoids creating conflicting native and Flatpak menu entries. Remove
the old format's integration before switching. It does not automatically copy or
merge libraries: native data is under `~/.local/share/niimstudio/` and
`~/.config/niimstudio/`, while Flatpak data/settings are under
`~/.var/app/io.github.niimstudio.App/`. Export/import JSON labels when migrating.
Both uninstall methods keep user data by default. Back up important labels first.

## Packaging references

v0.1.0 ships the native `tar.gz`, x86-64/ARM64 `.flatpak` bundles, `install.sh`,
and `SHA256SUMS`. Neither format includes private labels or proprietary NIIMBOT
assets; source/dependency licenses are retained. This is not an AppImage, `.deb`,
`.rpm`, or AUR release. The small installer + release download approach was
reviewed against [Zed](https://github.com/zed-industries/zed/blob/main/script/install.sh)
and [uv](https://docs.astral.sh/uv/getting-started/installation/); their code was
not copied. See CONTRIBUTING.md for isolated install tests and release builds.
