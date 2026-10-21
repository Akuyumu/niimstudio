/** Keep transport/negotiation failures actionable, without guessing their cause. */
export function connectionFeedback(error: unknown): { detail: string; tip: string } {
  const detail = error instanceof Error ? error.message : String(error);
  const text = detail.toLowerCase();
  let tip =
    "Open Devices, choose the Bluetooth LE entry, close the phone's NIIMBOT app, and retry with the printer awake and nearby. If authentication fails, try Pair first. USB is another option.";
  if (/classic|serial port/.test(text)) {
    tip =
      "Choose the Bluetooth LE entry with the same printer name, not classic Bluetooth serial. Pairing the classic entry will not enable BLE.";
  } else if (/authentication|notauthorized|not authorized|rejected|notpaired|not paired/.test(text)) {
    tip =
      "Open Devices → Pair for the Bluetooth LE entry, approve any prompt, then Connect again. Some printers work without pairing.";
  } else if (/usb permission|permission denied|serial device/.test(text)) {
    tip =
      "Check the USB data cable and device permissions in docs/HARDWARE.md, then retry. Do not run NiimStudio as root.";
  }
  return { detail, tip };
}
