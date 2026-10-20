<script lang="ts">
  import { untrack } from "svelte";
  import { connectionState, printerInfo, printerMeta, rfidInfo, printerClient, confirmedStock } from "$/stores";
  import type { LabelProps } from "$/types";
  import AppModal from "$/components/basic/AppModal.svelte";
  import { isNative } from "$/desktop/bridge";
  import MdIcon from "$/components/basic/MdIcon.svelte";
  import {
    detectedStock,
    offlineProfile,
    printerProfile,
    stockFromSize,
    stockMatches,
    stockSizes,
    type DetectedStock,
  } from "./media";

  let {
    current,
    hasArtwork,
    onApply,
    blocked = false,
  }: {
    current: LabelProps;
    hasArtwork: () => boolean;
    onApply: (stock: DetectedStock) => void;
    blocked?: boolean;
  } = $props();
  let shown = $state(false);
  let retained = $state(false);
  let modal = $state<AppModal>();
  let handled = "";
  let applied = $state("");
  let selection = $state("");
  let selectedSize = $state("");
  let selectedRoll = $state("");
  let refreshing = $state(false);
  let profile = $derived($connectionState === "connected" ? printerProfile($printerMeta, $printerInfo) : undefined);
  let detected = $derived($connectionState === "connected" ? detectedStock($rfidInfo.paperInfo, profile) : undefined);
  let rollIdentity = $derived(
    JSON.stringify([
      $printerMeta?.model,
      $rfidInfo.labelRfidInfo?.tagPresent,
      $rfidInfo.labelRfidInfo?.uuid,
      $rfidInfo.labelRfidInfo?.serialNumber,
    ]),
  );
  let candidates = $derived(
    stockSizes.map((stock) => ({
      ...stock,
      projected:
        $connectionState === "connected" && !profile ? undefined : stockFromSize(stock, profile ?? offlineProfile),
    })),
  );
  let chosen = $derived(
    selection && selectedSize === JSON.stringify(current.size) && (!selectedRoll || selectedRoll === rollIdentity)
      ? stockSizes.find((stock) => stock.id === selection)
      : undefined,
  );
  let proposed = $derived(detected ?? (profile && chosen ? stockFromSize(chosen, profile) : undefined));
  const description = (stock: DetectedStock) => `${stock.widthMm} × ${stock.heightMm} mm · ${stock.dpi} DPI`;
  const apply = (stock: DetectedStock, id = "") => {
    // RFID tells us dimensions, not the die-cut shape. Keep an explicit shape.
    const configured = { ...stock, shape: id || !detected ? stock.shape : (current.shape ?? "rounded_rect") };
    onApply(configured);
    confirmedStock.set(configured);
    applied = description(stock);
    selection = id;
    selectedSize = JSON.stringify(stock.size);
    selectedRoll = $connectionState === "connected" ? rollIdentity : "";
    if (shown) modal?.hide();
  };
  const refresh = async () => {
    if (blocked || refreshing || !$printerClient) return;
    refreshing = true;
    try {
      await $printerClient.fetchRfidInfo();
    } finally {
      refreshing = false;
    }
  };
  $effect(() => {
    if (shown && isNative) retained = true;
  });
  $effect(() => {
    const state = $connectionState;
    const reported = proposed;
    const busy = blocked;
    const model = $printerMeta?.model;
    if (state !== "connected") {
      handled = "";
      return;
    }
    if (busy) return;
    const key = JSON.stringify([model, reported, rollIdentity]);
    if (handled === key) return;
    handled = key;
    untrack(() => {
      if (!reported) {
        confirmedStock.set(undefined);
        shown = true;
      } else if (stockMatches(current, reported)) {
        applied = description(reported);
        confirmedStock.set({ ...reported, shape: current.shape ?? "rounded_rect" });
      } else if (!hasArtwork()) apply(reported, detected ? "" : (chosen?.id ?? ""));
      else shown = true;
    });
  });
</script>

<button
  class="btn btn-sm btn-secondary studio-stock-button"
  data-action="label-stock"
  disabled={blocked}
  onclick={() => (shown = true)}
  title={detected
    ? "Stock detected by the printer. Size, DPI and feed direction are automatic."
    : "Choose the stock loaded in your printer"}>
  <MdIcon icon="label" />
  {#if detected}{detected.widthMm} × {detected.heightMm} mm <span class="studio-stock-auto">Auto</span>
  {:else}Label stock{/if}
</button>

{#if shown || retained}
  <AppModal
    title={detected ? "Detected label stock" : proposed ? "Use this printer's resolution?" : "Choose your label stock"}
    bind:show={shown}
    bind:this={modal}>
    {#if proposed}
      <p class="studio-stock-summary" data-testid="detected-stock">{description(proposed)}</p>
      <p>
        {detected ? "The printer reports this stock." : "Using the stock size you chose."} Resolution and feed direction are
        set automatically.
      </p>
      <p class="text-secondary">
        {stockMatches(current, proposed)
          ? "Your design already matches this size."
          : "Use this size for your canvas. Existing artwork stays in place; Undo restores the previous size."}
      </p>
      <p class="text-secondary small">
        Rounded corners are a stock preview, not a measured corner radius. The printer does not report the exact cut
        shape.
      </p>
    {:else}
      <p>
        {$connectionState === "connected"
          ? "This printer or roll does not report a usable label size. Choose the size printed on the roll packaging."
          : "Connect a printer for automatic stock detection, or choose a size to design offline."}
      </p>
      <p class="text-secondary small">
        {profile
          ? `${profile.dpi} DPI · Feed direction set by the printer`
          : $connectionState === "connected"
            ? "The printer model could not be identified. Reconnect before choosing stock."
            : "Offline preview uses 203 DPI. Check the stock after connecting."}
      </p>
      <div class="studio-stock-grid">
        {#each candidates as stock (stock.id)}
          <button
            class="btn btn-secondary"
            data-stock-id={stock.id}
            disabled={!stock.projected || blocked}
            onclick={() => apply(stock.projected!, stock.id)}>
            {stock.widthMm} × {stock.heightMm} mm
            <span
              >{stock.shape === "circle"
                ? "Round"
                : stock.shape === "rect"
                  ? "Square corners"
                  : "Rounded corners"}</span>
          </button>
        {/each}
      </div>
      <p class="text-secondary small mt-3">
        Sizes too wide for this printer are unavailable. If your stock is not listed, do not choose a different size and
        print.
      </p>
      {#if applied}<p class="small">Selected: {applied}{selection ? ` · ${selection}` : ""}</p>{/if}
    {/if}
    {#snippet footer()}
      {#if $connectionState === "connected"}<button
          class="btn btn-secondary"
          disabled={blocked || refreshing}
          onclick={refresh}>Check roll again</button
        >{/if}
      <button class="btn btn-secondary" data-action="keep-stock-design" onclick={() => modal?.hide()}
        >{proposed && !stockMatches(current, proposed) ? "Keep design" : "Close"}</button>
      {#if proposed}<button
          class="btn btn-primary"
          data-action="use-detected-stock"
          disabled={blocked}
          onclick={() => apply(proposed!, detected ? "" : selection)}
          >Use {detected ? "detected stock" : "printer settings"}</button
        >{/if}
    {/snippet}
  </AppModal>
{/if}
