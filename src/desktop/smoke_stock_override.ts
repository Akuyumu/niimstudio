/** Only synthetic stores/protocol doubles; no printer transport is used. */
import { tick } from "svelte";
import { get } from "svelte/store";
import type { NiimbotAbstractClient } from "@mmote/niimbluelib";
import { connectionState, printerClient, printJobActive, rfidInfo, stockOverride, printerInfo } from "$/stores";
import { normalizePaperHeight } from "$/desktop/media_reads";
import { nativeRequest } from "$/desktop/bridge";

const waitFor = async (check: () => boolean) => {
  await tick();
  const deadline = Date.now() + 8000;
  while (!check()) {
    if (Date.now() > deadline)
      throw new Error(
        `Override/print guard did not settle: ${document.querySelector(".modal.show")?.textContent?.slice(0, 700)}`,
      );
    await new Promise((resolve) => setTimeout(resolve, 40));
    await tick();
  }
};
const click = async (selector: string) => {
  await waitFor(
    () =>
      !!document.querySelector<HTMLButtonElement>(selector) &&
      !document.querySelector<HTMLButtonElement>(selector)!.disabled,
  );
  document.querySelector<HTMLButtonElement>(selector)!.click();
  await tick();
};

export async function runStockOverrideSmoke(openPreview: () => void) {
  const originalClient = get(printerClient);
  const tag = {
    tagPresent: true,
    uuid: "override-fixture",
    serialNumber: "synthetic",
    barCode: "TEST-OVERRIDE",
    allPaper: 100,
    usedPaper: 0,
    consumablesType: 1,
  };
  const reported = {
    valid: true,
    gapHeightPixel: 70,
    totalHeightPixel: 354,
    paperType: 1,
    gapHeight: 6,
    totalHeight: 30,
    paperWidthPixel: 590,
    paperWidth: 50,
    direction: 0,
    tailLengthPixel: 0,
    tailLength: 0,
    paperHeight: 24,
    paperHeightPixel: 284,
  };
  rfidInfo.set({ labelRfidInfo: tag, paperInfo: reported });
  await waitFor(() => !!document.querySelector('[data-action="override-stock"]'));
  await click('[data-action="override-stock"]');
  await click('[data-action="keep-stock-design"]');
  const overrideCancelKeepsDetection =
    !get(stockOverride) && !!document.querySelector('[data-action="override-stock"]');
  await click('[data-action="override-stock"]');
  await click('[data-stock-id="50x30"]');
  await waitFor(() => !document.querySelector(".modal.show"));
  const manualOverrideApplied =
    get(stockOverride)?.stock.heightMm === 30 &&
    document.querySelector('[data-action="label-stock"]')?.textContent?.includes("Manual") === true;
  await click('[data-action="label-stock"]');
  const overrideClearlyLabelled =
    !!document.querySelector('[data-testid="manual-stock-warning"]') &&
    !document.querySelector('[data-testid="detected-stock"].text-success');
  await nativeRequest("testSnapshot", { name: "stock-override" });
  await click('[data-action="restore-stock-detection"]');
  const overrideCanRestoreDetection =
    !get(stockOverride) && !document.querySelector('[data-testid="manual-stock-warning"]');
  await click('[data-action="override-stock"]');
  await click('[data-stock-id="50x30"]');
  await waitFor(() => !document.querySelector(".modal.show"));
  await click('[data-action="label-stock"]');
  await click(".modal.show .btn-close");
  await waitFor(() => !document.querySelector(".modal.show"));

  let created = 0,
    cleaned = 0,
    genericEnd = 0,
    printPages = 0;
  let factoryFailure = true;
  const fake = {
    getPrintTaskType: () => "D110M_V4",
    stopHeartbeat: () => {},
    startHeartbeat: () => {},
    on: () => {},
    off: () => {},
    protocol: {
      newPrintTask: () => {
        created++;
        if (factoryFailure) throw new Error("Synthetic task factory failed");
        return {
          printInit: async () => {
            throw new Error("Synthetic task init failed");
          },
          printEnd: async () => {
            cleaned++;
          },
          printPage: async () => {
            printPages++;
          },
        };
      },
      printEnd: async () => {
        genericEnd++;
      },
    },
  } as unknown as NiimbotAbstractClient;
  printerClient.set(fake);
  let manualOverrideReachesPreview = false,
    taskFactoryFailureUnlocksUI = false,
    taskInitFailureUnlocksUI = false,
    oversizedOffsetsCannotStartPrint = false;
  try {
    openPreview();
    await waitFor(() => !!document.querySelector('[data-testid="preview-manual-stock"]'));
    manualOverrideReachesPreview =
      document.querySelector('[data-testid="preview-manual-stock"]')?.textContent?.includes("50 × 30") === true;
    await click('[data-action="print-label"]');
    await waitFor(
      () =>
        !get(printJobActive) &&
        document.querySelector('.modal.show [role="alert"]')?.textContent?.includes("Synthetic task factory failed") ===
          true,
    );
    taskFactoryFailureUnlocksUI =
      created === 1 &&
      genericEnd === 0 &&
      !document.querySelector<HTMLButtonElement>('[data-action="print-label"]')!.disabled;
    factoryFailure = false;
    await click('[data-action="print-label"]');
    await waitFor(
      () =>
        !get(printJobActive) &&
        document.querySelector('.modal.show [role="alert"]')?.textContent?.includes("Synthetic task init failed") ===
          true,
    );
    taskInitFailureUnlocksUI =
      created === 2 &&
      cleaned === 1 &&
      printPages === 0 &&
      !document.querySelector<HTMLButtonElement>('[data-action="print-label"]')!.disabled;

    const advanced = document.querySelector<HTMLDetailsElement>('[data-testid="print-advanced"]')!;
    advanced.open = true;
    advanced.dispatchEvent(new Event("toggle"));
    await tick();
    const x = document.querySelector<HTMLInputElement>('[aria-label="Horizontal position adjustment"]')!;
    const boundary = document.querySelector<HTMLSelectElement>('[aria-label="Position adjustment boundary"]')!;
    x.value = "100";
    x.dispatchEvent(new Event("input", { bubbles: true }));
    boundary.value = "outer";
    boundary.dispatchEvent(new Event("change", { bubbles: true }));
    await tick();
    await click('[data-action="print-label"]');
    await waitFor(
      () =>
        !get(printJobActive) &&
        document.querySelector('.modal.show [role="alert"]')?.textContent?.includes("supports 567") === true,
    );
    oversizedOffsetsCannotStartPrint = created === 2 && printPages === 0;
    x.value = "0";
    x.dispatchEvent(new Event("input", { bubbles: true }));
    boundary.value = "inner";
    boundary.dispatchEvent(new Event("change", { bubbles: true }));
    await tick();
    await click(".modal.show .btn-close");
    await waitFor(() => !document.querySelector(".modal.show"));
  } finally {
    printerClient.set(originalClient);
  }

  rfidInfo.set({ labelRfidInfo: { ...tag, usedPaper: 1 }, paperInfo: reported });
  await tick();
  const usageCountDoesNotExpireOverride = !!get(stockOverride);
  rfidInfo.set({ labelRfidInfo: { ...tag, uuid: "changed-roll" }, paperInfo: reported });
  await waitFor(() => !get(stockOverride));
  const changedRollExpiresOverride =
    !get(stockOverride) && !document.querySelector('[data-testid="manual-stock-warning"]');
  if (document.querySelector(".modal.show")) await click(".modal.show .btn-close");
  await waitFor(() => !document.querySelector(".modal.show"));

  printerInfo.update((info) => ({ ...info, printheadWidth: 576 }));
  rfidInfo.set({ labelRfidInfo: tag, paperInfo: normalizePaperHeight(reported, 4097) });
  await waitFor(
    () => document.querySelector('[data-testid="detected-stock"]')?.textContent?.includes("50 × 30") === true,
  );
  const realReplyHeightCorrected =
    document.querySelector('[data-testid="detected-stock"]')?.textContent?.includes("50 × 30") === true;
  await nativeRequest("testSnapshot", { name: "stock-height-corrected" });
  await click('[data-action="override-stock"]');
  await click('[data-stock-id="40x30"]');
  await waitFor(() => !document.querySelector(".modal.show"));
  connectionState.set("disconnected");
  await tick();
  const reconnectExpiresOverride = !get(stockOverride);
  connectionState.set("connected");
  await tick();
  if (document.querySelector(".modal.show")) await click(".modal.show .btn-close");
  return {
    overrideCancelKeepsDetection,
    manualOverrideApplied,
    overrideClearlyLabelled,
    overrideCanRestoreDetection,
    manualOverrideReachesPreview,
    taskFactoryFailureUnlocksUI,
    taskInitFailureUnlocksUI,
    oversizedOffsetsCannotStartPrint,
    usageCountDoesNotExpireOverride,
    changedRollExpiresOverride,
    reconnectExpiresOverride,
    realReplyHeightCorrected,
  };
}
