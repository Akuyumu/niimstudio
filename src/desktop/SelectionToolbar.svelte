<script lang="ts">
  import * as fabric from "fabric";
  import type { Snippet } from "svelte";
  import MdIcon from "$/components/basic/MdIcon.svelte";
  import FontFamilyPicker from "$/components/designer-controls/FontFamilyPicker.svelte";
  import { QRCode } from "$/fabric-object/qrcode";
  import { Barcode } from "$/fabric-object/barcode";

  let {
    selectedObject,
    selectedCount,
    editRevision,
    valueUpdated,
    clone,
    remove,
    children,
    editCode,
  }: {
    selectedObject?: fabric.FabricObject;
    selectedCount: number;
    editRevision: number;
    valueUpdated: () => void;
    clone: () => void;
    remove: () => void;
    children: Snippet;
    editCode: () => void;
  } = $props();

  const text = $derived(selectedObject instanceof fabric.IText ? selectedObject : undefined);
  const code = $derived(
    selectedObject instanceof QRCode || selectedObject instanceof Barcode ? selectedObject : undefined,
  );
  const codeText = $derived.by(() => {
    void editRevision;
    return code?.text ?? "";
  });
  const style = $derived.by(() => {
    void editRevision;
    return {
      bold: text?.fontWeight === "bold" || Number(text?.fontWeight) >= 600,
      italic: text?.fontStyle === "italic",
      underline: text?.underline ?? false,
      highlight: text?.backgroundColor === "black",
      align: text?.textAlign,
      size: text?.fontSize ?? 24,
      family: text?.fontFamily ?? "Noto Sans Variable",
    };
  });
  const updateText = (properties: Partial<fabric.ITextProps>) => {
    text?.set(properties);
    valueUpdated();
  };
  const center = (axis: "horizontal" | "vertical") => {
    if (!selectedObject?.canvas) return;
    if (axis === "horizontal") selectedObject.canvas.centerObjectH(selectedObject);
    else selectedObject.canvas.centerObjectV(selectedObject);
    valueUpdated();
  };
</script>

<div class="studio-formatting" role="group" aria-label="Selection formatting">
  {#if code}
    <span class="studio-code-kind"
      ><MdIcon icon={code instanceof QRCode ? "qr_code_2" : "view_week"} />
      {code instanceof QRCode ? "QR code" : "Barcode"}</span>
    <span class="studio-code-value" title={codeText}>{codeText}</span>
    <button class="btn btn-sm btn-secondary" onclick={editCode} data-action="edit-code"
      ><MdIcon icon="edit" /> Edit content</button>
  {:else}
    {#if text}
      <FontFamilyPicker value={style.family} {editRevision} valueUpdated={(fontFamily) => updateText({ fontFamily })} />
    {:else}
      <span class="studio-selection-hint"
        >{selectedCount > 1 ? `${selectedCount} objects selected` : "Select text to format"}</span>
    {/if}
    <input
      class="form-control form-control-sm studio-font-size"
      type="number"
      aria-label="Font size"
      title="Font size"
      value={style.size}
      min="1"
      max="999"
      disabled={!text}
      onchange={(event) =>
        updateText({ fontSize: Math.max(1, Math.min(999, event.currentTarget.valueAsNumber || 24)) })} />
    <span class="studio-toolbar-separator"></span>
    <button
      class:studio-toggle-active={style.bold}
      class="btn btn-sm studio-format-button"
      aria-label="Bold"
      title="Bold"
      aria-pressed={style.bold}
      disabled={!text}
      onclick={() => updateText({ fontWeight: style.bold ? "normal" : "bold" })}><MdIcon icon="format_bold" /></button>
    <button
      class:studio-toggle-active={style.italic}
      class="btn btn-sm studio-format-button"
      aria-label="Italic"
      title="Italic"
      aria-pressed={style.italic}
      disabled={!text}
      onclick={() => updateText({ fontStyle: style.italic ? "normal" : "italic" })}
      ><MdIcon icon="format_italic" /></button>
    <button
      class:studio-toggle-active={style.underline}
      class="btn btn-sm studio-format-button"
      aria-label="Underline"
      title="Underline"
      aria-pressed={style.underline}
      disabled={!text}
      onclick={() => updateText({ underline: !style.underline })}><MdIcon icon="format_underlined" /></button>
    <button
      class:studio-toggle-active={style.highlight}
      class="btn btn-sm studio-format-button"
      aria-label="Highlight text"
      title="Highlight · white text on black (thermal-safe)"
      aria-pressed={style.highlight}
      disabled={!text}
      onclick={() =>
        updateText({
          backgroundColor: style.highlight ? "transparent" : "black",
          fill: style.highlight ? "black" : "white",
        })}><MdIcon icon="format_color_fill" /></button>
    <span class="studio-toolbar-separator"></span>
    {#each ["left", "center", "right"] as const as align (align)}
      <button
        class:studio-toggle-active={style.align === align}
        class="btn btn-sm studio-format-button"
        aria-label={`Align text ${align}`}
        title={`Align text ${align}`}
        aria-pressed={style.align === align}
        disabled={!text}
        onclick={() => updateText({ textAlign: align })}
        ><MdIcon
          icon={align === "left"
            ? "format_align_left"
            : align === "center"
              ? "format_align_center"
              : "format_align_right"} /></button>
    {/each}
  {/if}
  <span class="studio-toolbar-separator"></span>
  <button
    class="btn btn-sm studio-format-button"
    aria-label="Center object horizontally"
    title="Center object horizontally on label"
    disabled={!selectedObject}
    onclick={() => center("horizontal")}><MdIcon icon="horizontal_distribute" /></button>
  <button
    class="btn btn-sm studio-format-button"
    aria-label="Center object vertically"
    title="Center object vertically on label"
    disabled={!selectedObject}
    onclick={() => center("vertical")}><MdIcon icon="vertical_distribute" /></button>
  <div class="dropdown">
    <button
      class="btn btn-sm studio-format-button"
      aria-label="More object properties"
      title="More properties · rotation, spacing, color and position"
      data-bs-toggle="dropdown"
      data-bs-auto-close="outside"
      disabled={!selectedCount}><MdIcon icon="more_horiz" /></button>
    <div class="dropdown-menu studio-advanced-properties p-3">{@render children()}</div>
  </div>
  <span class="studio-toolbar-separator"></span>
  <button
    class="btn btn-sm studio-format-button"
    aria-label="Duplicate selected objects"
    title="Duplicate · Ctrl+D"
    disabled={!selectedCount}
    onclick={clone}><MdIcon icon="content_copy" /></button>
  <button
    class="btn btn-sm studio-format-button"
    aria-label="Delete selected objects"
    title="Delete selected objects"
    disabled={!selectedCount}
    onclick={remove}><MdIcon icon="delete_outline" /></button>
</div>
