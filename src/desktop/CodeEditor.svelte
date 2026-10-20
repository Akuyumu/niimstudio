<script lang="ts">
  import { onMount } from "svelte";
  import QRCodeFactory from "qrcode-generator";
  import AppModal from "$/components/basic/AppModal.svelte";
  import { code128b, ean13 } from "$/utils/barcode";
  import { stringToBytes } from "$/utils/qrcode";
  import type { QRCode, ErrorCorrectionLevel } from "$/fabric-object/qrcode";
  import type { Barcode, BarcodeCoding } from "$/fabric-object/barcode";

  QRCodeFactory.stringToBytes = stringToBytes;
  export type CodeContent = {
    kind: "qrcode" | "barcode";
    text: string;
    encoding: BarcodeCoding;
    ecl: ErrorCorrectionLevel;
    printText: boolean;
    modules: number;
  };
  let {
    kind,
    existing,
    availableWidth,
    availableHeight,
    onSave,
    onClose,
  }: {
    kind: "qrcode" | "barcode";
    existing?: QRCode | Barcode;
    availableWidth: number;
    availableHeight: number;
    onSave: (content: CodeContent) => void;
    onClose: () => void;
  } = $props();
  let shown = $state(true);
  let content = $state("");
  let encoding = $state<BarcodeCoding>("CODE128B");
  let ecl = $state<ErrorCorrectionLevel>("M");
  let printText = $state(true);
  let preview: HTMLCanvasElement;
  let modal: AppModal;

  onMount(() => {
    content = existing?.text ?? "";
    if (existing && "encoding" in existing) {
      encoding = existing.encoding;
      printText = existing.printText;
    }
    if (existing && "ecl" in existing) ecl = existing.ecl;
  });

  const validation = $derived.by(() => {
    if (!content.trim()) return { error: "Enter the content you want to encode.", qr: null, bars: "", normalized: "" };
    try {
      if (kind === "qrcode") {
        const qr = QRCodeFactory(0, ecl);
        qr.addData(content, "Byte");
        qr.make();
        if (qr.getModuleCount() + 8 > Math.min(availableWidth, availableHeight)) {
          throw new Error(
            "This QR code is too dense for the current label. Shorten its content or increase the label size.",
          );
        }
        return { error: "", qr, bars: "", normalized: content };
      }
      if (encoding === "EAN13" && !/^\d{12,13}$/.test(content))
        throw new Error("EAN-13 needs 12 digits, or 13 digits with a valid check digit.");
      if (encoding === "CODE128B" && !/^[\x20-\x7e]+$/.test(content))
        throw new Error("Code 128 supports printable ASCII text. Use a QR code for Unicode or multiline content.");
      const encoded = encoding === "EAN13" ? ean13(content) : { text: content, bandcode: code128b(content) };
      if (!existing && encoded.bandcode.length + 20 > availableWidth)
        throw new Error(
          "This barcode is too wide for this label. Shorten the value, enlarge the label, or use a QR code for a long link.",
        );
      return { error: "", qr: null, bars: encoded.bandcode, normalized: encoded.text };
    } catch (error) {
      return { error: error instanceof Error ? error.message : String(error), qr: null, bars: "", normalized: "" };
    }
  });

  $effect(() => {
    const { qr, bars, normalized, error } = validation;
    if (!preview) return;
    const context = preview.getContext("2d")!;
    preview.width = kind === "qrcode" ? 264 : Math.max(360, bars.length * 2 + 40);
    preview.height = kind === "qrcode" ? 264 : 145;
    context.fillStyle = "white";
    context.fillRect(0, 0, preview.width, preview.height);
    if (error) return;
    context.fillStyle = "black";
    if (qr) {
      const scale = Math.floor(264 / (qr.getModuleCount() + 8));
      const offset = Math.floor((264 - qr.getModuleCount() * scale) / 2);
      context.translate(offset, offset);
      qr.renderTo2dContext(context, scale);
    } else {
      for (let x = 0; x < bars.length; x++)
        if (bars[x] === "1") context.fillRect(20 + x * 2, 15, 2, printText ? 88 : 112);
      if (printText) {
        context.font = "15px sans-serif";
        context.textAlign = "center";
        context.fillText(normalized, preview.width / 2, 129);
      }
    }
  });

  const submit = () => {
    if (validation.error) return;
    onSave({
      kind,
      text: validation.normalized,
      encoding,
      ecl,
      printText,
      modules: validation.qr?.getModuleCount() ?? 0,
    });
    modal.hide();
  };
</script>

<AppModal
  title={`${existing ? "Edit" : "Add"} ${kind === "qrcode" ? "QR code" : "barcode"}`}
  bind:show={shown}
  bind:this={modal}
  {onClose}>
  <form
    id="studio-code-form"
    onsubmit={(event) => {
      event.preventDefault();
      submit();
    }}>
    <label class="form-label" for="studio-code-content"
      >{kind === "qrcode"
        ? "Link or text"
        : encoding === "EAN13"
          ? "Product number"
          : "Text, number, or short link"}</label>
    <textarea
      id="studio-code-content"
      class="form-control studio-code-content"
      bind:value={content}
      placeholder={kind === "qrcode" ? "https://example.com" : "e.g. ITEM-001"}
      maxlength="2000"
      rows="3"
      data-modal-autofocus
      required></textarea>
    <p class="studio-help mt-2">
      {kind === "qrcode"
        ? "Paste a full link, or enter text. Nothing is opened or sent online."
        : "Code 128 is for general text; EAN-13 is for product numbers."}
    </p>
    <div class="studio-code-options">
      {#if kind === "barcode"}
        <label
          >Format<select class="form-select form-select-sm" bind:value={encoding}
            ><option value="CODE128B">Code 128</option><option value="EAN13">EAN-13</option></select
          ></label>
        <label class="studio-code-caption"
          ><input class="form-check-input" type="checkbox" bind:checked={printText} /> Show text below code</label>
      {:else}
        <label
          >Error correction<select class="form-select form-select-sm" bind:value={ecl}
            ><option value="L">Low · 7%</option><option value="M">Medium · 15%</option><option value="Q"
              >Quartile · 25%</option
            ><option value="H">High · 30%</option></select
          ></label>
      {/if}
    </div>
    {#if content && validation.error}<p class="studio-code-error" role="alert">{validation.error}</p>{/if}
    <div class="studio-code-preview" class:studio-code-preview-empty={!!validation.error}>
      <canvas bind:this={preview} aria-label="Code preview"></canvas>
      {#if !content}<span>Your code will appear here</span>{/if}
    </div>
  </form>
  {#snippet footer()}
    <button class="btn btn-secondary" onclick={() => modal.hide()}>Cancel</button>
    <button class="btn btn-primary" type="submit" form="studio-code-form" disabled={!!validation.error}
      >{existing ? "Apply changes" : kind === "qrcode" ? "Insert QR code" : "Insert barcode"}</button>
  {/snippet}
</AppModal>
