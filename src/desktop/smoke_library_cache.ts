/** Cache correctness is a prerequisite for avoiding storage work on panel opens. */
import { tick } from "svelte";
import type { ExportedLabelTemplate } from "$/types";
import { LocalStoragePersistence as storage } from "$/utils/persistence";

export async function runLibraryCacheSmoke(template: ExportedLabelTemplate) {
  const originalLoad = storage.loadLabels;
  let reads = 0;
  storage.loadLabels = function () {
    reads++;
    return originalLoad.call(this);
  };
  const open = async () => {
    document.querySelector<HTMLButtonElement>('[data-action="templates"]')!.click();
    await tick();
    return document.querySelector<HTMLDialogElement>(".studio-template-drawer")!;
  };
  try {
    storage.saveLabels([{ ...template, title: "Cache original" }]);
    let drawer = await open();
    drawer.close();
    const firstReads = reads;
    drawer = await open();
    const libraryReusesValidatedCache = reads === firstReads;
    drawer.close();
    const revision = storage.labelsRevision;
    const rejected = storage.saveLabels([
      { ...template, label: { ...template.label, size: { width: -1, height: 1 } } },
    ]);
    const rejectedSaveKeepsRevision = rejected.zodErrors.length === 1 && storage.labelsRevision === revision;
    storage.saveLabels([{ ...template, title: "Cache saved" }]);
    drawer = await open();
    const libraryCacheSeesSaves = drawer.textContent!.includes("Cache saved") && reads > firstReads;
    drawer.close();
    const label = originalLoad.call(storage)[0];
    storage.saveObject(label.id!, { ...label, title: "Cache direct write" });
    drawer = await open();
    const libraryCacheSeesDirectWrites = drawer.textContent!.includes("Cache direct write");
    drawer.close();
    localStorage.setItem(label.id!, JSON.stringify({ ...label, title: "Cache another window" }));
    window.dispatchEvent(new StorageEvent("storage", { key: label.id, storageArea: localStorage }));
    drawer = await open();
    const libraryCacheSeesOtherWindows = drawer.textContent!.includes("Cache another window");
    drawer.close();
    return {
      libraryReusesValidatedCache,
      rejectedSaveKeepsRevision,
      libraryCacheSeesSaves,
      libraryCacheSeesDirectWrites,
      libraryCacheSeesOtherWindows,
    };
  } finally {
    storage.loadLabels = originalLoad;
    document.querySelector<HTMLDialogElement>(".studio-template-drawer")?.close();
    storage.saveLabels([template]);
  }
}
