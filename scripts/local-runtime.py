"""Expose an extracted, signed Arch package in an app-only mount namespace.

WebKit has compiled-in helper paths under /usr/lib. A library search path alone
cannot relocate those helpers. This view merges just /usr/lib; it does not write
to /usr, disable WebKit's sandbox, or require administrator privileges.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path


def merge(host, overlay, destination, host_view, relative=Path()):
    destination.mkdir()
    installed = set(p.name for p in host.iterdir()) if host.is_dir() else set()
    for name in sorted(installed | set(p.name for p in overlay.iterdir())):
        original, addition, target = host / name, overlay / name, destination / name
        if addition.is_dir() and not addition.is_symlink():
            merge(original, addition, target, host_view, relative / name)
        elif addition.exists() or addition.is_symlink():
            target.symlink_to(Path("/usr/lib/.niimstudio-overlay") / relative / name)
        else:
            target.symlink_to(host_view / relative / name)


def main():
    root = Path(__file__).resolve().parents[1]
    runtime = root / ".runtime"
    with tempfile.TemporaryDirectory(prefix="view-", dir=runtime) as temporary:
        view = Path(temporary)
        merged = view / "lib"
        host_view = Path("/usr/lib/.niimstudio-host")
        merge(Path("/usr/lib"), runtime / "root/usr/lib", merged, host_view)
        (merged / ".niimstudio-host").mkdir()
        (merged / ".niimstudio-overlay").mkdir()
        env = os.environ.copy()
        env["NIIMSTUDIO_LOCAL_RUNTIME"] = "1"
        env["LD_LIBRARY_PATH"] = "/usr/lib"
        env["GI_TYPELIB_PATH"] = "/usr/lib/girepository-1.0"
        return subprocess.call(
            [
                "bwrap",
                "--bind",
                "/",
                "/",
                "--dev-bind",
                "/dev",
                "/dev",
                "--proc",
                "/proc",
                "--ro-bind",
                str(merged),
                "/usr/lib",
                "--die-with-parent",
                "--ro-bind",
                "/usr/lib",
                str(host_view),
                "--ro-bind",
                str(runtime / "root/usr/lib"),
                "/usr/lib/.niimstudio-overlay",
                sys.executable,
                "-m",
                "niimstudio",
                *sys.argv[1:],
            ],
            env=env,
        )


raise SystemExit(main())
