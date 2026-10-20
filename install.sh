#!/usr/bin/env bash
# Download a prebuilt release. Never run this script with sudo.
set -euo pipefail

die() { echo "NiimStudio: $*" >&2; exit 1; }

confirm() {
  local answer=""
  [[ "${assume_yes:-0}" -eq 1 ]] && return 0
  if ! { printf '%s [y/N] ' "$1" > /dev/tty; read -r answer < /dev/tty; } 2>/dev/null; then
    die "No terminal for confirmation. Review --help and use --yes for explicit unattended consent"
  fi
  [[ "$answer" == y || "$answer" == Y || "$answer" == yes ]] || die "Canceled"
}

find_python() {
  local candidate
  for candidate in /usr/bin/python3 /usr/bin/python; do
    if [[ -x "$candidate" ]] && "$candidate" -c 'import sys; assert sys.version_info >= (3, 11)' 2>/dev/null; then
      echo "$candidate"
      return 0
    fi
  done
  return 1
}

runtime_ready() {
  [[ -n "$python" ]] || return 1
  "$python" - <<'PY' 2>/dev/null
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("WebKit", "6.0")
from gi.repository import Gtk, Adw, WebKit
assert (Gtk.get_major_version(), Gtk.get_minor_version()) >= (4, 12)
assert (Adw.get_major_version(), Adw.get_minor_version()) >= (1, 5)
PY
}

sandbox_ready() {
  command -v bwrap >/dev/null || return 1
  # Probe an empty, read-only user namespace. Never weaken host security policy.
  bwrap --unshare-user --ro-bind / / --dev /dev --proc /proc -- /usr/bin/true 2>/dev/null
}

dependency_command() {
  local kind="${1:-native}"
  local release_file="${2:-/etc/os-release}"
  local ID="" ID_LIKE=""
  [[ ! -f "$release_file" ]] || source "$release_file"
  case " $ID $ID_LIKE " in
    *" arch "*|*" omarchy "*) deps=(pacman -S --needed --noconfirm gtk4 libadwaita python python-gobject webkitgtk-6.0 bluez) ;;
    *" ubuntu "*|*" debian "*) deps=(apt-get install -y python3 python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 gir1.2-webkit-6.0 bluez) ;;
    *" fedora "*) deps=(dnf install -y python3 python3-gobject gtk4 libadwaita webkitgtk6.0 bluez) ;;
    *) [[ "$kind" == flatpak ]] || return 1 ;;
  esac
  if [[ "$kind" == flatpak ]]; then
    case " $ID $ID_LIKE " in
      *" arch "*|*" omarchy "*) deps=(pacman -S --needed --noconfirm flatpak) ;;
      *" ubuntu "*|*" debian "*) deps=(apt-get install -y flatpak) ;;
      *" fedora "*|*" rhel "*) deps=(dnf install -y flatpak) ;;
      *" suse "*|*" opensuse "*|*" opensuse-tumbleweed "*|*" opensuse-leap "*) deps=(zypper --non-interactive install flatpak) ;;
      *" alpine "*) deps=(apk add flatpak) ;;
      *" void "*) deps=(xbps-install -Sy flatpak) ;;
      *) return 1 ;;
    esac
  fi
}

download() {
  curl --fail --silent --show-error --location --proto '=https' --proto-redir '=https' \
    --tlsv1.2 --connect-timeout 20 --max-time 300 --retry 2 --max-filesize 52428800 \
    --output "$2" "$1"
}

install_flatpak_bundle() {
  local output status
  if output="$(LC_ALL=C flatpak install --user -y --reinstall "$1" 2>&1)"; then
    printf '%s\n' "$output"
    return 0
  else
    status=$?
    # Flatpak rejects an identical local-bundle commit even with --reinstall.
    # Do not confuse a failed upgrade or another install error with this case.
    if [[ "$output" == *"This version of io.github.niimstudio.App is already installed"* ]] && \
       flatpak --user info io.github.niimstudio.App >/dev/null 2>&1; then
      echo "NiimStudio is already up to date."
      return 0
    fi
    printf '%s\n' "$output" >&2
    return "$status"
  fi
}

