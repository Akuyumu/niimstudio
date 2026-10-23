/** Display-only scaling must never change document geometry or exported pixels. */
import { tick } from "svelte";
import type { CustomCanvas } from "$/fabric-object/custom_canvas";
import { nativeRequest } from "$/desktop/bridge";

export async function runDisplaySmoke(canvas: CustomCanvas) {
  const frames = () =>
    new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve())));
  await frames();
  const viewport = document.querySelector<HTMLElement>(".canvas-viewport")!;
  const initialZoomFitsWholeLabel =
    viewport.scrollWidth <= viewport.clientWidth + 2 && viewport.scrollHeight <= viewport.clientHeight + 2;
  const width = canvas.getWidth(),
    height = canvas.getHeight();
  const objects = JSON.stringify(canvas.toObject());
  canvas.virtualZoom(1);
  canvas.renderAll();
  const before = canvas.toCanvasElement();
  const originalPixels = before.getContext("2d")!.getImageData(0, 0, width, height).data;
  canvas.virtualZoom(2);
  canvas.renderAll();
  await tick();
  const rectangle = canvas.getElement().getBoundingClientRect();
  const zoomRendersAtDisplayResolution =
    canvas.getElement().width >= width * 2 && canvas.getElement().height >= height * 2;
  const point = canvas.getScenePoint(
    new MouseEvent("mousemove", {
      clientX: rectangle.left + rectangle.width / 2,
      clientY: rectangle.top + rectangle.height / 2,
    }),
  );
  const zoomHitTestingAligned = Math.abs(point.x - width / 2) < 1 && Math.abs(point.y - height / 2) < 1;
  canvas.virtualZoom(4);
  canvas.renderAll();
  const exported = canvas.toCanvasElement();
  const newPixels = exported.getContext("2d")!.getImageData(0, 0, width, height).data;
  const zoomDoesNotChangePrintPixels =
    exported.width === width &&
    exported.height === height &&
    originalPixels.every((value, index) => value === newPixels[index]);
  const zoomKeepsDocumentGeometry =
    canvas.getWidth() === width && canvas.getHeight() === height && JSON.stringify(canvas.toObject()) === objects;
  viewport.style.maxWidth = "420px";
  canvas.virtualZoom(4, "user");
  canvas.renderAll();
  viewport.dispatchEvent(new Event("scroll"));
  await frames();
  await tick();
  const clippedViewIsIndicated =
    document.querySelector(".studio-canvas-clip-note")?.textContent?.includes("scroll to see") === true;
  await nativeRequest("testSnapshot", { name: "zoom-clipped" });
  const upper = viewport.querySelector<HTMLCanvasElement>(".upper-canvas")!;
  const rect = upper.getBoundingClientRect();
  const scrollBeforePlainMiddle = viewport.scrollLeft;
  upper.dispatchEvent(
    new MouseEvent("mousedown", {
      bubbles: true,
      cancelable: true,
      button: 1,
      buttons: 4,
      clientX: rect.left + 160,
      clientY: rect.top + 80,
    }),
  );
  upper.dispatchEvent(
    new MouseEvent("mousemove", {
      bubbles: true,
      cancelable: true,
      button: 1,
      buttons: 4,
      clientX: rect.left + 60,
      clientY: rect.top + 40,
    }),
  );
  upper.dispatchEvent(
    new MouseEvent("mouseup", {
      bubbles: true,
      cancelable: true,
      button: 1,
      clientX: rect.left + 60,
      clientY: rect.top + 40,
    }),
  );
  await frames();
  const plainMiddleDoesNotPan = viewport.scrollLeft === scrollBeforePlainMiddle;
  const scrollBeforePan = viewport.scrollLeft;
  for (const type of ["mousedown", "mousemove", "mouseup"]) {
    upper.dispatchEvent(
      new MouseEvent(type, {
        bubbles: true,
        cancelable: true,
        button: 1,
        buttons: type === "mouseup" ? 0 : 4,
        ctrlKey: true,
        clientX: rect.left + (type === "mousemove" ? 60 : 160),
        clientY: rect.top + (type === "mousemove" ? 40 : 80),
      }),
    );
  }
  await frames();
  const middleDragPansViewport = viewport.scrollLeft > scrollBeforePan;
  viewport.style.maxWidth = "";
  document.querySelector<HTMLButtonElement>('[data-action="fit-zoom"]')!.click();
  await frames();
  const fitButtonShowsWholeLabel =
    viewport.scrollWidth <= viewport.clientWidth + 2 && viewport.scrollHeight <= viewport.clientHeight + 2;
  viewport.style.maxWidth = "500px";
  await frames();
  const fitTracksViewportResize =
    viewport.scrollWidth <= viewport.clientWidth + 2 && viewport.scrollHeight <= viewport.clientHeight + 2;
  viewport.style.maxWidth = "";
  viewport.style.height = "240px";
  await frames();
  const fitTracksViewportHeightResize =
    viewport.scrollWidth <= viewport.clientWidth + 2 && viewport.scrollHeight <= viewport.clientHeight + 2;
  viewport.style.height = "";
  document.querySelector<HTMLButtonElement>('[data-action="fit-zoom"]')!.click();
  await frames();
  const font = document.querySelector<HTMLInputElement>('.studio-formatting [aria-label="Font family"]')!;
  const fontNameUsesAvailableSpace = font.clientWidth >= 180;
  const devices = document.querySelector<HTMLElement>('[data-action="devices"]')!.getBoundingClientRect();
  const settings = document.querySelector<HTMLElement>('[data-action="settings"]')!.getBoundingClientRect();
  const headerButtonsAligned =
    Math.abs(devices.y - settings.y) < 1 &&
    Math.abs(devices.height - settings.height) < 1 &&
    !document.querySelector(".studio-reconnect-status");
  await nativeRequest("testSnapshot", { name: "crisp-text" });
  return {
    zoomRendersAtDisplayResolution,
    zoomHitTestingAligned,
    zoomDoesNotChangePrintPixels,
    zoomKeepsDocumentGeometry,
    initialZoomFitsWholeLabel,
    clippedViewIsIndicated,
    plainMiddleDoesNotPan,
    middleDragPansViewport,
    fitButtonShowsWholeLabel,
    fitTracksViewportResize,
    fitTracksViewportHeightResize,
    fontNameUsesAvailableSpace,
    headerButtonsAligned,
  };
}
