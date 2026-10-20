# Printer setup and hardware validation

## First label on the B1 Pro

1. Power on the printer. Close the official mobile app and any NiimBlue browser
   tab that might still own its connection.
2. Open NiimStudio and select **Devices**.
3. For USB, use a **data-capable** cable and select the detected serial port.
   For Bluetooth, turn Bluetooth on in your desktop settings first, then **Scan for printers**.
4. Select the printer. BLE often works with **Connect** without pairing. Use
   **Pair** if a bond is required; answer the native PIN/passkey prompt using
   the printer's documented code. No default PIN is assumed.
5. Set the actual loaded label dimensions. The B1 Pro is 300 DPI: choose a
   300-DPI preset or set 11.81 dots/mm. Upstream metadata gives it 567 printhead
   pixels; the editor rounds head dimensions down to multiples of eight.
   A 40×30 mm, 300-DPI label is a sensible starting point **only if that is the
   media you actually loaded**. Do not use a 50-mm printable width blindly.
6. Open **Preview** and verify orientation, margins, density, and dithering.
   NiimBlueLib negotiates a print task. If the B1 Pro needs an override, the
   user-reported working task is `D110M_V4`; select
   it in the preview and use the lock control to remember it.
7. Choose one copy and explicitly press **Print**. Verify the physical result
   before attempting batches.

The app is never run as root and does not print, pair, reset a printer, or
flash firmware automatically. Canceling a batch stops **remaining pages** after
the current page and its submitted copies complete; it cannot unprint labels
already submitted. The preview cannot be dismissed while a job is running.

After the first successful link, the app remembers the printer and tries to
reconnect at startup or after an unexpected cable/radio disconnect. It never
replays an interrupted print. A deliberate disconnect pauses retries for that
session. Disable **Reconnect automatically** in Devices to persistently opt out.

## USB permission errors

Check the actual node using `ls -l /dev/ttyACM* /dev/ttyUSB*` and find the exact
USB vendor/product with `udevadm info --attribute-walk --name=/dev/ttyACM0`.
On a logind desktop, a narrowly targeted udev rule granting `TAG+="uaccess"`
to that specific VID/PID is preferable to world-writable serial devices.
Installing a rule requires administrator review and a replug. No rule is
installed by NiimStudio, and no guessed vendor/product ID is hardcoded.

Do not use `chmod 666 /dev/tty*`, add broad permissions, stop system services,
or change group memberships just to mask a connection error. Other programs
holding the port can also prevent a connection. Ordinary printers need not
be registered with CUPS to use this app.

## Bluetooth limitations

This implementation targets the NIIMBOT BLE service
`e7810a71-73ae-499d-8c15-faa9aef0c3f2`, with combined or separate write/notify
characteristics. Classic Bluetooth RFCOMM/SPP is not implemented. Use USB for
a classic-only device, or investigate its transport before claiming support.
The list can show all Bluetooth devices for unusual printer names, but that
does not mean non-printers or every NIIMBOT model are supported.

Scanning lasts 25 seconds and releases only this app's discovery sessions. The
app never turns adapters on/off, trusts arbitrary devices, removes existing
bonds, or replaces the desktop pairing agent. If a device is busy, close the
phone app before retrying rather than resetting its settings automatically.

## Hardware acceptance checklist

Record printer model, firmware/hardware versions, OS, connection type, and
NiimBlueLib version, without publishing full Bluetooth addresses by default.

- [ ] USB connect / negotiated model and print task / single physical label
- [ ] BLE discovery / connect / single physical label
- [ ] Optional pairing / PIN / passkey / confirmation / cancellation
- [ ] 300-DPI dimensions, print direction, offsets, density, gaps/black marks
- [ ] Text, Unicode/fonts, QR/barcode scanning, image threshold and dithering
- [ ] Multiple copies, CSV batches, cancellation at page boundary
- [ ] Cable removal or Bluetooth loss during a job, then reconnect
- [ ] Restart: draft and named templates remain available
- [ ] Theme switch: native chooser and editor update; output stays black/white

Until these are performed against the actual device, describe the native
transport as implemented and automated-tested, not hardware-verified.
