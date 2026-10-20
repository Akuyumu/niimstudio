<script lang="ts">
  import AppModal from "$/components/basic/AppModal.svelte";
  import MdIcon from "$/components/basic/MdIcon.svelte";
  import { ExportedLabelTemplateSchema, type ExportedLabelTemplate } from "$/types";
  import { FileUtils } from "$/utils/file_utils";
  import { LocalStoragePersistence } from "$/utils/persistence";
  import type { Snippet } from "svelte";

  let {
    exportLabel,
    loadLabel,
    controls,
  }: {
    exportLabel: () => ExportedLabelTemplate;
    loadLabel: (label: ExportedLabelTemplate) => void;
    controls?: Snippet<[() => void, () => void, string]>;
  } = $props();
  let shown = $state(false);
  let drawer: HTMLDialogElement;
  let templates = $state<ExportedLabelTemplate[]>([]);
  let query = $state("");
  let title = $state("");
  let activeId = $state<string>();
  let replaceExisting = $state(true);
  let pendingDelete = $state<string>();
  let error = $state("");
  let notice = $state("");
  const active = $derived(templates.find((item) => item.id === activeId));
  const filtered = $derived(
    templates.filter((item) => (item.title ?? "Untitled label").toLowerCase().includes(query.toLowerCase())),
  );

  const refresh = () => {
    templates = LocalStoragePersistence.loadLabels();
    error = "";
    pendingDelete = undefined;
  };
  export const openLibrary = () => {
    refresh();
    query = "";
    drawer.showModal();
    drawer.querySelector<HTMLInputElement>('input[type="search"]')?.focus();
  };
  export const openSave = () => {
    refresh();
    title = active?.title ?? "";
    replaceExisting = !!active;
    drawer?.close();
    shown = true;
  };

  const persist = (items: ExportedLabelTemplate[]): boolean => {
    const result = LocalStoragePersistence.saveLabels(items);
    if (result.zodErrors.length || result.otherErrors.length) {
      error = "Could not save the template library. Your existing labels were kept. Export your label as a backup.";
      return false;
    }
    templates = LocalStoragePersistence.loadLabels();
    return true;
  };

  const save = () => {
    const name = title.trim();
    if (!name) {
      error = "Give your template a name.";
      return;
    }
    const label = { ...exportLabel(), title: name };
    const items = [...templates];
    const index = replaceExisting ? items.findIndex((item) => item.id === activeId) : -1;
    if (index < 0) items.push(label);
    else items[index] = label;
    if (!persist(items)) return;
    activeId = label.id;
    notice = `Saved “${name}”`;
    shown = false;
  };

  const load = (label: ExportedLabelTemplate) => {
    activeId = label.id;
    loadLabel(label);
    drawer.close();
    notice = label.title ?? "Template loaded";
  };

  const remove = (label: ExportedLabelTemplate) => {
    if (pendingDelete !== label.id) {
      pendingDelete = label.id;
      return;
    }
    if (persist(templates.filter((item) => item.id !== label.id))) {
      if (activeId === label.id) activeId = undefined;
      pendingDelete = undefined;
    }
  };

  const importLabel = async () => {
    try {
      const contents = await FileUtils.pickAndReadSingleTextFile("json");
      const label = ExportedLabelTemplateSchema.parse(JSON.parse(contents));
      if (persist([...templates, label])) notice = "Template imported";
    } catch (cause) {
      error = `Could not import this template: ${String(cause)}`;
    }
  };

  const exportCurrent = async (format: "json" | "png") => {
    try {
      const label = exportLabel();
      if (format === "json")
        await FileUtils.downloadBase64(
          `${active?.title ?? "label"}.json`,
          "application/json",
          FileUtils.base64obj(label),
        );
      else {
        const { StaticCanvas } = await import("fabric");
        const canvas = new StaticCanvas(undefined, {
          width: label.label.size.width,
          height: label.label.size.height,
          backgroundColor: "white",
        });
        try {
          await canvas.loadFromJSON(label.canvas);
          canvas.renderAll();
          const data = canvas.toDataURL({ format: "png", multiplier: 1 }).split(",")[1];
          await FileUtils.downloadBase64("label.png", "image/png", data);
        } finally {
          await canvas.dispose();
        }
      }
    } catch (cause) {
      error = `Export failed: ${String(cause)}`;
    }
  };
</script>

