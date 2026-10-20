"""Expose an extracted, signed Arch package in an app-only mount namespace.

WebKit has compiled-in helper paths under /usr/lib. A library search path alone
cannot relocate those helpers. This view merges just /usr/lib; it does not write
to /usr, disable WebKit's sandbox, or require administrator privileges.
"""

import os
import subprocess
import sys
from pathlib import Path

from niimstudio.lifecycle import mark
from niimstudio.runtime_view import HOST_VIEW, runtime_view


def main():
    mark("runtime_start")
    root = Path(__file__).resolve().parents[1]
    runtime = root / ".runtime"
    with runtime_view(runtime) as merged:
        mark("runtime_view_ready")
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
                str(HOST_VIEW),
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
