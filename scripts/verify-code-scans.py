# /// script
# requires-python = ">=3.11"
# dependencies = ["Pillow==13.0.0", "zxing-cpp==3.1.1"]
# ///
"""Independently decode actual Fabric output from the GUI smoke test.

Run: uv run scripts/verify-code-scans.py .test-results/omarchy
These are synthetic test artifacts, not files from the user's label library.
"""

import sys
from pathlib import Path

import zxingcpp
from PIL import Image

directory = Path(sys.argv[1] if len(sys.argv) > 1 else ".test-results/omarchy")
expected = {
    "qr-url.png": "https://example.com/niimstudio",
    "barcode-url.png": "https://a.co",
    "barcode-special.png": "$)",
    "ean13.png": "5901234123457",
}
for name, text in expected.items():
    with Image.open(directory / name) as image:
        result = zxingcpp.read_barcode(image)
        if result is None or result.text != text:
            raise SystemExit(f"FAIL {name}: expected {text!r}, got {result.text if result else 'no result'!r}")
        print(f"PASS {name}: {result.text}")
