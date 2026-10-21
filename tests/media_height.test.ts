import test from "node:test";
import assert from "node:assert/strict";
import {
  PacketParser,
  NiimbotPacket,
  ResponseCommandId,
  getPrinterMetaByModel,
  PrinterModel,
} from "@mmote/niimbluelib";
import { normalizePaperHeight, readMedia } from "../src/desktop/media_reads.ts";
import {
  detectedStock,
  printerProfile,
  stockContext,
  activeStockOverride,
  stockFromSize,
} from "../src/desktop/media.ts";

// Reconstructed 18-byte payload from the user-provided 50×30 B1 Pro 2.12
// paper fields, not a captured/raw packet and not an RFID→size lookup table.
const payload = [0, 70, 1, 98, 1, 0, 60, 1, 44, 2, 78, 1, 244, 0, 0, 0, 0, 0];
const parsed = PacketParser.parsePaperInfoResponse(new NiimbotPacket(ResponseCommandId.In_GetPaperInfo, payload));

test("B1 Pro 30 mm height is not reduced by its separate 6 mm field", () => {
  assert.equal(parsed.paperHeight, 24);
  assert.equal(parsed.paperHeightPixel, 284);
  const fixed = normalizePaperHeight(parsed, 4097);
  assert.equal(fixed.paperHeight, 30);
  assert.equal(fixed.paperHeightPixel, 354);
  assert.equal(fixed.gapHeight, 6);
  assert.equal(fixed.gapHeightPixel, 70);
  assert.equal(fixed.totalHeight, 30);
  assert.equal(parsed.paperHeight, 24, "do not mutate library/parser data");
  const profile = printerProfile(getPrinterMetaByModel(PrinterModel.B1_PRO), { printheadWidth: 576 })!;
  const stock = detectedStock(fixed, profile)!;
  assert.equal(stock.heightMm, 30);
  assert.equal(stock.size.height, 354);
  assert.equal(stock.size.width, 576);
});
test("height backport is restricted to B1 Pro and leaves other models/invalid reports alone", () => {
  assert.equal(normalizePaperHeight(parsed, 785), parsed);
  assert.equal(normalizePaperHeight(parsed), parsed);
  assert.equal(normalizePaperHeight({ valid: false }, 4097).valid, false);
  assert.equal(normalizePaperHeight({ valid: true }, 4097).paperHeight, undefined);
});
test("native media-read path applies the B1 Pro correction", async () => {
  const noTag = async () => ({
    tagPresent: false,
    uuid: "",
    serialNumber: "",
    barCode: "",
    allPaper: 0,
    usedPaper: 0,
    consumablesType: 0,
  });
  const result = await readMedia({ rfidInfo: noTag, getPaperInfo: async () => parsed, rfidInfo2: noTag }, 4097);
  assert.equal(result.info.paperInfo?.paperHeight, 30);
  assert.deepEqual(result.errors, {});
});
test("manual overrides are valid only for the same model, roll, report and print profile", () => {
  const profile = printerProfile(getPrinterMetaByModel(PrinterModel.B1_PRO))!;
  const stock = stockFromSize({ widthMm: 50, heightMm: 30, shape: "rounded_rect" }, profile)!;
  const tag = {
    tagPresent: true,
    uuid: "fixture",
    serialNumber: "private",
    barCode: "fixture",
    allPaper: 100,
    usedPaper: 0,
    consumablesType: 1,
  };
  const context = stockContext("B1_PRO", tag, parsed, profile);
  const override = { context, stock };
  assert.equal(activeStockOverride(override, context), stock);
  assert.equal(activeStockOverride(override, stockContext("B1", tag, parsed, profile)), undefined);
  assert.equal(
    activeStockOverride(override, stockContext("B1_PRO", { ...tag, uuid: "different" }, parsed, profile)),
    undefined,
  );
  assert.equal(
    activeStockOverride(override, stockContext("B1_PRO", tag, { ...parsed, totalHeight: 40 }, profile)),
    undefined,
  );
  assert.equal(
    activeStockOverride(override, stockContext("B1_PRO", tag, parsed, { ...profile, printheadPixels: 576 })),
    undefined,
  );
  assert.equal(
    activeStockOverride(override, stockContext("B1_PRO", { ...tag, usedPaper: 20 }, parsed, profile)),
    stock,
  );
});
