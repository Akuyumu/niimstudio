/** Repeated overlays must not resize the viewport, shift the editor or leak backdrops. */
import { tick } from "svelte";

const pause = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));
const waitFor = async (condition: () => boolean) => {
  const deadline = Date.now() + 5000;
  while (!condition()) {
    if (Date.now() > deadline) throw new Error("Overlay did not settle");
    await pause(25);
    await tick();
  }
};
const metrics = () => {
  const heading = document.querySelector(".studio-editor-title")!.getBoundingClientRect();
  const canvas = document.querySelector(".canvas-wrapper")!.getBoundingClientRect();
  return {
    width: innerWidth,
    height: innerHeight,
    headingX: heading.x,
    headingY: heading.y,
    canvasX: canvas.x,
    canvasY: canvas.y,
    canvasWidth: canvas.width,
    canvasHeight: canvas.height,
  };
};
const click = (selector: string) => document.querySelector<HTMLButtonElement>(selector)!.click();

export async function runOverlaySmoke() {
  click('[data-action="more-tools"]');
  await tick();
  const more = document.querySelector<HTMLElement>('[data-testid="more-tools-menu"]')!;
  const moreHasNoDuplicates =
    more.classList.contains("show") &&
    Array.from(more.querySelectorAll<HTMLElement>("[data-object-type]"))
      .map((button) => button.dataset.objectType)
      .join(",") === "aruco" &&
    more.textContent!.includes("ZPL") &&
    more.textContent!.includes("PDF");
  click('[data-action="more-tools"]');
  const initial = metrics();
  const frames = [initial];
  let drawerMotionAndBlurFree = true;
  let nativeModalMotionFree = true;
  let retainedStockDialog = true;
  let modalFocusWorks = true;
  let firstStockDialog: HTMLDialogElement | undefined;
  const sample = async () => {
    for (let frame = 0; frame < 6; frame++) {
      await pause(40);
      frames.push(metrics());
    }
  };
  for (let cycle = 0; cycle < 3; cycle++) {
    click('[data-action="templates"]');
    await tick();
    const drawer = document.querySelector<HTMLDialogElement>(".studio-template-drawer")!;
    drawerMotionAndBlurFree &&=
      getComputedStyle(drawer).animationName === "none" &&
      !getComputedStyle(drawer, "::backdrop").getPropertyValue("backdrop-filter").includes("blur");
    await sample();
    drawer.close();
    await tick();
    await sample();
    const trigger = document.querySelector<HTMLButtonElement>('[data-action="label-stock"]')!;
    trigger.focus();
    trigger.click();
    await waitFor(() => !!document.querySelector('.modal[data-modal-ready="true"]'));
    nativeModalMotionFree &&= !document.querySelector(".modal.fade") && !document.querySelector(".modal-backdrop.fade");
    const stock = document.querySelector<HTMLDialogElement>(".modal.show")!;
    firstStockDialog ??= stock;
    retainedStockDialog &&= stock === firstStockDialog;
    modalFocusWorks &&= stock.open && stock.contains(document.activeElement);
    await sample();
    if (cycle === 0) click(".modal.show .btn-close");
    else if (cycle === 1) stock.dispatchEvent(new Event("cancel", { cancelable: true }));
    else stock.dispatchEvent(new PointerEvent("pointerdown", { clientX: -1, clientY: -1, bubbles: true }));
    await waitFor(() => !document.querySelector(".modal.show"));
    await sample();
    modalFocusWorks &&= document.activeElement === trigger;
  }
  const overlaysKeepViewport = frames.every(
    (frame) => frame.width === initial.width && frame.height === initial.height,
  );
  const overlayEditorStationary = frames.every((frame) =>
    ["headingX", "headingY", "canvasX", "canvasY", "canvasWidth", "canvasHeight"].every(
      (key) => Math.abs(frame[key as keyof typeof frame] - initial[key as keyof typeof initial]) < 1,
    ),
  );
  const overlayCleanup =
    !document.querySelector(".modal-backdrop, .modal.show, dialog[open]") &&
    !document.body.classList.contains("modal-open");
  const uniqueFrames = Array.from(new Map(frames.map((frame) => [JSON.stringify(frame), frame])).values()).slice(0, 8);
  return {
    overlaysKeepViewport,
    overlayEditorStationary,
    drawerMotionAndBlurFree,
    nativeModalMotionFree,
    overlayCleanup,
    moreHasNoDuplicates,
    retainedStockDialog,
    modalFocusWorks,
    overlayFrames: uniqueFrames,
  };
}
