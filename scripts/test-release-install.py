#!/usr/bin/env python3
"""Exercise the actual release without touching the developer's install/data."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
artifacts = Path(sys.argv[1] if len(sys.argv) > 1 else root / ".release").resolve()
with tempfile.TemporaryDirectory(prefix="niimstudio-install-test-") as temporary:
    home = Path(temporary) / "test user"
    home.mkdir()
    data = home / "data"
    environment = {
        **os.environ,
        "HOME": str(home),
        "XDG_DATA_HOME": str(data),
        "XDG_CONFIG_HOME": str(home / "config"),
        "XDG_CACHE_HOME": str(home / "cache"),
    }
    saved = data / "niimstudio/keep-my-label.json"
    saved.parent.mkdir(parents=True)
    saved.write_text('{"synthetic":"keep"}')
    installer = [
        sys.executable,
        str(root / "scripts/managed_install.py"),
        "install",
        "--archive",
        str(artifacts / "niimstudio-linux.tar.gz"),
        "--checksums",
        str(artifacts / "SHA256SUMS"),
    ]
    subprocess.run(installer, env=environment, check=True)
    launcher = home / ".local/bin/niimstudio"
    version = json.loads((root / "package.json").read_text())["version"]
    result = subprocess.check_output([str(launcher), "--version"], env=environment, text=True)
    assert result.strip() == "NiimStudio " + version, result
    subprocess.run(installer, env=environment, check=True)
    assert launcher.is_symlink() and saved.read_text() == '{"synthetic":"keep"}'
    if os.environ.get("NIIMSTUDIO_TEST_INSTALLED_GUI"):
        subprocess.run([str(launcher), "--smoke-test"], env=environment, check=True, timeout=90)
    subprocess.run([str(launcher), "--uninstall"], env=environment, check=True)
    assert not launcher.exists() and not launcher.is_symlink()
    assert not (data / "niimstudio-app").exists()
    assert saved.read_text() == '{"synthetic":"keep"}'
print("PASS actual bundle: install, command/version, repeat install, uninstall, preserved label data (HOME has spaces)")
