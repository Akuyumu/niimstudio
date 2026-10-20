#!/usr/bin/env python3
"""Package built JS + Python, not a source checkout or bundled system runtime."""

import argparse
import gzip
import hashlib
import io
import json
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def release_files(root):
    files = {}
    for directory in ("dist", "native/niimstudio", "packaging"):
        for path in (root / directory).rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix not in (".pyc", ".pyo"):
                files[path.relative_to(root).as_posix()] = path
    for name in (
        "LICENSE",
        "README.md",
        "install.sh",
        "scripts/niimstudio",
        "scripts/system-python",
        "scripts/managed_install.py",
        "docs/INSTALLING.md",
        "docs/HARDWARE.md",
        "docs/UPSTREAM.md",
        "docs/STATUS.md",
    ):
        files[name] = root / name
    return files


def dependency_notices(root):
    """Conservatively include notices for all installed packages, including tools."""
    files, packages = {}, []
    lock = json.loads((root / "package-lock.json").read_text())
    for relative, metadata in sorted(lock["packages"].items()):
        if not relative.startswith("node_modules/") or not (root / relative).is_dir():
            continue
        package = root / relative
        info = json.loads((package / "package.json").read_text())
        packages.append(
            {
                "name": info.get("name", relative),
                "version": info.get("version"),
                "license": info.get("license", metadata.get("license", "See package notices")),
            }
        )
        for path in package.iterdir():
            if path.is_file() and path.name.upper().startswith(("LICENSE", "LICENCE", "COPYING", "NOTICE", "OFL")):
                files["licenses/" + path.relative_to(root / "node_modules").as_posix()] = path
    required = (
        "@mmote/niimbluelib/LICENSE",
        "fabric/LICENSE",
        "svelte/LICENSE.md",
        "pdfjs-dist/LICENSE",
        "@fontsource-variable/noto-sans/LICENSE",
    )
    for name in required:
        if "licenses/" + name not in files:
            raise ValueError(f"Missing bundled dependency notice: {name}")
    return files, json.dumps(packages, indent=2).encode() + b"\n"


def package_release(output):
    version = json.loads((ROOT / "package.json").read_text())["version"]
    if not (ROOT / "dist/index.html").is_file():
        raise ValueError("Run npm ci --ignore-scripts && npm run build first")
    files = release_files(ROOT)
    notices, metadata = dependency_notices(ROOT)
    files.update(notices)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    generated = {
        "release.json": json.dumps(
            {
                "product": "niimstudio",
                "format": 1,
                "version": version,
                "commit": commit,
                "platform": "linux",
                "architecture": "any",
                "systemRuntimeRequired": True,
            },
            indent=2,
        ).encode()
        + b"\n",
        "licenses/packages.json": metadata,
    }
    output.mkdir(parents=True, exist_ok=True)
    archive = output / "niimstudio-linux.tar.gz"
    # Stable order, timestamps, ownership and gzip header for reproducible content.
    with (
        archive.open("wb") as raw,
        gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0) as compressed,
        tarfile.open(fileobj=compressed, mode="w") as bundle,
    ):
        for name in sorted(files.keys() | generated.keys()):
            data = generated[name] if name in generated else files[name].read_bytes()
            entry = tarfile.TarInfo("niimstudio/" + name)
            entry.size = len(data)
            entry.mode = 0o755 if name in ("install.sh", "scripts/niimstudio", "scripts/system-python") else 0o644
            bundle.addfile(entry, io.BytesIO(data))
    installer = output / "install.sh"
    installer.write_bytes((ROOT / "install.sh").read_bytes())
    with (output / "SHA256SUMS").open("w") as checksums:
        for file in (archive, installer):
            checksums.write(f"{hashlib.sha256(file.read_bytes()).hexdigest()}  {file.name}\n")
    print(f"Packaged NiimStudio {version}: {archive} ({archive.stat().st_size:,} bytes)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / ".release")
    package_release(parser.parse_args().output)
