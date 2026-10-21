"""Opt-in release checks for managed native installs.

Only a version query is sent to the public GitHub API. Nothing about labels,
printers, or usage is uploaded, and the update itself still goes through the
existing checksum-verifying installer.
"""

import json
import os
import re
import sys
from pathlib import Path

LATEST_URL = "https://api.github.com/repos/Akuyumu/niimstudio/releases/latest"
VERSION = re.compile(r"v?(\d+)\.(\d+)\.(\d+)")


def version_tuple(value):
    match = VERSION.fullmatch((value or "").strip())
    return tuple(int(part) for part in match.groups()) if match else None


def managed_root(root, environ=None):
    """Return the install root only for a managed native bundle."""
    environ = os.environ if environ is None else environ
    if environ.get("FLATPAK_ID"):
        return None
    root = Path(root)
    try:
        manifest = json.loads((root / "release.json").read_text())
    except (OSError, ValueError):
        return None
    if manifest.get("product") != "niimstudio" or version_tuple(manifest.get("version", "")) is None:
        return None
    return root


def updates_enabled(environ=None):
    environ = os.environ if environ is None else environ
    return not environ.get("NIIMSTUDIO_NO_UPDATE_CHECK")


def fetch_latest(current_version, timeout=5):
    import urllib.request

    request = urllib.request.Request(
        LATEST_URL,
        headers={
            "User-Agent": f"NiimStudio/{current_version}",
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read(64 * 1024))
    if data.get("draft") or data.get("prerelease"):
        return None
    tag = data.get("tag_name")
    latest = version_tuple(tag)
    current = version_tuple(current_version)
    if latest is None or current is None or latest <= current:
        return None
    return {"version": ".".join(str(part) for part in latest), "tag": tag}


def update_command(root, tag):
    return [
        sys.executable,
        str(Path(root) / "scripts/managed_install.py"),
        "update",
        "--version",
        tag,
        "--yes",
        "--no-deps",
    ]


def run_update(root, tag, timeout=180):
    import subprocess

    result = subprocess.run(
        update_command(root, tag),
        capture_output=True,
        text=True,
        timeout=timeout,
        env={**os.environ, "NIIMSTUDIO_NO_UPDATE_CHECK": "1"},
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip().splitlines()
        return False, detail[-1][:300] if detail else "The update did not finish."
    return True, ""
