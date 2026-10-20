import test from "node:test";
import assert from "node:assert/strict";
import { getPrinterMetaByModel, LabelType, PrinterModel, type PaperInfo } from "@mmote/niimbluelib";
import {
  detectedStock,
  offlineProfile,
  printerProfile,
  stockFromSize,
  stockMatches,
  stockSizes,
} from "../src/desktop/media.ts";

const meta = getPrinterMetaByModel(PrinterModel.B1_PRO)!;
const profile = printerProfile(meta)!;
const paper: PaperInfo = {
  valid: true,
  paperWidth: 40,
  paperHeight: 30,
  paperWidthPixel: 472,
  paperHeightPixel: 354,
  paperType: LabelType.WithGaps,
};

test("B1 Pro profile selects 300 DPI and its native feed direction", () => {
  assert.equal(profile.dpi, 300);
  assert.equal(profile.printDirection, "top");
  assert.equal(printerProfile(undefined), undefined);
  assert.equal(printerProfile({ ...meta, dpi: 0 }), undefined);
});
test("reported resolution takes precedence and the protocol's 200 class means 203 DPI", () => {
  assert.equal(printerProfile(meta, { capabilities: { printheadDpi: 200 } })!.dpmm, 8);
  assert.equal(printerProfile({ ...meta, dpi: 203 }, { capabilities: { printheadDpi: 300 } })!.dpi, 300);
  assert.equal(printerProfile(meta, { capabilities: { printheadDpi: -1 } }), undefined);
});
test("valid media uses the label height excluding the gap and byte-aligns the printhead edge", () => {
  const stock = detectedStock(paper, profile)!;
  assert.deepEqual(stock.size, { width: 472, height: 354 });
  assert.equal(stock.labelType, LabelType.WithGaps);
  assert.equal(stockMatches({ size: stock.size, printDirection: "top" }, stock), true);
  assert.equal(stockMatches({ size: stock.size, printDirection: "left" }, stock), false);
});
test("left-fed printers map across-head width to canvas height, not canvas width", () => {
  const stock = detectedStock(paper, { ...profile, printDirection: "left" })!;
  assert.deepEqual(stock.size, { width: 354, height: 472 });
  assert.deepEqual([stock.widthMm, stock.heightMm], [30, 40]);
});
test("missing, invalid and continuous media never invent a stock size", () => {
  for (const input of [
    undefined,
    { valid: false },
    { valid: true },
    { ...paper, paperType: LabelType.Continuous },
    { ...paper, tailLengthPixel: 10 },
  ]) {
    assert.equal(detectedStock(input, profile), undefined);
  }
});
test("invalid or conflicting reported dimensions are rejected", () => {
  for (const input of [
    { paperWidth: 0 },
    { paperHeight: NaN },
    { paperHeight: Infinity },
    { paperWidthPixel: -1 },
    { paperWidthPixel: 100 },
    { paperWidth: 100, paperWidthPixel: 1181 },
    { paperHeight: 2000 },
  ]) {
    assert.equal(detectedStock({ ...paper, ...input }, profile), undefined);
  }
});
test("mm-only media is converted using the identified printer DPI", () => {
  assert.deepEqual(
    detectedStock({ ...paper, paperWidthPixel: undefined, paperHeightPixel: undefined }, profile)!.size,
    { width: 472, height: 354 },
  );
});
test("preset stock filters excessive width and does not expose custom resolution", () => {
  const stock = stockSizes.find((stock) => stock.id === "40x30")!;
  assert.deepEqual(stockFromSize(stock, profile)!.size, { width: 472, height: 354 });
  assert.equal(stockFromSize({ ...stock, widthMm: 50 }, profile), undefined);
  assert.deepEqual(stockFromSize(stock, offlineProfile)!.size, { width: 320, height: 240 });
  assert.equal(stockFromSize({ ...stock, heightMm: -1 }, profile), undefined);
});