{#if controls}
  {@render controls(openLibrary, openSave, notice)}
{:else}
  <div class="studio-template-actions">
    <button class="btn btn-sm btn-secondary" onclick={openLibrary} data-action="templates"
      ><MdIcon icon="view_sidebar" /> Templates</button>
    <button
      class="btn btn-sm btn-secondary"
      onclick={openSave}
      title="Save template · Ctrl+S"
      aria-label="Save template"
      data-action="save-template"><MdIcon icon="bookmark_add" /> Save as template</button>
    <span class="studio-save-notice" role="status">{notice}</span>
  </div>
{/if}

<dialog
  bind:this={drawer}
  id="studio-template-drawer"
  class="studio-template-drawer"
  aria-labelledby="studio-template-heading">
  <header class="studio-drawer-header">
    <div>
      <span class="studio-section-label">YOUR LIBRARY</span>
      <h2 id="studio-template-heading">Templates</h2>
    </div>
    <button class="btn studio-format-button" aria-label="Close templates" onclick={() => drawer.close()}
      ><MdIcon icon="close" /></button>
  </header>
  <div class="studio-drawer-body">
    {#if error}<div class="alert alert-danger" role="alert">{error}</div>{/if}
    <input
      class="form-control studio-template-search"
      type="search"
      placeholder="Search templates…"
      aria-label="Search templates"
      bind:value={query} />
    {#if templates.length === 0}
      <div class="studio-library-empty">
        <MdIcon icon="bookmark_border" />
        <h3>A good label is worth keeping.</h3>
        <p>Save a layout once. Come back to it whenever you need it.</p>
        <button class="btn btn-primary" onclick={openSave}>Save this label</button>
      </div>
    {:else if filtered.length === 0}
      <p class="studio-help py-4">No templates match “{query}”.</p>
    {:else}
      <div class="studio-template-grid">
        {#each filtered as label (label.id)}
          <article class="studio-template-card">
            <button
              class="studio-template-open"
              onclick={() => load(label)}
              aria-label={`Open ${label.title ?? "Untitled label"}`}>
              <div class="studio-template-thumb">
                {#if label.thumbnailBase64}<img src={label.thumbnailBase64} alt="" />{:else}<MdIcon icon="label" />{/if}
              </div>
              <strong>{label.title ?? "Untitled label"}</strong>
              <span
                >{label.label.size.width} × {label.label.size.height} px · {label.canvas.objects.length} objects</span>
            </button>
            <button
              class="btn btn-sm studio-template-delete"
              title={pendingDelete === label.id ? "Confirm deletion" : "Delete template"}
              aria-label={`Delete ${label.title ?? "template"}`}
              onclick={() => remove(label)}>
              {#if pendingDelete === label.id}Delete?{:else}<MdIcon icon="delete_outline" />{/if}
            </button>
          </article>
        {/each}
      </div>
    {/if}
  </div>
  <footer class="studio-library-footer">
    <button class="btn btn-sm btn-secondary" onclick={importLabel}><MdIcon icon="file_upload" /> Import</button>
    <div class="dropdown">
      <button class="btn btn-sm btn-secondary dropdown-toggle" data-bs-toggle="dropdown">Export</button>
      <div class="dropdown-menu">
        <button class="dropdown-item" onclick={() => exportCurrent("json")}>Editable JSON</button><button
          class="dropdown-item"
          onclick={() => exportCurrent("png")}>PNG image</button>
      </div>
    </div>
    <button class="btn btn-sm btn-primary ms-auto" onclick={openSave}><MdIcon icon="add" /> Save label</button>
  </footer>
</dialog>

{#if shown}
  <AppModal title="Save template" bind:show={shown}>
    {#if error}<div class="alert alert-danger" role="alert">{error}</div>{/if}
    <form
      id="studio-save-template"
      onsubmit={(event) => {
        event.preventDefault();
        save();
      }}>
      <label class="form-label" for="studio-template-name">Template name</label>
      <input
        id="studio-template-name"
        class="form-control"
        placeholder="e.g. Pantry jars"
        bind:value={title}
        maxlength="120"
        data-modal-autofocus
        required />
      <p class="studio-help mt-2">
        A reusable copy of this label, including its layout and batch data. Stored only on this device.
      </p>
      {#if active}
        <label class="studio-replace-option"
          ><input type="checkbox" class="form-check-input" bind:checked={replaceExisting} /> Update “{active.title ??
            "Untitled label"}” instead of saving a new copy</label>
      {/if}
    </form>
    {#snippet footer()}
      <button class="btn btn-secondary" onclick={() => (shown = false)}>Cancel</button>
      <button class="btn btn-primary" type="submit" form="studio-save-template"
        >{replaceExisting && active ? "Save changes" : "Save template"}</button>
    {/snippet}
  </AppModal>
{/if}
