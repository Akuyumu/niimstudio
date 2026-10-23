/** Read-only printer metadata. Never infer a roll size from its printer model. */
import {
  LabelType,
  PrinterModel,
  type PaperInfo,
  type PrinterInfo,
  type PrinterModelMeta,
  type RfidInfo,
} from "@mmote/niimbluelib";

export function rollStockKey(model: string | undefined, tag: RfidInfo | undefined): string | undefined {
  const product = tag?.barCode?.trim();
  if (!model || !tag?.tagPresent || !product || product.length > 128) return;
  return JSON.stringify([model, product, tag.consumablesType]);
}

export type StockShape = "rounded_rect" | "rect" | "circle";
export interface PrinterProfile {
  dpi: number;
  dpmm: number;
  printDirection: "left" | "top";
  printheadPixels: number;
  mediaBounds?: { minWidth: number; maxWidth: number; minHeight: number; maxHeight: number };
}
export interface StockSize {
  widthMm: number;
  heightMm: number;
  shape: StockShape;
}
export interface DetectedStock extends StockSize {
  size: { width: number; height: number };
  printDirection: "left" | "top";
  dpi: number;
  labelType?: LabelType;
  printableAreaLimited?: boolean;
}

export type StockOverride = { context: string; stock: DetectedStock };

/** Session-only identity: a manual override must not leak to a changed roll/report. */
export function stockContext(
  model: string | undefined,
  tag: RfidInfo | undefined,
  paper: PaperInfo | undefined,
  profile: PrinterProfile | undefined,
): string {
  return JSON.stringify([
    model,
    tag?.tagPresent,
    tag?.uuid,
    tag?.serialNumber,
    tag?.barCode,
    tag?.consumablesType,
    paper,
    profile,
  ]);
}

export function activeStockOverride(override: StockOverride | undefined, context: string): DetectedStock | undefined {
  return override?.context === context ? override.stock : undefined;
}

export const stockSizes = [
  { id: "30x12", widthMm: 30, heightMm: 12, shape: "rounded_rect" },
  { id: "40x12", widthMm: 40, heightMm: 12, shape: "rounded_rect" },
  { id: "40x20", widthMm: 40, heightMm: 20, shape: "rounded_rect" },
  { id: "40x30", widthMm: 40, heightMm: 30, shape: "rounded_rect" },
  { id: "50x30", widthMm: 50, heightMm: 30, shape: "rounded_rect" },
  { id: "50x50", widthMm: 50, heightMm: 50, shape: "rounded_rect" },
  { id: "60x40", widthMm: 60, heightMm: 40, shape: "rounded_rect" },
  { id: "70x40", widthMm: 70, heightMm: 40, shape: "rounded_rect" },
  { id: "circle-30", widthMm: 30, heightMm: 30, shape: "circle" },
  { id: "circle-40", widthMm: 40, heightMm: 40, shape: "circle" },
  { id: "rectangle-40x30", widthMm: 40, heightMm: 30, shape: "rect" },
] as const satisfies readonly (StockSize & { id: string })[];

export const offlineProfile: PrinterProfile = { dpi: 203, dpmm: 8, printDirection: "left", printheadPixels: 0 };

// NIIMBOT's hardware configuration treats printable head width and physical media
// width separately. Its model table gives 48 mm heads a 50 mm media default, K2's
// 56 mm head 60 mm media, 72 mm heads 75 mm media, K3's 80 mm head 82 mm, and B4's
// 104 mm head 108 mm. The same table documents 15 mm media for 12 mm D11-class
// heads and 25 mm media for 24 mm D101-class heads. Several entries are clearly
// inconsistent (for example 200 mm on some 48 mm models and 82 mm on K4), so use
// the head class as the fallback and only admit values confirmed by the model data.
// Source: https://print.niimbot.com/api/hardware/list (model configuration).
const MEDIA_WIDTH_BY_HEAD_MM = [
  [12, 15],
  [15, 15],
  [25, 25],
  [48, 50],
  [50, 50],
  [59, 60],
  [72, 75],
  [75, 77],
  [80, 82],
  [104, 108],
] as const;

