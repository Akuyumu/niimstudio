<script lang="ts">
  import { untrack } from "svelte";
  import { connectionState, printerInfo, printerMeta, rfidInfo, printerClient, confirmedStock } from "$/stores";
  import type { LabelProps } from "$/types";
  import AppModal from "$/components/basic/AppModal.svelte";
  import { isNative } from "$/desktop/bridge";
  import MdIcon from "$/components/basic/MdIcon.svelte";
  import { mediaReadReport } from "$/desktop/media_reads";
  import { rollStockKey, savedRollStocks } from "$/desktop/roll_stock";
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
  let rememberRoll = $state(false);
  let error = $state("");
  let profile = $derived($connectionState === "connected" ? printerProfile($printerMeta, $printerInfo) : undefined);
  let detected = $derived($connectionState === "connected" ? detectedStock($rfidInfo.paperInfo, profile) : undefined);
  let rollKey = $derived(rollStockKey($printerMeta?.model, $rfidInfo.labelRfidInfo));
  let savedPreset = $derived(rollKey ? stockSizes.find((stock) => stock.id === $savedRollStocks[rollKey]) : undefined);
  // A valid but conflicting/invalid geometry report must not be bypassed by a
  // remembered preset; only use the user mapping when no parsed size is available.
  let remembered = $derived(
    $connectionState === "connected" && profile && savedPreset && !$rfidInfo.paperInfo?.valid
      ? stockFromSize(savedPreset, profile)
      : undefined,
  );
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
  let proposed = $derived(detected ?? remembered ?? (profile && chosen ? stockFromSize(chosen, profile) : undefined));
  const description = (stock: DetectedStock) => `${stock.widthMm} × ${stock.heightMm} mm · ${stock.dpi} DPI`;
  const apply = (stock: DetectedStock, id = "") => {
    error = "";
    if (rememberRoll && rollKey && id && $connectionState === "connected") {
      try {
        savedRollStocks.update((saved) => ({ ...saved, [rollKey!]: id as (typeof stockSizes)[number]["id"] }));
      } catch {
        error = "Could not remember this roll size. Untick Remember to use this size without saving a mapping.";
        return;
      }
    }
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
    error = "";
    try {
      await $printerClient.fetchRfidInfo();
    } catch (cause) {
      error = cause instanceof Error ? cause.message : String(cause);
    } finally {
      refreshing = false;
    }
  };
  const forgetRoll = () => {
    if (!rollKey || blocked) return;
    try {
      savedRollStocks.update((saved) => {
        const next = { ...saved };
        delete next[rollKey!];
        return next;
      });
      selection = "";
      rememberRoll = false;
      error = "";
    } catch {
      error = "Could not change the saved roll size. Your current mapping was kept.";
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

{#snippet rollReadStatus()}
  {#if $connectionState === "connected"}
    {#if $rfidInfo.labelRfidInfo?.tagPresent}
      <p class="small" data-testid="roll-read-status">
        RFID roll tag detected{$rfidInfo.labelRfidInfo.barCode ? ` · Product ${$rfidInfo.labelRfidInfo.barCode}` : ""}.
        A roll identity does not necessarily include width and height.
      </p>
    {:else if $mediaReadReport.label}
      <p class="small text-secondary" data-testid="roll-read-status">Roll-tag read failed: {$mediaReadReport.label}</p>
    {:else if $rfidInfo.labelRfidInfo}
      <p class="small text-secondary" data-testid="roll-read-status">
        The printer reports no readable RFID tag. Check the lid and roll seating; untagged stock needs a size choice.
      </p>
    {/if}
    {#if $mediaReadReport.paper}<p class="small text-secondary">Label-size read failed: {$mediaReadReport.paper}</p>
    {:else if $rfidInfo.paperInfo && !$rfidInfo.paperInfo.valid}<p class="small text-secondary">
        The printer replied, but not with the extended label-dimensions format.
      </p>{/if}
    {#if rollKey && !detected && !remembered}<label class="small d-flex gap-2 mb-3"
        ><input type="checkbox" class="form-check-input" data-setting="remember-roll" bind:checked={rememberRoll} /> Remember
        my chosen size for this roll product on this printer</label
      >{/if}
  {/if}
{/snippet}

<button
  class="btn btn-sm btn-secondary studio-stock-button"
  data-action="label-stock"
  disabled={blocked}
  onclick={() => {
    rememberRoll = false;
    error = "";
    shown = true;
  }}
  title={detected
    ? "Stock detected by the printer. Size, DPI and feed direction are automatic."
    : "Choose the stock loaded in your printer"}>
  <MdIcon icon="label" />
  {#if detected}{detected.widthMm} × {detected.heightMm} mm <span class="studio-stock-auto">Auto</span>
  {:else if remembered}{remembered.widthMm} × {remembered.heightMm} mm <span class="studio-stock-auto">Saved roll</span>
  {:else}Label stock{/if}
</button>

{#if shown || retained}
  <AppModal
    title={detected
      ? "Detected label stock"
      : remembered
        ? "Saved roll size"
        : proposed
          ? "Use this printer's resolution?"
          : "Choose your label stock"}
    bind:show={shown}
    bind:this={modal}>
    {#if error}<p class="alert alert-danger" role="alert">{error}</p>{/if}
    {#if proposed}
      <p class="studio-stock-summary" data-testid="detected-stock">{description(proposed)}</p>
      <p>
        {detected
          ? "The printer reports this stock."
          : remembered
            ? "Using the size you previously confirmed for this roll's product code, not a measured size."
            : "Using the stock size you chose."} Resolution and feed direction are set automatically.
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
      {@render rollReadStatus()}
      {#if remembered}<button
          class="btn btn-sm btn-secondary"
          data-action="change-saved-roll"
          disabled={blocked}
          onclick={forgetRoll}>Change saved roll size</button
        >{/if}
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
      {@render rollReadStatus()}
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
          onclick={() => apply(proposed!, detected ? "" : (savedPreset?.id ?? selection))}
          >Use {detected ? "detected stock" : "printer settings"}</button
        >{/if}
    {/snippet}
  </AppModal>
{/if}
