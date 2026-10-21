"""Small actionable tips; keep the original error available for troubleshooting."""


def connection_tip(error, kind="bluetooth"):
    detail = str(error).lower()
    if kind == "serial":
        return "Check the USB data cable and device permissions, then retry. See docs/HARDWARE.md; do not run the app as root."
    if "classic" in detail or "serial port" in detail:
        return "Choose the Bluetooth LE entry for this printer, not the classic/serial entry. Pairing the classic entry will not enable BLE."
    if "notsupported" in detail or "not supported" in detail:
        return "Pairing may not be supported by this BLE printer. Try Connect on the Bluetooth LE entry without pairing, with the phone's NIIMBOT app closed."
    if "authenticationcanceled" in detail or "authentication canceled" in detail:
        return "Bluetooth authentication was canceled or timed out; this does not identify a PIN requirement. Try Connect without pairing. If it still fails before services appear, capture one connection attempt with btmon rather than repeatedly pairing."
    if "before gatt service discovery" in detail:
        return "The Bluetooth link did not open, so changing printer packets cannot fix this stage. Keep the printer awake, close other printing apps and scan again. A btmon capture can show the controller's connection failure reason."
    if any(
        word in detail
        for word in ("authentication", "notauthorized", "not authorized", "rejected", "notpaired", "not paired")
    ):
        return "Try Pair for the Bluetooth LE entry, approve any prompt, then Connect again. Some printers connect without pairing."
    if "no niimbot" in detail:
        return "Choose the Bluetooth LE entry, close the phone's NIIMBOT app, and retry. If no compatible BLE service appears, try USB."
    return "Close the phone's NIIMBOT app, keep the printer awake and nearby, then retry the Bluetooth LE entry. If authentication fails, try Pair first; USB is another option."