// The cloud table has a few valid per-model exceptions to the head class.
const MEDIA_WIDTH_OVERRIDES: Partial<Record<PrinterModel, number>> = {
  [PrinterModel.B1_SE]: 54,
  [PrinterModel.B3]: 75,
  [PrinterModel.S6_P]: 75,
  [PrinterModel.M3]: 78,
  [PrinterModel.EP3M]: 78,
  [PrinterModel.T2S]: 107,
};

// B11/B21S-class guides accept narrower stock than the B1/B2 family.
const MEDIA_MIN_WIDTH_OVERRIDES: Partial<Record<PrinterModel, number>> = {
  [PrinterModel.B11]: 10,
  [PrinterModel.B21S]: 10,
  [PrinterModel.B21_C2B]: 10,
};

function documentedMediaBounds(meta: PrinterModelMeta) {
  const dpmm = meta.dpi === 203 ? 8 : meta.dpi / 25.4;
  const headMm = Math.round(meta.printheadPixels / dpmm);
  const widthClass = MEDIA_WIDTH_BY_HEAD_MM.find(([headMax]) => headMm <= headMax);
  const maxWidth = MEDIA_WIDTH_OVERRIDES[meta.model as PrinterModel] ?? widthClass?.[1] ?? Math.ceil(headMm);
  const minWidth = MEDIA_MIN_WIDTH_OVERRIDES[meta.model as PrinterModel] ?? (headMm >= 48 ? 20 : headMm >= 24 ? 12 : 8);
  return { minWidth, maxWidth, minHeight: 8, maxHeight: 350 };
}

export function printerProfile(
  meta?: PrinterModelMeta,
  info?: Pick<PrinterInfo, "capabilities" | "printheadWidth">,
): PrinterProfile | undefined {
  if (!meta || !["left", "top"].includes(meta.printDirection) || !(meta.printheadPixels >= 8)) return;
  // The capabilities protocol calls its 203-DPI class "200".
  const reported = info?.capabilities?.printheadDpi;
  const dpi = reported === 200 ? 203 : (reported ?? meta.dpi);
  const reportedHead = info?.printheadWidth;
  const printheadPixels =
    Number.isInteger(reportedHead) && reportedHead! >= 8 && reportedHead! <= 4096
      ? reportedHead!
      : meta.printheadPixels;
  if (![203, 300, 600].includes(dpi)) return;
  return {
    dpi,
    dpmm: dpi === 203 ? 8 : dpi / 25.4,
    printDirection: meta.printDirection,
    printheadPixels,
    // Keep NiimBlueLib's conservative printable-head limit; use documented
    // physical-stock bounds separately so wider rolls are not misclassified.
    mediaBounds: documentedMediaBounds(meta),
  };
}

export function stockFromSize(stock: StockSize, profile: PrinterProfile): DetectedStock | undefined {
  if (![stock.widthMm, stock.heightMm].every((value) => Number.isFinite(value) && value > 0 && value <= 1000)) return;
  // Sizes are shown in the design's reading orientation. The short edge crosses
  // the printhead for a left-fed label; the width crosses it for a top-fed label.
  const width = Math.round(stock.widthMm * profile.dpmm);
  const height = Math.round(stock.heightMm * profile.dpmm);
  const head = profile.printDirection === "left" ? height : width;
  const acrossMm = profile.printDirection === "left" ? stock.heightMm : stock.widthMm;
  const feedMm = profile.printDirection === "left" ? stock.widthMm : stock.heightMm;
  const bounds = profile.mediaBounds;
  if (
    bounds &&
    (acrossMm < bounds.minWidth || acrossMm > bounds.maxWidth || feedMm < bounds.minHeight || feedMm > bounds.maxHeight)
  )
    return;
  if (!bounds && profile.printheadPixels && head > profile.printheadPixels) return;
  const printable = profile.printheadPixels ? Math.min(head, profile.printheadPixels) : head;
  const aligned = printable - (printable % 8);
  if (aligned < 8 || width > 10000 || height > 10000) return;
  return {
    ...stock,
    dpi: profile.dpi,
    printDirection: profile.printDirection,
    size: {
      width: profile.printDirection === "top" ? aligned : width,
      height: profile.printDirection === "left" ? aligned : height,
    },
    ...(printable < head ? { printableAreaLimited: true } : {}),
  };
}

