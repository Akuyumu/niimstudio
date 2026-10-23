import test from "node:test";
import assert from "node:assert/strict";
import { getPrinterMetaByModel, LabelType, modelsLibrary, PrinterModel, type PaperInfo } from "@mmote/niimbluelib";
import {
  detectedStock,
  offlineProfile,
  printerProfile,
  stockFromSize,
  stockMatches,
  stockSizes,
  rollStockKey,
  availableStockPresets,
  printableAreaNotice,
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
test("actual reported printhead width takes precedence over static metadata without widening the physical stock range", () => {
  const reported = printerProfile(meta, { printheadWidth: 576 })!;
  assert.equal(reported.printheadPixels, 576);
  assert.equal(stockFromSize({ widthMm: 50, heightMm: 30, shape: "rounded_rect" }, reported)?.size.width, 576);
  assert.equal(stockFromSize({ widthMm: 60, heightMm: 40, shape: "rounded_rect" }, reported), undefined);
  assert.equal(printerProfile(meta, { printheadWidth: 0 })?.printheadPixels, meta.printheadPixels);
  assert.equal(printerProfile(meta, { printheadWidth: NaN })?.printheadPixels, meta.printheadPixels);
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
  const wideRoll = stockFromSize({ ...stock, widthMm: 50 }, profile)!;
  assert.equal(wideRoll.widthMm, 50);
  assert.equal(wideRoll.size.width, 560);
  assert.equal(wideRoll.printableAreaLimited, true);
  assert.match(printableAreaNotice(wideRoll)!, /50 × 30 mm roll.*47.4 × 30.0 mm/);
  assert.equal(printableAreaNotice(stockFromSize(stock, profile)!), undefined);
  assert.deepEqual(stockFromSize(stock, offlineProfile)!.size, { width: 320, height: 240 });
  assert.equal(stockFromSize({ ...stock, heightMm: -1 }, profile), undefined);
});

test("B1 Pro physical media bounds include 50 mm rolls but never expand printhead width", () => {
  const choices = availableStockPresets(profile);
  assert.ok(choices.some((stock) => stock.id === "50x30"));
  assert.ok(choices.some((stock) => stock.id === "50x50"));
  assert.ok(!choices.some((stock) => stock.id === "60x40"));
  assert.ok(!choices.some((stock) => stock.id === "70x40"));
  assert.ok(choices.every((stock) => stock.projected.size.width <= profile.printheadPixels));
  assert.equal(availableStockPresets(undefined).length, 0);
  assert.equal(stockFromSize({ widthMm: 12, heightMm: 30, shape: "rect" }, profile), undefined);
  assert.equal(stockFromSize({ widthMm: 50, heightMm: 400, shape: "rect" }, profile), undefined);
  const unknownBounds = { ...profile, mediaBounds: undefined };
  assert.equal(stockFromSize({ widthMm: 50, heightMm: 30, shape: "rect" }, unknownBounds), undefined);
});

test("reported 50 mm B1 Pro roll retains physical size with a bounded printable raster", () => {
  const detected = detectedStock({ ...paper, paperWidth: 50, paperWidthPixel: 591 }, profile)!;
  assert.equal(detected.widthMm, 50);
  assert.deepEqual(detected.size, { width: 560, height: 354 });
  assert.equal(detected.printableAreaLimited, true);
});

test("B21S accepts documented 50 mm rolls despite its 48 mm printable head", () => {
  const b21s = printerProfile(getPrinterMetaByModel(PrinterModel.B21S))!;
  assert.equal(b21s.dpi, 203);
  assert.equal(b21s.printheadPixels, 384);
  const choices = availableStockPresets(b21s);
  assert.ok(choices.some((stock) => stock.id === "50x30"));
  assert.ok(choices.some((stock) => stock.id === "50x50"));
  assert.ok(!choices.some((stock) => stock.id === "60x40"));
  const preset = stockFromSize({ widthMm: 50, heightMm: 30, shape: "rounded_rect" }, b21s)!;
  assert.deepEqual(preset.size, { width: 384, height: 240 });
  assert.equal(preset.printableAreaLimited, true);
  const detected = detectedStock({ ...paper, paperWidth: 50, paperWidthPixel: 400, paperHeightPixel: 240 }, b21s)!;
  assert.equal(detected.widthMm, 50);
  assert.equal(detected.heightMm, 30);
  assert.deepEqual(detected.size, { width: 384, height: 240 });
  assert.equal(detected.printableAreaLimited, true);
});

function reportedPaper(widthMm: number, heightMm: number, dpi: number): PaperInfo {
  const dpmm = dpi === 203 ? 8 : dpi / 25.4;
  return {
    valid: true,
    paperWidth: widthMm,
    paperHeight: heightMm,
    paperWidthPixel: Math.round(widthMm * dpmm),
    paperHeightPixel: Math.round(heightMm * dpmm),
    paperType: LabelType.WithGaps,
  };
}

test("every model in the supported library has physical media bounds beyond its printable head", () => {
  for (const model of modelsLibrary) {
    const modelProfile = printerProfile(model);
    assert.ok(modelProfile, model.model);
    assert.ok(modelProfile.mediaBounds, model.model);
    const headMm = Math.round(model.printheadPixels / (model.dpi === 203 ? 8 : model.dpi / 25.4));
    assert.ok(modelProfile.mediaBounds.maxWidth >= headMm, model.model);
  }
});

test("media width classes cover all NIIMBOT head sizes", () => {
  const expected: Array<[PrinterModel, number]> = [
    [PrinterModel.D11, 15],
    [PrinterModel.D101, 25],
    [PrinterModel.A1_PRO, 25],
    [PrinterModel.B1, 50],
    [PrinterModel.B1_SE, 54],
    [PrinterModel.B2_PRO, 50],
    [PrinterModel.B11, 50],
    [PrinterModel.T8, 50],
    [PrinterModel.K2, 60],
    [PrinterModel.B3, 75],
    [PrinterModel.B3S, 75],
    [PrinterModel.M3, 78],
    [PrinterModel.B31, 77],
    [PrinterModel.K3, 82],
    [PrinterModel.B4, 108],
    [PrinterModel.T2S, 107],
    [PrinterModel.ET10, 200],
  ];
  for (const [model, maxWidth] of expected) {
    assert.equal(printerProfile(getPrinterMetaByModel(model))!.mediaBounds.maxWidth, maxWidth, model);
  }
});

test("all 48-50 mm top-fed models expose 50 mm fixed stock without exposing 60 mm stock", () => {
  for (const model of modelsLibrary) {
    if (model.printDirection !== "top") continue;
    const headMm = Math.round(model.printheadPixels / (model.dpi === 203 ? 8 : model.dpi / 25.4));
    if (headMm < 48 || headMm > 50) continue;
    const choices = availableStockPresets(printerProfile(model));
    assert.ok(
      choices.some((stock) => stock.id === "50x30"),
      model.model,
    );
    assert.ok(
      choices.some((stock) => stock.id === "50x50"),
      model.model,
    );
    assert.ok(!choices.some((stock) => stock.id === "60x40"), model.model);
  }
});

test("wider-head classes expose their documented larger stock and keep the printable head cap", () => {
  const k2 = printerProfile(getPrinterMetaByModel(PrinterModel.K2))!;
  assert.ok(availableStockPresets(k2).some((stock) => stock.id === "60x40"));
  assert.ok(!availableStockPresets(k2).some((stock) => stock.id === "70x40"));
  assert.equal(stockFromSize({ widthMm: 60, heightMm: 40, shape: "rect" }, k2)!.size.width, 448);

  for (const model of [PrinterModel.B3S, PrinterModel.B3, PrinterModel.B31, PrinterModel.B4]) {
    assert.ok(
      availableStockPresets(printerProfile(getPrinterMetaByModel(model))).some((stock) => stock.id === "70x40"),
      model,
    );
  }
});

test("auto-detection accepts each documented physical media class with a clipped printable raster", () => {
  const cases: Array<[PrinterModel, number, number]> = [
    [PrinterModel.B1, 50, 30],
    [PrinterModel.K2, 60, 40],
    [PrinterModel.B3S, 75, 50],
    [PrinterModel.B4, 108, 50],
  ];
  for (const [model, widthMm, heightMm] of cases) {
    const modelProfile = printerProfile(getPrinterMetaByModel(model))!;
    const detected = detectedStock(reportedPaper(widthMm, heightMm, modelProfile.dpi), modelProfile);
    assert.ok(detected, model);
    assert.equal(detected.widthMm, widthMm, model);
    assert.equal(detected.printableAreaLimited, true, model);
    assert.ok(detected.size.width <= modelProfile.printheadPixels, model);
  }
});

test("smaller head classes keep oversized fixed stock hidden and accept their documented overhang", () => {
  const d101 = printerProfile(getPrinterMetaByModel(PrinterModel.D101))!;
  assert.ok(availableStockPresets(d101).some((stock) => stock.id === "40x20"));
  assert.ok(!availableStockPresets(d101).some((stock) => stock.id === "40x30"));
  assert.equal(detectedStock(reportedPaper(50, 30, 203), d101), undefined);

  const d11 = printerProfile(getPrinterMetaByModel(PrinterModel.D11))!;
  assert.ok(availableStockPresets(d11).some((stock) => stock.id === "30x12"));
  assert.ok(!availableStockPresets(d11).some((stock) => stock.id === "40x20"));
  assert.equal(detectedStock(reportedPaper(50, 30, 203), d11), undefined);
  const fifteen = detectedStock(reportedPaper(15, 30, 203), d11)!;
  assert.deepEqual([fifteen.widthMm, fifteen.heightMm], [30, 15]);
  assert.deepEqual(fifteen.size, { width: 240, height: 96 });
  assert.equal(fifteen.printableAreaLimited, true);
});

test("remembered roll keys require a reported product identity and ignore private serial/UUID", () => {
  const tag = {
    tagPresent: true,
    uuid: "one",
    serialNumber: "private",
    barCode: " SKU ",
    allPaper: 100,
    usedPaper: 0,
    consumablesType: LabelType.WithGaps,
  };
  const key = rollStockKey("B1_PRO", tag);
  assert.equal(key, rollStockKey("B1_PRO", { ...tag, uuid: "two", serialNumber: "different" }));
  assert.notEqual(key, rollStockKey("B1", tag));
  assert.equal(rollStockKey("B1_PRO", { ...tag, tagPresent: false }), undefined);
  assert.equal(rollStockKey("B1_PRO", { ...tag, barCode: "" }), undefined);
  assert.equal(rollStockKey(undefined, tag), undefined);
});
