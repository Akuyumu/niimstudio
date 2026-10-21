/** Existing NiimBlueLib operations only; never invent model-specific command codes. */
import { SoundSettingsItemType, type AutoShutdownTime, type NiimbotProtocol } from "@mmote/niimbluelib";

export const sleepModes = [
  { value: 1, label: "15 minutes (typical)" },
  { value: 2, label: "30 minutes (typical)" },
  { value: 3, label: "45 / 60 minutes (firmware dependent)" },
  { value: 4, label: "Never / 60 minutes (firmware dependent)" },
] as const;

export function offeredSleepModes(range?: { min: number; max: number }) {
  // Only interpret a range as mode indexes when it fits the documented codes;
  // some firmware exposes a minutes-based range instead.
  if (
    range &&
    Number.isInteger(range.min) &&
    Number.isInteger(range.max) &&
    range.min >= 0 &&
    range.max <= 4 &&
    range.min <= range.max
  ) {
    return sleepModes.filter((mode) => mode.value >= range.min && mode.value <= range.max);
  }
  return sleepModes;
}

export type PrinterSettingsSnapshot = {
  powerSound?: boolean;
  connectionSound?: boolean;
  sleepMode?: number;
  errors: string[];
};
type SettingsProtocol = Pick<
  NiimbotProtocol,
  "isSoundEnabled" | "setSoundEnabled" | "getAutoShutDownTime" | "setAutoShutDownTime"
>;
const message = (error: unknown) => (error instanceof Error ? error.message : String(error));

export async function readPrinterSettings(protocol: SettingsProtocol): Promise<PrinterSettingsSnapshot> {
  const result: PrinterSettingsSnapshot = { errors: [] };
  for (const [key, type] of [
    ["powerSound", SoundSettingsItemType.PowerSound],
    ["connectionSound", SoundSettingsItemType.BluetoothConnectionSound],
  ] as const) {
    try {
      result[key] = await protocol.isSoundEnabled(type);
    } catch (error) {
      result.errors.push(`${key === "powerSound" ? "Power sound" : "Connection sound"}: ${message(error)}`);
    }
  }
  try {
    result.sleepMode = await protocol.getAutoShutDownTime();
  } catch (error) {
    result.errors.push(`Sleep: ${message(error)}`);
  }
  return result;
}

export async function setVerifiedSound(protocol: SettingsProtocol, type: SoundSettingsItemType, enabled: boolean) {
  if (
    ![SoundSettingsItemType.PowerSound, SoundSettingsItemType.BluetoothConnectionSound].includes(type) ||
    typeof enabled !== "boolean"
  )
    throw new Error("Invalid sound setting");
  await protocol.setSoundEnabled(type, enabled);
  if ((await protocol.isSoundEnabled(type)) !== enabled)
    throw new Error("The printer did not confirm the sound setting. Its previous value may still be active.");
}

export async function setVerifiedSleep(protocol: SettingsProtocol, mode: number) {
  if (!sleepModes.some((option) => option.value === mode)) throw new Error("Unsupported sleep mode; no command sent");
  await protocol.setAutoShutDownTime(mode as AutoShutdownTime);
  if ((await protocol.getAutoShutDownTime()) !== mode)
    throw new Error("The printer did not confirm the sleep setting. Check its current value before retrying.");
}
