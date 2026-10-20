/** Synthetic screenshot content, used only in an isolated smoke-test profile. */
import * as fabric from "fabric";
import type { CustomCanvas } from "$/fabric-object/custom_canvas";
import { LabelDesignerObjectHelper } from "$/utils/label_designer_object_helper";

export function loadSmokeDemo(canvas: CustomCanvas) {
  canvas.clear();
  const title = LabelDesignerObjectHelper.addText(canvas, "COFFEE BEANS", {
    fontSize: 24,
    fontWeight: "bold",
    textAlign: "left",
    width: 200,
  });
  title.set({ originX: "left", originY: "top", left: 20, top: 17 });
  canvas.add(
    new fabric.Rect({
      left: 20,
      top: 51,
      width: 200,
      height: 1,
      fill: "black",
      strokeWidth: 0,
      originX: "left",
      originY: "top",
    }),
  );
  const note = LabelDesignerObjectHelper.addText(canvas, "Whole bean  ·  Store airtight", {
    fontSize: 10,
    textAlign: "left",
    width: 200,
  });
  note.set({ originX: "left", originY: "top", left: 20, top: 63 });
  canvas.discardActiveObject();
  canvas.renderAll();
}
