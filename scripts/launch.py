"""Validate the chosen interpreter/runtime once, then enter the application.

Deliberately avoids importing PyGObject here: in the optional extracted-runtime
setup that import costs ~100ms before the app process even starts. A packaged
typelib is enough to choose the runtime; the app imports GI exactly once.
"""

import os
import runpy
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]


def find_typelib(name):
    directories = [Path(item) for item in os.environ.get("GI_TYPELIB_PATH", "").split(":") if item]
    directories += [
        Path("/usr/lib/girepository-1.0"),
        Path("/usr/lib64/girepository-1.0"),
        Path("/usr/lib/x86_64-linux-gnu/girepository-1.0"),
        Path("/usr/lib/aarch64-linux-gnu/girepository-1.0"),
    ]
    return any((directory / name).is_file() for directory in directories)


if sys.version_info < (3, 11):
    if not os.environ.get("NIIMSTUDIO_PYTHON") and not os.environ.get("NIIMSTUDIO_PYTHON_RETRIED"):
        for candidate in ("/usr/bin/python3", "/usr/bin/python"):
            if Path(candidate).is_file() and not os.path.samefile(candidate, sys.executable):
                os.environ["NIIMSTUDIO_PYTHON_RETRIED"] = "1"
                os.execv(candidate, [candidate, __file__, *sys.argv[1:]])
    raise SystemExit("NiimStudio needs system Python 3.11+ with PyGObject (python3-gi / python-gobject).")

if find_typelib("WebKit-6.0.typelib"):
    # If PyGObject itself is missing, the app's import reports it plainly.
    runpy.run_module("niimstudio", run_name="__main__", alter_sys=True)
else:
    runtime = root / ".runtime/root/usr/lib"
    if not (runtime / "girepository-1.0/WebKit-6.0.typelib").is_file():
        raise SystemExit(
            "Missing WebKitGTK 6. Install webkitgtk-6.0 (Arch), gir1.2-webkit-6.0 (Debian/Ubuntu), or webkitgtk6.0 (Fedora).\n"
            "Arch/Omarchy only: an optional signed-package runtime is available via scripts/bootstrap-runtime."
        )
    os.environ["XDG_DATA_DIRS"] = (
        str(root / ".runtime/root/usr/share") + ":" + os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share")
    )
    runpy.run_path(str(root / "scripts/local-runtime.py"), run_name="__main__")
