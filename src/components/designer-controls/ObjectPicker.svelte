<script lang="ts">
  import { type LabelProps, type OjectType } from "$/types";
  import { tr } from "$/utils/i18n";
  import MdIcon from "$/components/basic/MdIcon.svelte";
  import ZplImportButton from "$/components/designer-controls/ZplImportButton.svelte";
  import PdfImportButton from "$/components/designer-controls/PdfImportButton.svelte";

  interface Props {
    onSubmit: (i: OjectType) => void;
    labelProps: LabelProps;
    zplImageReady: (img: Blob) => void;
    pdfImageReady: (img: HTMLCanvasElement) => void;
    label?: string;
    advancedOnly?: boolean;
  }

  let { onSubmit, labelProps, zplImageReady, pdfImageReady, label, advancedOnly = false }: Props = $props();
  const objectTools = [
    { type: "text", icon: "title", title: "editor.objectpicker.text" },
    { type: "line", icon: "remove", title: "editor.objectpicker.line" },
    { type: "rectangle", icon: "crop_square", title: "editor.objectpicker.rectangle" },
    { type: "circle", icon: "radio_button_unchecked", title: "editor.objectpicker.circle" },
    { type: "image", icon: "image", title: "editor.objectpicker.image" },
    { type: "qrcode", icon: "qr_code_2", title: "editor.objectpicker.qrcode" },
    { type: "aruco", icon: "grid_on", title: "editor.objectpicker.aruco" },
    { type: "barcode", icon: "view_week", title: "editor.objectpicker.barcode" },
  ] as const;
  const tools = $derived(advancedOnly ? objectTools.filter((tool) => tool.type === "aruco") : objectTools);
</script>

<div class="dropdown">
  <button
    class="btn btn-sm btn-secondary"
    data-bs-toggle="dropdown"
    data-bs-auto-close="outside"
    data-action={advancedOnly ? "more-tools" : undefined}>
    <MdIcon icon={label ? "more_horiz" : "format_shapes"} />
    {#if label}<span>{label}</span>{:else}<MdIcon icon="add" />{/if}
  </button>

  <div class="dropdown-menu" data-testid={advancedOnly ? "more-tools-menu" : undefined}>
    <h6 class="dropdown-header">{advancedOnly ? "More tools" : $tr("editor.objectpicker.title")}</h6>
    <div class="p-3">
      {#each tools as tool (tool.type)}
        <button class="btn me-1" data-object-type={tool.type} onclick={() => onSubmit(tool.type)}>
          <MdIcon icon={tool.icon} />
          {$tr(tool.title)}
        </button>
      {/each}

      <ZplImportButton {labelProps} onImageReady={zplImageReady} />

      <PdfImportButton {labelProps} onImageReady={pdfImageReady} />
    </div>
  </div>
</div>

<style>
  .dropdown-menu {
    width: 100vw;
    max-width: 450px;
  }
</style>
