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
import { runSettingsSmoke } from "$/desktop/smoke_settings";
import { runStockOverrideSmoke } from "$/desktop/smoke_stock_override";

const settle = async () => {
  await tick();
  await new Promise((resolve) => setTimeout(resolve, 600));
};
const waitFor = async (condition: () => boolean, description: string) => {
  const deadline = Date.now() + 8000;
  while (!condition()) {
    if (Date.now() > deadline) {
      const modals = Array.from(document.querySelectorAll<HTMLElement>(".modal")).map((modal) => ({
        title: modal.querySelector(".modal-title")?.textContent,
        ready: modal.dataset.modalReady,
        classes: modal.className,
      }));
      throw new Error(
        `Stock UI did not become ready: ${description}; modals=${JSON.stringify(modals)}; stockButtonDisabled=${document.querySelector<HTMLButtonElement>('[data-action="label-stock"]')?.disabled}`,
      );
    }
    await new Promise((resolve) => setTimeout(resolve, 50));
    await tick();
  }
};
const click = async (selector: string) => {
  await waitFor(() => {
    const element = document.querySelector<HTMLButtonElement>(selector);
    const modal = element?.closest<HTMLElement>(".modal");
    return !!element && !element.disabled && (!modal || modal.dataset.modalReady === "true");
  }, selector);
  document.querySelector<HTMLButtonElement>(selector)!.click();
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
  await click('[data-action="label-stock"]');
  await settle();
  const simpleStockPicker =
    !!document.querySelector('[data-stock-id="40x30"]') && !document.querySelector('.modal.show input[type="number"]');
  await nativeRequest("testSnapshot", { name: "stock-picker" });
  await click('[data-stock-id="40x30"]');
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
  const settingsResults = await runSettingsSmoke();

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
  await click('[data-action="keep-stock-design"]');
  await settle();
  context.openPreview();
  await settle();
  await click('[data-action="print-label"]');
  await waitFor(
    () =>
      document.querySelector(".modal.show .alert-danger")?.textContent?.includes("differs from the loaded stock") ===
      true,
    "mismatched stock print guard",
  );
  const mismatchedStockCannotPrint =
    document.querySelector(".modal.show .alert-danger")?.textContent?.includes("differs from the loaded stock") ===
    true;
  const preview = document.querySelector<HTMLCanvasElement>(".modal.show canvas")!;
  await waitFor(
    () =>
      preview.width === context.exportLabel().label.size.width &&
      preview.height === context.exportLabel().label.size.height,
    "rendered print preview",
  );
  const roundedPrintPreview = getComputedStyle(preview).borderRadius === "10px";
  const corner = preview.getContext("2d")!.getImageData(0, 0, 1, 1).data;
  const previewRoundingIsVisualOnly = corner[0] === 255 && corner[1] === 255 && corner[2] === 255 && corner[3] === 255;
  await click(".modal.show .btn-close");
  await waitFor(() => !document.querySelector(".modal.show"), "closed print preview");
  await click('[data-action="label-stock"]');
  await settle();
  await click('[data-action="use-detected-stock"]');
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
  await click(".modal.show .btn-close");
  await waitFor(() => !document.querySelector(".modal.show"), "closed stock picker");
  context.openPreview();
  await settle();
  await click('[data-action="print-label"]');
  await waitFor(
    () =>
      document.querySelector(".modal.show .alert-danger")?.textContent?.includes("Choose the stock loaded") === true,
    "unknown stock print guard",
  );
  const unknownStockCannotPrint =
    document.querySelector(".modal.show .alert-danger")?.textContent?.includes("Choose the stock loaded") === true;
  await click(".modal.show .btn-close");
  await waitFor(() => !document.querySelector(".modal.show"), "closed final preview");

  const tag = {
    tagPresent: true,
    uuid: "synthetic-roll-one",
    barCode: "TEST-40x30",
    serialNumber: "synthetic",
    allPaper: 100,
    usedPaper: 0,
    consumablesType: LabelType.WithGaps,
  };
  rfidInfo.set({ labelRfidInfo: tag, paperInfo: { valid: false } });
  await settle();
  const rollReadExplained =
    document.querySelector('[data-testid="roll-read-status"]')?.textContent?.includes("RFID roll tag detected") ===
    true;
  const physicalStockFilterCorrect =
    !!document.querySelector<HTMLButtonElement>('[data-stock-id="50x30"]') &&
    !document.querySelector<HTMLButtonElement>('[data-stock-id="50x30"]')!.disabled &&
    !document.querySelector('[data-stock-id="60x40"]') &&
    !document.querySelector('[data-stock-id="70x40"]');
  await nativeRequest("testSnapshot", { name: "stock-compatible" });
  document.querySelector<HTMLInputElement>('[data-setting="remember-roll"]')!.click();
  await click('[data-stock-id="40x30"]');
  await settle();
  rfidInfo.set({ labelRfidInfo: { ...tag, uuid: "synthetic-roll-two" }, paperInfo: { valid: false } });
  await settle();
  const rememberedRollWorks =
    document.querySelector('[data-action="label-stock"]')?.textContent?.includes("Saved roll") === true &&
    get(confirmedStock)?.size.width === 472;
  rfidInfo.set({
    labelRfidInfo: { ...tag, uuid: "synthetic-roll-two" },
    paperInfo: { ...paper, paperWidth: 200, paperWidthPixel: 2362 },
  });
  await settle();
  const rememberedRollCannotOverrideConflictingReport =
    !!document.querySelector('[data-stock-id="40x30"]') && !get(confirmedStock);
  rfidInfo.set({ labelRfidInfo: { ...tag, uuid: "synthetic-roll-two" }, paperInfo: { valid: false } });
  await settle();
  await click('[data-action="change-saved-roll"]');
  await settle();
  const rememberedRollCanBeChanged = !!document.querySelector('[data-stock-id="40x30"]');
  await click(".modal.show .btn-close");

  await click('[data-action="label-stock"]');
  await click('[data-stock-id="50x30"]');
  await settle();
  const fiftyMmRollSupported =
    get(confirmedStock)?.widthMm === 50 &&
    context.exportLabel().label.size.width === 560 &&
    context.exportLabel().label.size.height === 354;
  context.openPreview();
  await settle();
  const printableMarginsExplained =
    document.querySelector('[data-testid="preview-printable-area"]')?.textContent?.includes("50 × 30 mm roll") ===
      true && document.querySelector('[data-testid="preview-printable-area"]')?.textContent?.includes("47.4") === true;
  const simplePrintPreview =
    !!document.querySelector('.modal.show [aria-label="Copies"]') &&
    !document.querySelector(".modal.show .param-lock-btn") &&
    !document.querySelector(".modal.show #threshold") &&
    document.querySelectorAll(".modal.show input, .modal.show select").length === 1;
  const advanced = document.querySelector<HTMLDetailsElement>('[data-testid="print-advanced"]')!;
  advanced.open = true;
  advanced.dispatchEvent(new Event("toggle"));
  await tick();
  const advancedPrintControlsAvailable =
    !!document.querySelector(".modal.show #threshold") && !document.querySelector('.modal.show option[value="B1"]');
  const advancedPrintTooltips = Array.from(
    document.querySelectorAll<HTMLElement>(
      '[data-testid="print-advanced"] input, [data-testid="print-advanced"] select, [data-testid="print-advanced"] button',
    ),
  ).every((control) => (control.title?.length ?? 0) > 20);
  await nativeRequest("testSnapshot", { name: "print-advanced" });
  advanced.open = false;
  advanced.dispatchEvent(new Event("toggle"));
  await tick();
  await nativeRequest("testSnapshot", { name: "stock-printable-area" });
  await click(".modal.show .btn-close");
  await waitFor(() => !document.querySelector(".modal.show"), "closed margin preview");
  const overrideResults = await runStockOverrideSmoke(context.openPreview);

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
    rollReadExplained,
    rememberedRollWorks,
    rememberedRollCannotOverrideConflictingReport,
    rememberedRollCanBeChanged,
    physicalStockFilterCorrect,
    fiftyMmRollSupported,
    printableMarginsExplained,
    simplePrintPreview,
    advancedPrintControlsAvailable,
    advancedPrintTooltips,
    ...overrideResults,
    ...settingsResults,
  };
}
