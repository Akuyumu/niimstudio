/** Loaded only in the isolated --smoke-test profile. Never sends printer bytes. */
import { tick } from "svelte";
import { ImageEncoder, PageColorType } from "@mmote/niimbluelib";
import type { CustomCanvas } from "$/fabric-object/custom_canvas";
import { ExportedLabelTemplateSchema, type ExportedLabelTemplate, type LabelProps, type OjectType } from "$/types";
import { LocalStoragePersistence } from "$/utils/persistence";
import { LabelDesignerObjectHelper } from "$/utils/label_designer_object_helper";
import type { UndoRedo } from "$/utils/undo_redo";
import { nativeRequest } from "$/desktop/bridge";
import { runCodeSmoke } from "$/desktop/smoke_codes";
import { get } from "svelte/store";
import { connectionState } from "$/stores";
import { runStockSmoke } from "$/desktop/smoke_stock";
import { runOverlaySmoke } from "$/desktop/smoke_overlays";
import { runLibraryCacheSmoke } from "$/desktop/smoke_library_cache";
import { NativeNiimbotClient } from "$/desktop/client";

export async function runEditorSmoke(context: {
  canvas: CustomCanvas;
  labelProps: LabelProps;
  undo: UndoRedo;
  addObject: (type: OjectType) => void;
  exportLabel: () => ExportedLabelTemplate;
  loadLabel: (label: ExportedLabelTemplate) => Promise<void>;
  saveDraft: () => void;
  openPreview: () => void;
}) {
  const runtimeErrors: string[] = [];
  const onError = (event: ErrorEvent) => runtimeErrors.push(event.message);
  const onRejected = (event: PromiseRejectionEvent) => runtimeErrors.push(String(event.reason));
  window.addEventListener("error", onError);
  window.addEventListener("unhandledrejection", onRejected);
  const { canvas, labelProps, undo } = context;
  const showcase = { ...context.exportLabel(), title: window.__NIIMSTUDIO_DEMO__ ? "Coffee beans" : "Example label" };
  const { overlayFrames, ...overlayResults } = await runOverlaySmoke();
  const overlaysWork = Object.values(overlayResults).every(Boolean);
  await nativeRequest("testUpdate");
  const updateDeadline = Date.now() + 3000;
  while (!document.querySelector('[data-testid="update-banner"]') && Date.now() < updateDeadline) {
    await new Promise((resolve) => setTimeout(resolve, 25));
    await tick();
  }
  const banner = document.querySelector<HTMLElement>('[data-testid="update-banner"]');
  const updateBannerWorks =
    !!banner && banner.textContent!.includes("9.9.9") && !!banner.querySelector('[data-action="update-now"]');
  banner?.querySelector<HTMLButtonElement>('[data-action="update-later"]')?.click();
  await tick();
  const updateBannerDismisses = !document.querySelector('[data-testid="update-banner"]');
  const cacheResults = await runLibraryCacheSmoke(showcase);
  const cacheWorks = Object.values(cacheResults).every(Boolean);
  const stockResults = await runStockSmoke(context);
  const stockSetupWorks = Object.values(stockResults).every(Boolean);
  await context.loadLabel({ ...showcase, label: { ...showcase.label, shape: "rect" } });
  await tick();
  const rectangleWorks = getComputedStyle(document.querySelector(".canvas-wrapper")!).borderRadius === "0px";
  await context.loadLabel({ ...showcase, label: { ...showcase.label, shape: "circle" } });
  await tick();
  const circleWorks = getComputedStyle(document.querySelector(".canvas-wrapper")!).borderRadius === "50%";
  await context.loadLabel(showcase);
  await tick();
  const stockShapesCorrect =
    rectangleWorks &&
    circleWorks &&
    Number.parseFloat(getComputedStyle(document.querySelector(".canvas-wrapper")!).borderRadius) > 0;
  canvas.clear();
  undo.push(canvas, labelProps);
  for (const type of ["text", "qrcode", "barcode", "rectangle", "circle", "line", "aruco"] as OjectType[]) {
    LabelDesignerObjectHelper.addObject(canvas, type);
    undo.push(canvas, labelProps);
  }
  const raster = document.createElement("canvas");
  raster.width = raster.height = 16;
  raster.getContext("2d")!.fillRect(0, 0, 8, 8);
  const blob = await new Promise<Blob>((resolve) => raster.toBlob((b) => resolve(b!)));
  await LabelDesignerObjectHelper.addImageBlob(canvas, blob);
  undo.push(canvas, labelProps);
  const before = canvas.getObjects().length;
  await undo.undo();
  const afterUndo = canvas.getObjects().length;
  await undo.redo();
  const afterRedo = canvas.getObjects().length;
  const exported = ExportedLabelTemplateSchema.parse(context.exportLabel());
  LocalStoragePersistence.validateAndSaveObject("smoke_label", exported, ExportedLabelTemplateSchema);
  const loaded = LocalStoragePersistence.loadAndValidateObject("smoke_label", ExportedLabelTemplateSchema)!;
  await context.loadLabel(loaded);
  LocalStoragePersistence.saveLabels([exported]);
  const libraryBefore = JSON.stringify(LocalStoragePersistence.loadLabels());
  const badSave = LocalStoragePersistence.saveLabels([
    { ...exported, label: { ...labelProps, size: { width: -1, height: 2 } } },
  ]);
  const rejectsInvalidSave =
    badSave.zodErrors.length === 1 && JSON.stringify(LocalStoragePersistence.loadLabels()) === libraryBefore;
  const originalSetItem = Storage.prototype.setItem;
  let failOnce = true;
  Storage.prototype.setItem = function (key: string, value: string) {
    if (key.startsWith("saved_label") && failOnce) {
      failOnce = false;
      throw new DOMException("Storage quota test", "QuotaExceededError");
    }
    return originalSetItem.call(this, key, value);
  };
  let quotaRollback = false;
  try {
    const failed = LocalStoragePersistence.saveLabels([exported, exported]);
    quotaRollback =
      failed.otherErrors.length === 1 && JSON.stringify(LocalStoragePersistence.loadLabels()) === libraryBefore;
  } finally {
    Storage.prototype.setItem = originalSetItem;
  }
  context.saveDraft();
  LocalStoragePersistence.saveLabels([showcase]);
  await context.loadLabel(showcase);
  document.querySelector<HTMLButtonElement>('[data-action="templates"]')!.click();
  await tick();
  const drawer = document.querySelector<HTMLDialogElement>(".studio-template-drawer")!;
  const drawerWorks = drawer.open && drawer.querySelectorAll(".studio-template-card").length === 1;
  await nativeRequest("testSnapshot", { name: "templates" });
  const search = drawer.querySelector<HTMLInputElement>("input[type=search]")!;
  search.value = "no-template-matches-this";
  search.dispatchEvent(new Event("input", { bubbles: true }));
  await tick();
  const searchWorks = drawer.querySelectorAll(".studio-template-card").length === 0;
  drawer.close();
  document.querySelector<HTMLButtonElement>('[data-action="save-template"]')!.click();
  await tick();
  await new Promise((resolve) => setTimeout(resolve, 550));
  const name = document.querySelector<HTMLInputElement>("#studio-template-name")!;
  name.value = "Smoke template";
  name.dispatchEvent(new Event("input", { bubbles: true }));
  await tick();
  document.querySelector<HTMLFormElement>("#studio-save-template")!.requestSubmit();
  await tick();
  await new Promise((resolve) => setTimeout(resolve, 550));
  const templateSaveWorks = LocalStoragePersistence.loadLabels().some((label) => label.title === "Smoke template");
  context.addObject("text");
  await tick();
  const selectedText = canvas.getActiveObject();
  document.querySelector<HTMLButtonElement>('button[aria-label="Bold"]')!.click();
  document.querySelector<HTMLButtonElement>('button[aria-label="Underline"]')!.click();
  document.querySelector<HTMLButtonElement>('button[aria-label="Align text center"]')!.click();
  await tick();
  const formattingWorks =
    selectedText?.get("fontWeight") === "bold" &&
    selectedText?.get("underline") === true &&
    selectedText?.get("textAlign") === "center";
  const displayResults = await (await import("$/desktop/smoke_display")).runDisplaySmoke(canvas);
  const displayWorks = Object.values(displayResults).every(Boolean);
  canvas.remove(selectedText!);
  const codeChecks = await runCodeSmoke(canvas);
  const { artifacts, ...codeResults } = codeChecks;
  const codesWork = Object.values(codeResults).every(Boolean);
  const deviceButton = Array.from(document.querySelectorAll<HTMLButtonElement>(".studio-printer button")).find(
    (button) => button.textContent?.includes("Devices"),
  )!;
  deviceButton.click();
  await new Promise((resolve) => setTimeout(resolve, 250));
  const deviceChooserOpened = await nativeRequest<boolean>("testDismissDevices");
  await new Promise((resolve) => setTimeout(resolve, 150));
  const deviceCancellationSilent =
    deviceChooserOpened && get(connectionState) === "disconnected" && !document.querySelector(".toast-danger");
  const originalConnect = NativeNiimbotClient.prototype.connect;
  let connectionFailureHelpful = false;
  let connectionFailureDismisses = false;
  try {
    NativeNiimbotClient.prototype.connect = async () => {
      throw new Error("org.bluez.Error.AuthenticationRejected");
    };
    deviceButton.click();
    const deadline = Date.now() + 3000;
    while (!document.querySelector('[data-testid="connection-failure"]') && Date.now() < deadline) {
      await new Promise((resolve) => setTimeout(resolve, 25));
      await tick();
    }
    const failure = document.querySelector<HTMLElement>('[data-testid="connection-failure"]');
    connectionFailureHelpful =
      !!failure &&
      failure.textContent!.includes("AuthenticationRejected") &&
      failure.textContent!.includes("Pair") &&
      failure.textContent!.includes("Bluetooth LE") &&
      failure.getAttribute("role") === "alert" &&
      get(connectionState) === "disconnected";
    await nativeRequest("testSnapshot", { name: "connection-failure" });
    failure?.querySelector<HTMLButtonElement>('[aria-label="Dismiss connection error"]')?.click();
    await tick();
    connectionFailureDismisses = !document.querySelector('[data-testid="connection-failure"]');
  } finally {
    NativeNiimbotClient.prototype.connect = originalConnect;
  }
  canvas.renderAll();
  const encoded = ImageEncoder.encodeCanvas(canvas.getElement(), PageColorType.SingleColor, labelProps.printDirection);
  context.openPreview();
  await tick();
  await new Promise((resolve) => setTimeout(resolve, 1200));
  const preview = document.querySelector<HTMLCanvasElement>(".modal canvas");
  await nativeRequest("testSnapshot", { name: "print-preview" });
  window.removeEventListener("error", onError);
  window.removeEventListener("unhandledrejection", onRejected);
  return {
    ok:
      before === 8 &&
      afterUndo === 7 &&
      afterRedo === 8 &&
      !!preview?.width &&
      !!encoded &&
      rejectsInvalidSave &&
      quotaRollback &&
      drawerWorks &&
      searchWorks &&
      templateSaveWorks &&
      formattingWorks &&
      displayWorks &&
      codesWork &&
      deviceCancellationSilent &&
      connectionFailureHelpful &&
      connectionFailureDismisses &&
      stockShapesCorrect &&
      stockSetupWorks &&
      overlaysWork &&
      cacheWorks &&
      updateBannerWorks &&
      updateBannerDismisses &&
      runtimeErrors.length === 0,
    objects: before,
    afterUndo,
    afterRedo,
    exportedObjects: loaded.canvas.objects.length,
    preview: preview ? [preview.width, preview.height] : null,
    theme: getComputedStyle(document.documentElement).getPropertyValue("--studio-accent").trim(),
    draft: !!localStorage.getItem("studio_draft"),
    rejectsInvalidSave,
    quotaRollback,
    drawerWorks,
    searchWorks,
    templateSaveWorks,
    formattingWorks,
    ...displayResults,
    ...codeResults,
    deviceCancellationSilent,
    connectionFailureHelpful,
    connectionFailureDismisses,
    stockShapesCorrect,
    ...stockResults,
    ...overlayResults,
    ...cacheResults,
    updateBannerWorks,
    updateBannerDismisses,
    runtimeErrors,
    overlayFrames: overlaysWork ? undefined : overlayFrames,
    artifacts,
  };
}