export function availableStockPresets(profile: PrinterProfile | undefined) {
  if (!profile) return [];
  return stockSizes.flatMap((stock) => {
    const projected = stockFromSize(stock, profile);
    return projected ? [{ ...stock, projected }] : [];
  });
}

export function printableAreaNotice(stock: DetectedStock): string | undefined {
  if (!stock.printableAreaLimited) return;
  const dpmm = stock.dpi === 203 ? 8 : stock.dpi / 25.4;
  return `${stock.widthMm} × ${stock.heightMm} mm roll · Printable canvas ${(stock.size.width / dpmm).toFixed(1)} × ${(stock.size.height / dpmm).toFixed(1)} mm. The roll is wider than the printhead; edge margins cannot be printed. The canvas shows the printable area, not the full label.`;
}

export function detectedStock(
  paper: PaperInfo | undefined,
  profile: PrinterProfile | undefined,
): DetectedStock | undefined {
  if (
    !paper?.valid ||
    !profile ||
    paper.paperType === LabelType.Continuous ||
    (paper.tailLength ?? 0) > 0 ||
    (paper.tailLengthPixel ?? 0) > 0
  )
    return;
  const widthMm = paper.paperWidth;
  const heightMm = paper.paperHeight;
  if (
    ![widthMm, heightMm].every(
      (value) => typeof value === "number" && Number.isFinite(value) && value > 0 && value <= 1000,
    )
  )
    return;
  const pixels = (reported: number | undefined, mm: number) => {
    const calculated = Math.round(mm * profile.dpmm);
    if (reported === undefined) return calculated;
    if (
      !Number.isInteger(reported) ||
      reported <= 0 ||
      Math.abs(reported - calculated) > Math.max(8, calculated * 0.03)
    )
      return;
    return reported;
  };
  const head = pixels(paper.paperWidthPixel, widthMm!);
  const length = pixels(paper.paperHeightPixel, heightMm!);
  if (head === undefined || length === undefined || length > 10000) return;
  const bounds = profile.mediaBounds;
  if (
    bounds &&
    (widthMm! < bounds.minWidth ||
      widthMm! > bounds.maxWidth ||
      heightMm! < bounds.minHeight ||
      heightMm! > bounds.maxHeight)
  )
    return;
  if (!bounds && head > profile.printheadPixels) return;
  const printable = Math.min(head, profile.printheadPixels);
  const aligned = printable - (printable % 8);
  if (aligned < 8) return;
  const left = profile.printDirection === "left";
  // The protocol reports head-width × feed-length, not the editor's reading orientation.
  return {
    widthMm: left ? heightMm! : widthMm!,
    heightMm: left ? widthMm! : heightMm!,
    shape: "rounded_rect",
    dpi: profile.dpi,
    printDirection: profile.printDirection,
    size: { width: left ? length : aligned, height: left ? aligned : length },
    ...(printable < head ? { printableAreaLimited: true } : {}),
    labelType:
      Object.values(LabelType).includes(paper.paperType!) && paper.paperType !== LabelType.Invalid
        ? paper.paperType
        : undefined,
  };
}

export function stockMatches(
  label: { size: { width: number; height: number }; printDirection: string },
  stock: DetectedStock,
): boolean {
  return (
    label.size.width === stock.size.width &&
    label.size.height === stock.size.height &&
    label.printDirection === stock.printDirection
  );
}
