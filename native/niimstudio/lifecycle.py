"""Opt-in timing markers; no label content or persistent telemetry."""

import json
import os
import time


def enabled():
    return bool(os.environ.get("NIIMSTUDIO_LIFECYCLE_TRACE"))


def mark(event, **fields):
    if enabled():
        print("LIFECYCLE=" + json.dumps({"event": event, "ns": time.monotonic_ns(), **fields}), flush=True)
