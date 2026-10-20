/** Synthetic printer metadata only. No protocol requests or transport writes. */
import { tick } from "svelte";
import { get } from "svelte/store";
import { getPrinterMetaByModel, LabelType, PrinterModel } from "@mmote/niimbluelib";
import { confirmedStock, connectionState, printerInfo, printerMeta, rfidInfo } from "$/stores";
import { createPrinterInfo } from "@mmote/niimbluelib/dist/cjs/client/abstract_client";
import type { CustomCanvas } from "$/fabric-object/custom_canvas";
import type { ExportedLabelTemplate } from "$/types";
import type { UndoRedo } from "$/utils/undo_redo";
import { LabelDesignerObjectHelper } from "$/utils/label_designer_object_helper";
import { nativeRequest } from "$/desktop/bridge";
import { detectedStock, printerProfile, stockMatches } from "$/desktop/media";

const settle = async () => {
  await tick();
  await new Promise((resolve) => setTimeout(resolve, 600));
};
const click = (selector: string) => {
  const element = document.querySelector<HTMLButtonElement>(selector);
  if (!element) throw new Error(`Missing stock control: ${selector}`);
  element.click();
};

export async function runStockSmoke(context: {
  canvas: CustomCanvas;
  exportLabel: () => ExportedLabelTemplate;
  loadLabel: (label: ExportedLabelTemplate) => Promise<void>;
  openPreview: () => void;
  undo: UndoRedo;
}) {
  const original = context.exportLabel();
  const previous = {
    state: get(connectionState),
    meta: get(printerMeta),
    info: get(printerInfo),
    rfid: get(rfidInfo),
    stock: get(confirmedStock),
  };
  click('[data-action="label-stock"]');
  await settle();
  const simpleStockPicker =
    !!document.querySelector('[data-stock-id="40x30"]') && !document.querySelector('.modal.show input[type="number"]');
  await nativeRequest("testSnapshot", { name: "stock-picker" });
  click('[data-stock-id="40x30"]');
  await settle();
  const offlinePresetWorks = context.exportLabel().label.size.width === 320;

  context.canvas.clear();
  const meta = getPrinterMetaByModel(PrinterModel.B1_PRO)!;
  printerInfo.set(createPrinterInfo());
  printerMeta.set(meta);
  const paper = {
    valid: true,
    paperWidth: 40,
    paperHeight: 30,
    paperWidthPixel: 472,
    paperHeightPixel: 354,
    paperType: LabelType.WithGaps,
  };
  rfidInfo.set({ paperInfo: paper });
  connectionState.set("connected");
  await settle();
  const automaticStockApplied =
    stockMatches(context.exportLabel().label, detectedStock(paper, printerProfile(meta))!) &&
    !document.querySelector(".modal.show");
  const automaticStockBadge =
    document.querySelector('[data-action="label-stock"]')?.textContent?.includes("Auto") === true;

  LabelDesignerObjectHelper.addText(context.canvas, "Keep my design");
  context.undo.push(context.canvas, context.exportLabel().label);
  const sizeBefore = JSON.stringify(context.exportLabel().label.size);
  rfidInfo.set({
    paperInfo: { ...paper, paperWidth: 30, paperHeight: 20, paperWidthPixel: 354, paperHeightPixel: 236 },
  });
  await settle();
  const existingDesignProtected =
    JSON.stringify(context.exportLabel().label.size) === sizeBefore &&
    !!document.querySelector('[data-action="use-detected-stock"]');
  await nativeRequest("testSnapshot", { name: "stock-detected" });
  Array.from(document.querySelectorAll<HTMLButtonElement>(".modal.show button"))
    .find((button) => button.textContent?.trim() === "Keep design")!
    .click();
  await settle();
  context.openPreview();
  await settle();
  click('[data-action="print-label"]');
  await tick();
  const mismatchedStockCannotPrint =
    document.querySelector(".modal.show .alert-danger")?.textContent?.includes("differs from the loaded stock") ===
    true;
  const preview = document.querySelector<HTMLCanvasElement>(".modal.show canvas")!;
  const roundedPrintPreview = getComputedStyle(preview).borderRadius === "10px";
  const corner = preview.getContext("2d")!.getImageData(0, 0, 1, 1).data;
  const previewRoundingIsVisualOnly = corner[0] === 255 && corner[1] === 255 && corner[2] === 255 && corner[3] === 255;
  click(".modal.show .btn-close");
  await settle();
  click('[data-action="label-stock"]');
  await settle();
  click('[data-action="use-detected-stock"]');
  await settle();
  const confirmedStockApplied =
    context.canvas.getObjects().length === 1 &&
    context.exportLabel().label.size.width === 352 &&
    context.exportLabel().label.size.height === 236;
  await context.undo.undo();
  const stockResizeUndoWorks =
    JSON.stringify(context.exportLabel().label.size) === sizeBefore && context.canvas.getObjects().length === 1;
  await context.undo.redo();

  rfidInfo.set({});
  await settle();
  click(".modal.show .btn-close");
  await settle();
  context.openPreview();
  await settle();
  click('[data-action="print-label"]');
  await tick();
  const unknownStockCannotPrint =
    document.querySelector(".modal.show .alert-danger")?.textContent?.includes("Choose the stock loaded") === true;
  click(".modal.show .btn-close");
  await settle();

  connectionState.set("disconnected");
  printerMeta.set(previous.meta);
  printerInfo.set(previous.info);
  rfidInfo.set(previous.rfid);
  confirmedStock.set(previous.stock);
  await context.loadLabel(original);
  connectionState.set(previous.state);
  await settle();
  return {
    simpleStockPicker,
    offlinePresetWorks,
    automaticStockApplied,
    automaticStockBadge,
    existingDesignProtected,
    mismatchedStockCannotPrint,
    roundedPrintPreview,
    previewRoundingIsVisualOnly,
    confirmedStockApplied,
    stockResizeUndoWorks,
    unknownStockCannotPrint,
  };
}
