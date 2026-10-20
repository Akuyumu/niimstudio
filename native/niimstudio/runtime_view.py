"""Reusable app-only library views for the optional extracted Arch runtime."""

import fcntl
import hashlib
import json
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

HOST_VIEW = Path("/usr/lib/.niimstudio-host")
OVERLAY_VIEW = Path("/usr/lib/.niimstudio-overlay")


def signature(host, overlay):
    """Only merged directory listings matter; symlinks still point at live files."""
    directories = []

    def visit(original, addition):
        for directory in (original, addition):
            stat = directory.stat() if directory.is_dir() else None
            directories.append((str(directory), (stat.st_dev, stat.st_ino, stat.st_mtime_ns) if stat else None))
        for child in sorted(addition.iterdir()):
            if child.is_dir() and not child.is_symlink():
                visit(original / child.name, child)

    visit(host, overlay)
    return hashlib.sha256(json.dumps([1, directories], sort_keys=True).encode()).hexdigest()


def merge(host, overlay, destination, relative=Path()):
    destination.mkdir()
    installed = set(p.name for p in host.iterdir()) if host.is_dir() else set()
    for name in sorted(installed | set(p.name for p in overlay.iterdir())):
        original, addition, target = host / name, overlay / name, destination / name
        if addition.is_dir() and not addition.is_symlink():
            merge(original, addition, target, relative / name)
        elif addition.exists() or addition.is_symlink():
            target.symlink_to(OVERLAY_VIEW / relative / name)
        else:
            target.symlink_to(HOST_VIEW / relative / name)


def prune(cache, current):
    views = sorted(
        (
            path
            for path in cache.iterdir()
            if path.is_dir()
            and not path.is_symlink()
            and len(path.name) == 64
            and all(c in "0123456789abcdef" for c in path.name)
            and (path / ".niimstudio-view").is_file()
        ),
        key=lambda path: path.stat().st_mtime_ns,
        reverse=True,
    )
    for view in views[2:]:
        if view == current:
            continue
        with (view / ".use-lock").open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                continue  # An older running app still has this tree mounted.
            shutil.rmtree(view)


@contextmanager
def runtime_view(runtime, host=Path("/usr/lib")):
    runtime, host = Path(runtime).resolve(), Path(host).resolve()
    overlay = runtime / "root/usr/lib"
    cache = runtime / "view-cache"
    cache.mkdir(mode=0o700, exist_ok=True)
    with (cache / ".build-lock").open("a") as build_lock:
        fcntl.flock(build_lock, fcntl.LOCK_EX)
        key = signature(host, overlay)
        view = cache / key
        if not (view / ".niimstudio-view").is_file():
            with tempfile.TemporaryDirectory(prefix=".building-", dir=cache) as temporary:
                staging = Path(temporary)
                merge(host, overlay, staging / "lib")
                (staging / "lib/.niimstudio-host").mkdir()
                (staging / "lib/.niimstudio-overlay").mkdir()
                if signature(host, overlay) != key:
                    raise RuntimeError("System libraries changed while preparing the runtime; relaunch NiimStudio")
                (staging / ".niimstudio-view").write_text("NiimStudio generated library view v1\n")
                staging.rename(view)
        use_lock = (view / ".use-lock").open("a")
        fcntl.flock(use_lock, fcntl.LOCK_SH)
        prune(cache, view)
    try:
        yield view / "lib"
    finally:
        use_lock.close()
