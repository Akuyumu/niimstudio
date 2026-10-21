import test from "node:test";
import assert from "node:assert/strict";
import { SoundSettingsItemType, type NiimbotProtocol } from "@mmote/niimbluelib";
import {
  readPrinterSettings,
  setVerifiedSleep,
  setVerifiedSound,
  sleepModes,
  offeredSleepModes,
} from "../src/desktop/printer_settings.ts";
import { readMedia } from "../src/desktop/media_reads.ts";

function protocol() {
  let mode = 1;
  const sounds = new Map<number, boolean>([
    [1, true],
    [2, true],
  ]);
  const writes: unknown[] = [];
  return {
    writes,
    isSoundEnabled: async (type: number) => sounds.get(type)!,
    setSoundEnabled: async (type: number, enabled: boolean) => {
      writes.push([type, enabled]);
      sounds.set(type, enabled);
    },
    getAutoShutDownTime: async () => mode,
    setAutoShutDownTime: async (value: number) => {
      writes.push(value);
      mode = value;
    },
  } as unknown as Pick<
    NiimbotProtocol,
    "isSoundEnabled" | "setSoundEnabled" | "getAutoShutDownTime" | "setAutoShutDownTime"
  > & { writes: unknown[] };
}

test("reading settings sends no setting writes", async () => {
  const fake = protocol();
  assert.deepEqual(await readPrinterSettings(fake), {
    powerSound: true,
    connectionSound: true,
    sleepMode: 1,
    errors: [],
  });
  assert.deepEqual(fake.writes, []);
});
test("unsupported queries stay unknown rather than silently looking off", async () => {
  const fake = protocol();
  fake.isSoundEnabled = async () => {
    throw new Error("not supported");
  };
  const snapshot = await readPrinterSettings(fake);
  assert.equal(snapshot.powerSound, undefined);
  assert.equal(snapshot.connectionSound, undefined);
  assert.equal(snapshot.sleepMode, 1);
  assert.equal(snapshot.errors.length, 2);
});
test("sound writes require a matching read-back", async () => {
  const fake = protocol();
  await setVerifiedSound(fake, SoundSettingsItemType.PowerSound, false);
  assert.deepEqual(fake.writes, [[SoundSettingsItemType.PowerSound, false]]);
  fake.isSoundEnabled = async () => true;
  await assert.rejects(setVerifiedSound(fake, SoundSettingsItemType.PowerSound, false), /did not confirm/);
});
test("sleep uses documented mode codes and never invents a disable code", async () => {
  const fake = protocol();
  await setVerifiedSleep(fake, 4);
  assert.equal(await fake.getAutoShutDownTime(), 4);
  assert.match(sleepModes[3].label, /Never.*60 minutes/);
  const before = fake.writes.length;
  for (const invalid of [0, -1, 15, 30, 255, NaN]) await assert.rejects(setVerifiedSleep(fake, invalid), /Unsupported/);
  assert.equal(fake.writes.length, before);
});
test("sleep read-back mismatch is a failure, not false success", async () => {
  const fake = protocol();
  fake.getAutoShutDownTime = async () => 1;
  await assert.rejects(setVerifiedSleep(fake, 4), /did not confirm/);
});
test("reported unsupported sleep modes are not offered", () => {
  assert.deepEqual(
    offeredSleepModes({ min: 1, max: 3 }).map((mode) => mode.value),
    [1, 2, 3],
  );
  assert.deepEqual(offeredSleepModes({ min: 0, max: 0 }), []);
  assert.equal(offeredSleepModes({ min: 15, max: 60 }).length, 4);
});
test("media reads keep RFID identity even if the independent size request fails", async () => {
  const tag = {
    tagPresent: true,
    uuid: "fixture",
    barCode: "SKU-FIXTURE",
    serialNumber: "private",
    allPaper: 100,
    usedPaper: 1,
    consumablesType: 1,
  };
  const result = await readMedia({
    rfidInfo: async () => tag,
    getPaperInfo: async () => {
      throw new Error("size request unsupported");
    },
    rfidInfo2: async () => {
      throw new Error("no ribbon support");
    },
  });
  assert.equal(result.info.labelRfidInfo?.barCode, "SKU-FIXTURE");
  assert.equal(result.info.paperInfo, undefined);
  assert.equal(result.errors.paper, "size request unsupported");
});
test("basic paper replies remain invalid instead of guessed dimensions", async () => {
  const result = await readMedia({
    rfidInfo: async () => {
      throw new Error("no tag response");
    },
    getPaperInfo: async () => ({ valid: false }),
    rfidInfo2: async () => {
      throw new Error("no ribbon response");
    },
  });
  assert.deepEqual(result.info.paperInfo, { valid: false });
  assert.equal(result.errors.paper, undefined);
  assert.equal(result.errors.label, "no tag response");
});
