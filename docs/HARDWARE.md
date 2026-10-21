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
    the desktop UI. A B1 Pro supports 20–50 mm label widths: physical roll width is
    not printhead width. **50×30 mm is supported**, with non-printable edge margins.
    The printable canvas uses the reported head width (576 px on the tested unit)
    or the library's conservative 567 px fallback, byte-aligned downwards. The
    picker hides presets outside the known physical media limits. Choose the
    actual roll size, not the closest-looking preset.
6. Open **Preview**, check the image and margins, and set **Copies**. The printer's
    protocol is selected automatically. Optional image processing, print darkness,
    speed, material and alignment controls are under **Advanced**, with plain-language
    hover descriptions. Ordinary printing needs no protocol-task selection.
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
has synthetic-metadata tests. A user screenshot now confirms a real dimensions
response, but it showed 50×24 mm for a roll the user identified as 50×30 mm. That
discrepancy is unresolved: inspect **Settings → Printer and roll details → paper**,
particularly `totalHeight` and `gapHeight`, rather than assuming the displayed
height is correct or silently rewriting the parser. The stock dialog explains
that NiimBlueLib subtracts the reported gap from the reported feed length.

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

The B1 Pro can appear twice with the same name and different addresses: one
classic Bluetooth Serial Port entry and one BLE entry. Choose **Connect** on
the BLE entry first. Known classic-only services are hidden unless **Show all
Bluetooth devices** is enabled; then they are labelled unsupported and cannot
be selected. Pairing that entry does not enable the BLE transport. An entry
whose BLE services have not been discovered yet is labelled a candidate, not
promised as supported.

A generic PIN/passkey failure in the desktop Bluetooth panel is not evidence
that the printer needs a code. Cancel it and try the BLE entry without pairing,
with the phone's NIIMBOT app closed. Only enter a PIN if the device's own
documentation calls for one; do not guess codes or remove existing bonds.
Connection/pairing failures stay visible in Devices with the original error
and a short next-step tip. Connection negotiation failures after the picker
closes appear as a dismissible error with **Open Devices / retry** in the editor.
Use **Cancel pairing** if pairing stalls without a prompt; it does not remove a
bond or reset Bluetooth. Classic serial is a Bluetooth radio protocol, not a USB
port. If BLE connection times out before service discovery, temporarily disable
the phone's Bluetooth and retry with the printer awake. Do not disconnect a working
USB session just to run another diagnostic without saving your work first.

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

### B1 Pro connection validation (development, 2026-10-21)

An independent Bleak 3.0.2 probe established the LE link and enabled notifications
without pairing. The original native transport was intermittent: one of three
attempts timed out, while two completed the protocol handshake. A D-Bus trace
also caught a brief connection followed by `le-connection-abort-by-local` before
service discovery. [Bleak's BlueZ backend](https://github.com/hbldh/bleak/blob/develop/bleak/backends/bluezdbus/client.py)
explicitly handles that transient error.

The native transport now refreshes the LE advertisement, shares/refcounts only
its own chooser/connection discovery session, prefers the known combined
NIIMBOT characteristic, and retries one local-abort/timeout after canceling its
own pending target connection. Authentication errors are not retried blindly;
there is no automatic pairing, bond removal or adapter reset. The chooser shows
link, service-discovery and notification progress, not an inert Connect button.

With that change, **three consecutive native connect/handshake/heartbeat/disconnect
cycles passed** on B1 Pro model 4097, firmware 2.12, protocol 5, reporting a 576 px
head. Each received 14 notifications and three valid heartbeat-info responses.
The handshake used the pinned NiimBlueLib 0.47.0 over the actual native GATT
transport, not a newly implemented packet stack. Every diagnostic link was cleaned
up. USB was not opened or closed by the tests. No Pair, print, reset, calibration,
or setting-write commands were sent; paper-info opcode 0x59 was deliberately
excluded from this connection-only probe. Physical BLE printing, power-cycle and
mid-print radio-loss tests remain unverified.

`btmon` is installed on the test machine but requires additional privileges to
capture HCI traffic. No permissions were changed and no privileged capture was
started. Private D-Bus/protocol diagnostics stay local, not in this repository.
Only if failures recur should a short, user-approved `btmon -w` capture be made
and opened in Wireshark. Such captures can include device identifiers and private
Bluetooth traffic; do not attach them publicly without review.

## Printer settings (development checkout)

Open **Settings** at the top right for power/connection sounds, sleep/auto-off and
the app's reconnect preference. Printer changes are sent only on a user action
and are read back before success is shown. Unknown/unsupported reads hide controls
rather than presenting them as off. A readable value does not prove a write will
succeed: each change is independently verified. Matching values get a small green
confirmation; mismatches retain the actual reported value and a persistent error.
If the new value cannot be read, the control is hidden until refresh instead of
showing a stale value as truth. Temporary success banners clear after 3.5 seconds;
errors do not. Settings lock while printing. No reset, calibration, paper feed or
firmware operation is included.

The protocol exposes sleep mode codes: 1/2 are usually 15/30 minutes, 3 is 45/60
minutes, and 4 is 60 minutes or never depending on model/firmware. The UI labels
that ambiguity rather than inventing an unverified disable code. Reading back
mode 4 confirms the code was saved, **not** that a particular B1 Pro firmware will
never sleep. See [NiimBlueLib's documented modes](https://libdocs.niim.blue/enums/API.AutoShutdownTime.html).

**Printer and roll details** shows read-only model/firmware, RFID presence/product
code and the paper-info result, including read failures. It omits printer/roll
serials, tag UUIDs and label artwork. An RFID product code is not a size: some
firmware returns an identity but no extended dimensions. Do not infer dimensions
from the printer model or a vaguely matching SKU. The stock picker can remember
a size you explicitly choose for that product on that model; subsequent use is
labelled **Saved roll**, not measured/Auto, and **Change saved roll size** clears
the association. Untagged rolls still need manual selection.

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

Only the BLE connection/handshake/heartbeat stages described above have agent-run
hardware validation; the user separately confirms USB connection. The combined
connect-and-print checklist items are still unchecked because physical prints
have not been verified. Do not extrapolate these results to all printer models.
