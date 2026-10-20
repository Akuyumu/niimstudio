/** Isolated real-WebKit benchmark. Never loaded in the ordinary workspace. */
import { tick } from "svelte";
import type { ExportedLabelTemplate } from "$/types";
import { LocalStoragePersistence } from "$/utils/persistence";

const frames = () =>
  new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve())));
const summary = (values: number[]) => {
  const sorted = [...values].sort((a, b) => a - b);
  return {
    medianMs: +sorted[Math.floor(sorted.length / 2)].toFixed(2),
    p95Ms: +sorted[Math.floor(sorted.length * 0.95)].toFixed(2),
  };
};
const measure = async (action: () => void, ready: () => boolean) => {
  const start = performance.now();
  action();
  await tick();
  const limit = start + 5000;
  while (!ready()) {
    if (performance.now() > limit) throw new Error("Benchmark control did not become ready");
    await new Promise((resolve) => setTimeout(resolve, 1));
    await tick();
  }
  const readyMs = performance.now() - start;
  await frames(); // A paint boundary proxy, not a monitor-presentation measurement.
  return { readyMs, framesMs: performance.now() - start };
};
const button = (selector: string) => document.querySelector<HTMLButtonElement>(selector)!;

export async function benchmarkOverlays(template: ExportedLabelTemplate) {
  if (!window.__NIIMSTUDIO_SMOKE__ || !window.__NIIMSTUDIO_BENCHMARK__)
    throw new Error("Benchmark requires the isolated smoke profile");
  const results: Record<string, unknown> = {};
  for (const count of [0, 128]) {
    const object = JSON.parse(JSON.stringify(template.canvas.objects[0]));
    const thumbnail = document.createElement("canvas").toDataURL();
    const labels = Array.from({ length: count }, (_, index) => ({
      ...template,
      id: undefined,
      title: `Synthetic label ${index}`,
      timestamp: 1000 + index,
      thumbnailBase64: thumbnail,
      canvas: { ...template.canvas, objects: Array.from({ length: 12 }, () => ({ ...object })) },
    }));
    const saved = LocalStoragePersistence.saveLabels(labels);
    if (saved.zodErrors.length || saved.otherErrors.length) throw new Error("Benchmark fixture could not be saved");
    const samples: Record<string, { readyMs: number; framesMs: number }[]> = {
      sidebarOpen: [],
      sidebarClose: [],
      stockOpen: [],
      stockClose: [],
    };
    let cold: unknown;
    for (let iteration = 0; iteration < 18; iteration++) {
      const openLibrary = await measure(
        () => button('[data-action="templates"]').click(),
        () => !!document.querySelector(".studio-template-drawer[open]"),
      );
      const closeLibrary = await measure(
        () => button('[aria-label="Close templates"]').click(),
        () => !document.querySelector(".studio-template-drawer[open]"),
      );
      const openStock = await measure(
        () => button('[data-action="label-stock"]').click(),
        () => !!document.querySelector('.modal.show[data-modal-ready="true"]'),
      );
      const closeStock = await measure(
        () => button(".modal.show .btn-close").click(),
        () => !document.querySelector(".modal.show"),
      );
      if (iteration === 0)
        cold = { sidebarOpen: openLibrary, sidebarClose: closeLibrary, stockOpen: openStock, stockClose: closeStock };
      if (iteration >= 3) {
        samples.sidebarOpen.push(openLibrary);
        samples.sidebarClose.push(closeLibrary);
        samples.stockOpen.push(openStock);
        samples.stockClose.push(closeStock);
      }
    }
    results[`templates${count}`] = Object.fromEntries(
      Object.entries(samples).map(([name, data]) => [
        name,
        {
          ready: summary(data.map((sample) => sample.readyMs)),
          paintBoundary: summary(data.map((sample) => sample.framesMs)),
        },
      ]),
    );
    results[`firstOpen${count}`] = cold;
  }
  return {
    ok: true,
    benchmark: results,
    samples: 15,
    notes:
      "Ready includes JS, DOM and focus work. Paint boundary is two RAF callbacks; not physical presentation latency. Synthetic temporary data only.",
  };
}
