/** Read-only printer metadata. Never infer a roll size from its printer model. */
import { LabelType, type PaperInfo, type PrinterInfo, type PrinterModelMeta } from "@mmote/niimbluelib";

export type StockShape = "rounded_rect" | "rect" | "circle";
export interface PrinterProfile {
  dpi: number;
  dpmm: number;
  printDirection: "left" | "top";
  printheadPixels: number;
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

export function printerProfile(
  meta?: PrinterModelMeta,
  info?: Pick<PrinterInfo, "capabilities">,
): PrinterProfile | undefined {
  if (!meta || !["left", "top"].includes(meta.printDirection) || !(meta.printheadPixels >= 8)) return;
  // The capabilities protocol calls its 203-DPI class "200".
  const reported = info?.capabilities?.printheadDpi;
  const dpi = reported === 200 ? 203 : (reported ?? meta.dpi);
  if (![203, 300, 600].includes(dpi)) return;
  return {
    dpi,
    dpmm: dpi === 203 ? 8 : dpi / 25.4,
    printDirection: meta.printDirection,
    printheadPixels: meta.printheadPixels,
  };
}

export function stockFromSize(stock: StockSize, profile: PrinterProfile): DetectedStock | undefined {
  if (![stock.widthMm, stock.heightMm].every((value) => Number.isFinite(value) && value > 0 && value <= 1000)) return;
  // Sizes are shown in the design's reading orientation. The short edge crosses
  // the printhead for a left-fed label; the width crosses it for a top-fed label.
  const width = Math.round(stock.widthMm * profile.dpmm);
  const height = Math.round(stock.heightMm * profile.dpmm);
  const head = profile.printDirection === "left" ? height : width;
  if (profile.printheadPixels && head > profile.printheadPixels) return;
  const aligned = head - (head % 8);
  if (aligned < 8 || width > 10000 || height > 10000) return;
  return {
    ...stock,
    dpi: profile.dpi,
    printDirection: profile.printDirection,
    size: {
      width: profile.printDirection === "top" ? aligned : width,
      height: profile.printDirection === "left" ? aligned : height,
    },
  };
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
  if (head === undefined || length === undefined || head > profile.printheadPixels || length > 10000) return;
  const aligned = head - (head % 8);
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
