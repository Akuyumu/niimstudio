/** Preserve read errors that the inherited convenience method normally hides. */
import { writable } from "svelte/store";
import type { CombinedRfidInfo, NiimbotProtocol, PaperInfo } from "@mmote/niimbluelib";

export function normalizePaperHeight(paper: PaperInfo, modelId?: number): PaperInfo {
  // Backport upstream 45ef990007e5ba3b257a9a81332e75ffcdf7b442 without
  // changing the pinned protocol or its packet parser. B1 Pro 2.12 reports
  // 30mm/354px sticker height plus a separate 6mm/70px gap. Subtraction is
  // wrong here. Keep the old interpretation for other, unverified models.
  if (modelId !== 4097 || !paper.valid || !(paper.totalHeight! > 0) || !(paper.totalHeightPixel! > 0)) return paper;
  return { ...paper, paperHeight: paper.totalHeight, paperHeightPixel: paper.totalHeightPixel };
}

export type MediaReadReport = Partial<Record<"label" | "paper" | "ribbon", string>>;
export const mediaReadReport = writable<MediaReadReport>({});

export async function readMedia(
  protocol: Pick<NiimbotProtocol, "rfidInfo" | "getPaperInfo" | "rfidInfo2">,
  modelId?: number,
) {
  const info: CombinedRfidInfo = {};
  const errors: MediaReadReport = {};
  try {
    info.labelRfidInfo = await protocol.rfidInfo();
  } catch (error) {
    errors.label = error instanceof Error ? error.message : String(error);
  }
  try {
    info.paperInfo = normalizePaperHeight(await protocol.getPaperInfo(), modelId);
  } catch (error) {
    errors.paper = error instanceof Error ? error.message : String(error);
  }
  try {
    info.ribbonRfidInfo = await protocol.rfidInfo2();
  } catch (error) {
    errors.ribbon = error instanceof Error ? error.message : String(error);
  }
  return { info, errors };
}
