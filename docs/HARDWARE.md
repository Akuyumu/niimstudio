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
5. The app reads the printer's model/capabilities and paper information. For a
   recognized B1 Pro it selects 300 DPI and top feed. Valid reported dimensions
   automatically size an empty/new canvas; existing artwork gets a confirmation
   first. If usable dimensions are not reported, choose the size on the roll
   packaging in **Label stock**. There are no raw size/DPI/direction controls in
   the desktop UI. The B1 Pro profile has 567 printhead pixels; widths are rounded
   down to multiples of eight, and oversized presets are unavailable. Choose
   40×30 mm **only if that is the stock actually loaded**; 50 mm exceeds its head.
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

## Automatic stock setup

Paper dimensions come from NiimBlueLib's validated paper-info response, not from
guessing a roll size by printer model or RFID product code. Reported label height
excludes its gap. Pixel/mm consistency, printhead width, finite positive sizes,
and protocol byte alignment are checked before use. DPI comes from capabilities
when available, otherwise the known model profile; feed direction comes from that
profile. Recognized media type also sets gaps/black-mark handling in Preview.

Older firmware, third-party/non-RFID stock, continuous rolls without a finite
label length, and special tail stock may not provide usable dimensions. These
use the fixed-size stock picker; technical adjustment fields stay hidden. Offline
presets use a 203-DPI preview and are checked against the connected profile before
printing. The app does not measure cut shape/radius; it preserves explicit stock
shapes and shows ordinary rounded stock with approximate corners in both views.

Changing canvas size does not silently scale or rearrange artwork. A confirmation
protects existing designs; Undo restores the previous canvas size. Printing is
blocked until the design matches detected or explicitly chosen stock. This logic
has synthetic-metadata tests, but real B1 Pro stock reporting still needs testing.

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
- [ ] Reported stock auto-setup, non-reporting-roll picker, safe roll-change prompt
- [ ] Text, Unicode/fonts, QR/barcode scanning, image threshold and dithering
- [ ] Multiple copies, CSV batches, cancellation at page boundary
- [ ] Cable removal or Bluetooth loss during a job, then reconnect
- [ ] Restart: draft and named templates remain available
- [ ] Theme switch: native chooser and editor update; output stays black/white

Until these are performed against the actual device, describe the native
transport as implemented and automated-tested, not hardware-verified.
