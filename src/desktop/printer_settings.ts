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
export type PrinterSettingKey = "powerSound" | "connectionSound" | "sleepMode";
export const settingLabels = {
  powerSound: "Power sounds",
  connectionSound: "Connection sounds",
  sleepMode: "Sleep / auto power-off",
} as const;
export const settingKeys = ["powerSound", "connectionSound", "sleepMode"] as const;

export function visiblePrinterSettings(
  snapshot: PrinterSettingsSnapshot,
  range?: { min: number; max: number },
): PrinterSettingKey[] {
  return settingKeys.filter((key) =>
    key === "sleepMode"
      ? offeredSleepModes(range).some((mode) => mode.value === snapshot.sleepMode)
      : typeof snapshot[key] === "boolean",
  );
}

export class SettingsConfirmationError extends Error {
  readonly observed: boolean | number | undefined;
  constructor(message: string, observed?: boolean | number) {
    super(message);
    this.observed = observed;
  }
}
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
      const value = await protocol.isSoundEnabled(type);
      if (typeof value !== "boolean") throw new Error("No readable sound setting was reported");
      result[key] = value;
    } catch (error) {
      result.errors.push(`${key === "powerSound" ? "Power sound" : "Connection sound"}: ${message(error)}`);
    }
  }
  try {
    const value = await protocol.getAutoShutDownTime();
    if (!sleepModes.some((mode) => mode.value === value))
      throw new Error(`Unmapped sleep mode ${value}; control hidden`);
    result.sleepMode = value;
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
  let observed: boolean;
  try {
    await protocol.setSoundEnabled(type, enabled);
    observed = await protocol.isSoundEnabled(type);
  } catch (error) {
    throw new SettingsConfirmationError(
      `Sound change not confirmed. The current value is unknown; refresh before retrying. ${message(error)}`,
    );
  }
  if (observed !== enabled)
    throw new SettingsConfirmationError(
      `The printer did not confirm the sound setting. Requested ${enabled ? "on" : "off"}; printer reports ${typeof observed === "boolean" ? (observed ? "on" : "off") : "an unreadable value"}.`,
      typeof observed === "boolean" ? observed : undefined,
    );
}

export async function setVerifiedSleep(protocol: SettingsProtocol, mode: number) {
  if (!sleepModes.some((option) => option.value === mode)) throw new Error("Unsupported sleep mode; no command sent");
  let observed: number;
  try {
    await protocol.setAutoShutDownTime(mode as AutoShutdownTime);
    observed = await protocol.getAutoShutDownTime();
  } catch (error) {
    throw new SettingsConfirmationError(
      `Sleep change not confirmed. The current value is unknown; refresh before retrying. ${message(error)}`,
    );
  }
  if (observed !== mode)
    throw new SettingsConfirmationError(
      `The printer did not confirm the sleep setting. Requested mode ${mode}; printer reports mode ${observed}.`,
      Number.isInteger(observed) ? observed : undefined,
    );
}