main() {
  local version=latest mode=ask replace_source=0 check_only=0 python="" temp="" expected actual base
  local format=auto assume_yes=0 asset=niimstudio-linux.tar.gz arch remote_url
  local -a deps=() extra=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --version) [[ $# -ge 2 ]] || die "--version needs a tag"; version="$2"; shift 2 ;;
      --install-deps) mode=install; shift ;;
      --no-deps) mode=skip; shift ;;
      --replace-source) replace_source=1; shift ;;
      --native) format=native; shift ;;
      --flatpak) format=flatpak; shift ;;
      --yes) assume_yes=1; shift ;;
      --check) check_only=1; shift ;;
      -h|--help)
        echo "Usage: bash install.sh [--native | --flatpak] [--version v0.1.0] [--install-deps | --no-deps] [--replace-source] [--check] [--yes]"
        echo "Installs/updates a prebuilt release for this user. No source build or shell-profile changes."
        echo "Default: native. Flatpak is a separate explicit route (--flatpak) and is never installed automatically."
        echo "Missing native dependencies require confirmation, or explicit --install-deps."
        return ;;
      *) die "Unknown option: $1 (see --help)" ;;
    esac
  done
  [[ "$version" == latest || "$version" =~ ^v[0-9]+\.[0-9]+\.[0-9]+(-[A-Za-z0-9.-]+)?$ ]] || die "Invalid release tag"
  [[ "$(uname -s)" == Linux ]] || die "This installer supports Linux only"
  [[ $EUID -ne 0 ]] || die "Run as your normal user, not with sudo"
  [[ "${HOME:-}" == /* ]] || die "HOME must be an absolute directory"
  command -v curl >/dev/null || die "Install curl first, then rerun this command"
  python="$(find_python || true)"
  if [[ "$format" == auto ]]; then
    # Native is the default route. Flatpak is never selected, downloaded, or
    # installed implicitly: it is an explicit, separate choice (--flatpak).
    format=native
    if command -v flatpak >/dev/null && flatpak --user info io.github.niimstudio.App >/dev/null 2>&1; then
      die "A Flatpak installation exists. Update it with --flatpak, or remove it before installing the native app (label data is kept)."
    fi
  fi
  echo "Installation format: $format"
  if [[ "$format" == flatpak ]]; then
    case "$(uname -m)" in
      x86_64|amd64) arch=x86_64 ;;
      aarch64|arm64) arch=aarch64 ;;
      *) die "Flatpak releases support x86-64 and ARM64. Other architectures need a compatible native runtime (--native)" ;;
    esac
    asset="niimstudio-linux-$arch.flatpak"
    if ! command -v flatpak >/dev/null; then
      dependency_command flatpak || die "Install Flatpak using your distribution's instructions, then rerun. See https://flatpak.org/setup/"
      printf 'Missing Flatpak. Package command: sudo'; printf ' %q' "${deps[@]}"; printf '\n'
      [[ $check_only -eq 0 ]] || return 1
      [[ "$mode" != skip ]] || die "Flatpak is missing (--no-deps); no changes made"
      [[ "$mode" == install ]] || confirm "Install Flatpak using the package command above?"
      command -v sudo >/dev/null || die "Ask your administrator to install Flatpak first"
      if [[ "${deps[0]}" == apt-get ]]; then sudo apt-get update; fi
      sudo "${deps[@]}"
    fi
    [[ $check_only -eq 0 ]] || { echo "Flatpak is available; GNOME runtime will be installed as needed"; return 0; }
    if flatpak --user info io.github.niimstudio.App >/dev/null 2>&1; then
      echo "Updating the user Flatpak installation"
    elif [[ -e "$HOME/.local/bin/niimstudio" || -L "$HOME/.local/bin/niimstudio" ]]; then
      die "An existing native/source launcher was found. Keep using --native, or uninstall its integration before switching formats; label data is kept separate"
    fi
    remote_url="$(flatpak remotes --user --columns=name,url | awk '$1 == "niimstudio-runtime" {print $2}')"
    if [[ -z "$remote_url" ]]; then
      confirm "Add the Flathub runtime repository for your user (niimstudio-runtime)?"
      flatpak remote-add --user niimstudio-runtime https://flathub.org/repo/flathub.flatpakrepo
    elif [[ "$remote_url" != https://dl.flathub.org/repo/ && "$remote_url" != https://dl.flathub.org/repo ]]; then
      die "The existing niimstudio-runtime remote has an unexpected URL; refusing to alter it"
    fi
  elif runtime_ready && ! sandbox_ready; then
    die "This host blocks the native WebKit sandbox. Flatpak is the separate explicit route (--flatpak); no kernel/security settings were changed"
  elif ! runtime_ready; then
    echo "Needs Python 3.11+, PyGObject, GTK 4.12+, Libadwaita 1.5+, and WebKitGTK 6."
    echo "This is the native route. Flatpak is separate and never installed automatically;"
    echo "use --flatpak only if you explicitly want Flatpak and its GNOME runtime."
    dependency_command || die "Install the equivalent native packages for your distribution; see docs/INSTALLING.md"
    echo "System dependency command (BlueZ is included for Bluetooth):"
    printf '  sudo'; printf ' %q' "${deps[@]}"; printf '\n'
    [[ $check_only -eq 0 ]] || return 1
    [[ "$mode" != skip ]] || die "Dependencies are missing; no changes made (--no-deps)"
    [[ "$mode" != ask ]] || confirm "Install these packages now?"
    command -v sudo >/dev/null || die "sudo is unavailable. Ask your administrator to install the packages above"
    if [[ "${deps[0]}" == apt-get ]]; then sudo apt-get update; fi
    sudo "${deps[@]}"
    python="$(find_python || true)"
    runtime_ready || die "Your native runtime is still too old/incomplete. A newer distribution may be needed"
    sandbox_ready || die "This host blocks the native WebKit sandbox. Use --flatpak instead of disabling security protections"
  fi
  [[ "$format" != native ]] || echo "Native runtime: ready"
  [[ $check_only -eq 0 ]] || return 0
  [[ "$format" != native ]] || command -v tar >/dev/null || die "Install tar first"
  command -v sha256sum >/dev/null || die "Install coreutils (sha256sum) first"
  temp="$(mktemp -d "${TMPDIR:-/tmp}/niimstudio-install.XXXXXXXX")"
  # Only this newly created temporary directory is removed.
  trap '[[ -z "${temp:-}" ]] || rm -rf -- "$temp"' EXIT
  base="https://github.com/Akuyumu/niimstudio/releases"
  if [[ "$version" == latest ]]; then base+="/latest/download"; else base+="/download/$version"; fi
  echo "Downloading NiimStudio $version…"
  download "$base/$asset" "$temp/$asset"
  download "$base/SHA256SUMS" "$temp/SHA256SUMS"
  expected="$(awk -v asset="$asset" '$2 == asset {print $1}' "$temp/SHA256SUMS")"
  [[ "$expected" =~ ^[a-f0-9]{64}$ ]] || die "Release checksum is missing or malformed"
  actual="$(sha256sum "$temp/$asset")"
  [[ "${actual%% *}" == "$expected" ]] || die "Checksum mismatch; nothing installed"
  echo "Release SHA-256 verified"
  if [[ "$format" == flatpak ]]; then
    echo "Flatpak needs display, network (optional ZPL import), USB serial devices and BlueZ access."
    echo "Only Omarchy theme directories are exposed read-only; general home access is not granted."
    confirm "Install NiimStudio and its GNOME runtime for your user?"
    install_flatpak_bundle "$temp/$asset"
    echo "Installed. Open NiimStudio from your app menu, or: flatpak run io.github.niimstudio.App"
    echo "Update: rerun this installer with --flatpak"
    echo "Remove (keeps data): flatpak uninstall --user io.github.niimstudio.App"
  else
    if command -v flatpak >/dev/null && flatpak --user info io.github.niimstudio.App >/dev/null 2>&1; then
      die "A user Flatpak install already exists. Remove it before switching to native; its label data is kept"
    fi
    # Extract exactly one file to stdout, never archive-supplied paths to disk.
    tar -xOzf "$temp/$asset" niimstudio/scripts/managed_install.py > "$temp/managed_install.py"
    [[ $replace_source -eq 0 ]] || extra+=(--replace-source)
    "$python" "$temp/managed_install.py" install --archive "$temp/$asset" \
      --checksums "$temp/SHA256SUMS" "${extra[@]}"
  fi
  rm -rf -- "$temp"
  temp=""
}

# Keep all work inside main so a truncated piped download cannot partially run it.
main "$@"
