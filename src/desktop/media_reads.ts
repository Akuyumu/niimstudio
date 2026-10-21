/** Preserve read errors that the inherited convenience method normally hides. */
import { writable } from "svelte/store";
import type { CombinedRfidInfo, NiimbotProtocol } from "@mmote/niimbluelib";

export type MediaReadReport = Partial<Record<"label" | "paper" | "ribbon", string>>;
export const mediaReadReport = writable<MediaReadReport>({});

export async function readMedia(protocol: Pick<NiimbotProtocol, "rfidInfo" | "getPaperInfo" | "rfidInfo2">) {
  const info: CombinedRfidInfo = {};
  const errors: MediaReadReport = {};
  try {
    info.labelRfidInfo = await protocol.rfidInfo();
  } catch (error) {
    errors.label = error instanceof Error ? error.message : String(error);
  }
  try {
    info.paperInfo = await protocol.getPaperInfo();
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
