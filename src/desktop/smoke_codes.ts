/** Exercise the visible code-entry flows, then export their real label objects. */
import { tick } from "svelte";
import type { FabricObject } from "fabric";
import type { CustomCanvas } from "$/fabric-object/custom_canvas";
import { nativeRequest } from "$/desktop/bridge";

const settle = async () => {
  await tick();
  await new Promise((resolve) => setTimeout(resolve, 550));
};
const click = (selector: string) => {
  const button = document.querySelector<HTMLButtonElement>(selector);
  if (!button) throw new Error(`Missing code control: ${selector}`);
  button.click();
};
const fill = async (value: string) => {
  const input = document.querySelector<HTMLTextAreaElement>("#studio-code-content")!;
  input.value = value;
  input.dispatchEvent(new Event("input", { bubbles: true }));
  await tick();
};
const submit = async () => {
  document.querySelector<HTMLFormElement>("#studio-code-form")!.requestSubmit();
  await settle();
};
const raster = (object: FabricObject) => {
  const source = object.toCanvasElement();
  const padded = document.createElement("canvas");
  padded.width = source.width + 32;
  padded.height = source.height + 32;
  const context = padded.getContext("2d")!;
  context.fillStyle = "white";
  context.fillRect(0, 0, padded.width, padded.height);
  context.drawImage(source, 16, 16);
  return padded.toDataURL("image/png");
};

export async function runCodeSmoke(canvas: CustomCanvas) {
  canvas.clear();
  click('[data-action="insert-qrcode"]');
  await settle();
  await fill("https://example.com/niimstudio");
  await nativeRequest("testSnapshot", { name: "qr-dialog" });
  await submit();
  const qr = canvas.getActiveObject()!;
  const qrInserted = qr.get("text") === "https://example.com/niimstudio" && qr.get("quietZone") === 4;
  const artifacts: Record<string, string> = { "qr-url.png": raster(qr) };
  await tick();
  click('[data-action="edit-code"]');
  await settle();
  await fill("https://example.com/updated");
  await submit();
  const qrEdited = qr.get("text") === "https://example.com/updated" && canvas.getObjects().length === 1;

  click('[data-action="insert-barcode"]');
  await settle();
  await fill("https://a.co");
  await nativeRequest("testSnapshot", { name: "barcode-dialog" });
  await submit();
  const barcode = canvas.getActiveObject()!;
  const barcodeInserted = barcode.get("text") === "https://a.co" && barcode.get("encoding") === "CODE128B";
  artifacts["barcode-url.png"] = raster(barcode);
  await tick();
  click('[data-action="edit-code"]');
  await settle();
  await fill("$)");
  await submit();
  const barcodeEdited = barcode.get("text") === "$)" && canvas.getObjects().length === 2;
  artifacts["barcode-special.png"] = raster(barcode);

  click('[data-action="insert-barcode"]');
  await settle();
  const format = document.querySelector<HTMLSelectElement>(".studio-code-options select")!;
  format.value = "EAN13";
  format.dispatchEvent(new Event("change", { bubbles: true }));
  await fill("123");
  await submit();
  const rejectsInvalidEan = !!document.querySelector(".studio-code-error") && canvas.getObjects().length === 2;
  await fill("590123412345");
  await submit();
  const ean = canvas.getActiveObject()!;
  const eanInserted = ean.get("text") === "5901234123457" && ean.get("encoding") === "EAN13";
  artifacts["ean13.png"] = raster(ean);

  click('[data-action="insert-qrcode"]');
  await settle();
  const cancel = Array.from(document.querySelectorAll<HTMLButtonElement>(".modal.show button")).find(
    (button) => button.textContent?.trim() === "Cancel",
  )!;
  cancel.click();
  await settle();
  const cancelDoesNotInsert = !document.querySelector("#studio-code-form") && canvas.getObjects().length === 3;
  return {
    qrInserted,
    qrEdited,
    barcodeInserted,
    barcodeEdited,
    rejectsInvalidEan,
    eanInserted,
    cancelDoesNotInsert,
    artifacts,
  };
}
