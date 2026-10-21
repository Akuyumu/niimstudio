<script lang="ts">
  import { get } from "svelte/store";
  import { SoundSettingsItemType } from "@mmote/niimbluelib";
  import AppModal from "$/components/basic/AppModal.svelte";
  import MdIcon from "$/components/basic/MdIcon.svelte";
  import { connectionState, printJobActive, printerClient, printerInfo, printerMeta, rfidInfo } from "$/stores";
  import { nativeRequest } from "$/desktop/bridge";
  import { mediaReadReport } from "$/desktop/media_reads";
  import {
    readPrinterSettings,
    setVerifiedSleep,
    setVerifiedSound,
    offeredSleepModes,
    type PrinterSettingsSnapshot,
  } from "$/desktop/printer_settings";

  let shown = $state(false);
  let busy = $state(false);
  let snapshot = $state<PrinterSettingsSnapshot>({ errors: [] });
  let loadedClient = $state.raw<typeof $printerClient>();
  let reconnect = $state<boolean>();
  let error = $state("");
  let notice = $state("");
  const connected = $derived($connectionState === "connected");
  const sleepModes = $derived(offeredSleepModes($printerInfo?.capabilities?.autoShutdownRange));
  const available = $derived(connected && loadedClient === $printerClient && !busy && !$printJobActive);
  $effect(() => {
    if ($connectionState !== "connected" || (loadedClient && loadedClient !== $printerClient)) {
      loadedClient = undefined;
      snapshot = { errors: [] };
    }
  });

  const refresh = async () => {
    if (busy || $printJobActive) return;
    const client = $printerClient;
    error = notice = "";
    snapshot = { errors: [] };
    loadedClient = undefined;
    busy = true;
    try {
      const history = await nativeRequest<{ enabled: boolean }>("knownDevice");
      reconnect = history.enabled;
      if (get(connectionState) === "connected" && client === get(printerClient)) {
        const result = await readPrinterSettings(client.protocol);
        if (client === get(printerClient) && get(connectionState) === "connected") {
          snapshot = result;
          loadedClient = client;
        }
      }
    } catch (cause) {
      error = cause instanceof Error ? cause.message : String(cause);
    } finally {
      busy = false;
    }
  };
  const open = () => {
    shown = true;
    void refresh();
  };
  const changeSound = async (type: SoundSettingsItemType, event: Event) => {
    const checkbox = event.currentTarget as HTMLInputElement;
    const key = type === SoundSettingsItemType.PowerSound ? "powerSound" : "connectionSound";
    if (!available) {
      checkbox.checked = snapshot[key] === true;
      return;
    }
    const client = $printerClient;
    const value = checkbox.checked;
    busy = true;
    error = notice = "";
    try {
      await setVerifiedSound(client.protocol, type, value);
      if (client !== get(printerClient) || get(connectionState) !== "connected")
        throw new Error("The printer disconnected or changed; refresh its settings.");
      snapshot = { ...snapshot, [key]: value };
      printerInfo.update((info) => ({ ...info, settings: { ...info.settings, [key]: value } }));
      notice = "Printer confirmed the sound setting.";
    } catch (cause) {
      error = cause instanceof Error ? cause.message : String(cause);
    } finally {
      checkbox.checked = snapshot[key] === true;
      busy = false;
    }
  };
  const changeSleep = async (event: Event) => {
    const select = event.currentTarget as HTMLSelectElement;
    if (!available) {
      select.value = String(snapshot.sleepMode ?? "");
      return;
    }
    const client = $printerClient;
    const mode = Number(select.value);
    if (!sleepModes.some((option) => option.value === mode)) {
      error = "This printer does not report support for that sleep mode.";
      select.value = String(snapshot.sleepMode ?? "");
      return;
    }
    busy = true;
    error = notice = "";
    try {
      await setVerifiedSleep(client.protocol, mode);
      if (client !== get(printerClient) || get(connectionState) !== "connected")
        throw new Error("The printer disconnected or changed; refresh its settings.");
      snapshot = { ...snapshot, sleepMode: mode };
      printerInfo.update((info) => ({ ...info, autoShutdownTime: mode }));
      notice = "Printer confirmed the sleep-mode code. Its timing depends on firmware.";
    } catch (cause) {
      error = cause instanceof Error ? cause.message : String(cause);
    } finally {
      select.value = String(snapshot.sleepMode ?? "");
      busy = false;
    }
  };
  const changeReconnect = async (event: Event) => {
    const checkbox = event.currentTarget as HTMLInputElement;
    const enabled = checkbox.checked;
    if (busy) {
      checkbox.checked = reconnect === true;
      return;
    }
    busy = true;
    error = notice = "";
    try {
      await nativeRequest("setReconnectPolicy", { enabled });
      reconnect = enabled;
      notice = "Reconnect preference saved. This does not replay print jobs.";
    } catch (cause) {
      error = cause instanceof Error ? cause.message : String(cause);
    } finally {
      checkbox.checked = reconnect === true;
      busy = false;
    }
  };
</script>

<button
  class="btn btn-sm btn-secondary studio-settings-button"
  title="App and printer settings"
  aria-label="Settings"
  data-action="settings"
  onclick={open}>
  <MdIcon icon="settings" /> <span class="studio-settings-caption">Settings</span>
</button>

{#if shown}
  <AppModal title="Settings" bind:show={shown} dismissible={!busy}>
    {#if error}<p class="alert alert-danger" role="alert">{error}</p>{/if}
    {#if notice}<p class="alert alert-info" role="status">{notice}</p>{/if}
    {#if !connected}<p class="text-secondary">Connect a printer to read or change its sounds and sleep mode.</p>{/if}
    {#if $printJobActive}<p class="text-secondary">Printer settings are locked while a print job is running.</p>{/if}
    {#if busy}<p class="text-secondary" role="status">Reading or saving settings…</p>{/if}
    <section>
      <h2>Printer sounds</h2>
      <label class="studio-setting-row form-switch">
        <span><strong>Power sounds</strong><small>Printer startup and power-off sounds</small></span>
        <input
          class="form-check-input"
          type="checkbox"
          role="switch"
          data-setting="power-sound"
          checked={snapshot.powerSound === true}
          disabled={!available || snapshot.powerSound === undefined}
          onchange={(event) => changeSound(SoundSettingsItemType.PowerSound, event)} />
      </label>
      <label class="studio-setting-row form-switch">
        <span><strong>Connection sounds</strong><small>Bluetooth connection and disconnection sounds</small></span>
        <input
          class="form-check-input"
          type="checkbox"
          role="switch"
          data-setting="connection-sound"
          checked={snapshot.connectionSound === true}
          disabled={!available || snapshot.connectionSound === undefined}
          onchange={(event) => changeSound(SoundSettingsItemType.BluetoothConnectionSound, event)} />
      </label>
      {#if connected && loadedClient && snapshot.powerSound === undefined && snapshot.connectionSound === undefined}<p
          class="text-secondary small">
          This printer did not report sound settings; they are unavailable.
        </p>{/if}
    </section>
    <section>
      <h2>Sleep / auto power-off</h2>
      <label for="studio-sleep-mode" class="form-label">Idle timeout</label>
      <select
        id="studio-sleep-mode"
        class="form-select"
        data-setting="sleep-mode"
        value={snapshot.sleepMode ?? ""}
        disabled={!available || !sleepModes.some((mode) => mode.value === snapshot.sleepMode)}
        onchange={changeSleep}>
        {#if !sleepModes.some((mode) => mode.value === snapshot.sleepMode)}<option value={snapshot.sleepMode ?? ""}
            >{snapshot.sleepMode === undefined ? "Not reported" : `Unmapped mode ${snapshot.sleepMode}`}</option
          >{/if}
        {#each sleepModes as mode (mode.value)}<option value={mode.value}>{mode.label}</option>{/each}
      </select>
      <p class="text-secondary small mt-2">
        The printer exposes mode codes, not minutes. Its fourth mode disables sleep on some firmware and means 60
        minutes on others. NiimStudio cannot promise “never” until this model/firmware is verified. No reset or
        power-off command is sent.
      </p>
    </section>
    <section>
      <h2>Connection</h2>
      <label class="studio-setting-row form-switch">
        <span
          ><strong>Reconnect automatically</strong><small
            >Retry the last successful printer; never replay print jobs</small
          ></span>
        <input
          class="form-check-input"
          type="checkbox"
          role="switch"
          data-setting="reconnect"
          checked={reconnect === true}
          disabled={busy || reconnect === undefined || $printJobActive}
          onchange={changeReconnect} />
      </label>
    </section>
    {#if snapshot.errors.length}<details>
        <summary>Settings not reported by the printer</summary>{#each snapshot.errors as detail (detail)}<p
            class="small text-secondary">
            {detail}
          </p>{/each}
      </details>{/if}
    <details>
      <summary>Printer and roll details</summary>
      <p class="small text-secondary">Read-only metadata, without printer/roll serial numbers or your label artwork.</p>
      <pre>{JSON.stringify(
          {
            model: $printerMeta?.model,
            firmware: $printerInfo?.softwareVersion,
            protocol: $printerInfo?.protocolVersion,
            rollTagPresent: $rfidInfo.labelRfidInfo?.tagPresent,
            rollProductCode: $rfidInfo.labelRfidInfo?.barCode,
            rollTotal: $rfidInfo.labelRfidInfo?.allPaper,
            rollUsed: $rfidInfo.labelRfidInfo?.usedPaper,
            paper: $rfidInfo.paperInfo,
            mediaReadErrors: $mediaReadReport,
          },
          null,
          2,
        )}</pre>
    </details>
    {#snippet footer()}
      <button
        class="btn btn-secondary"
        data-action="settings-refresh"
        disabled={busy || $printJobActive}
        onclick={refresh}>Refresh settings</button>
      <button class="btn btn-primary" data-action="settings-close" disabled={busy} onclick={() => (shown = false)}
        >Close</button>
    {/snippet}
  </AppModal>
{/if}

<style>
  section {
    margin-bottom: 20px;
  }
  h2 {
    font-size: 14px;
    font-weight: 600;
    margin: 0 0 8px;
  }
  .studio-setting-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 10px 0;
  }
  .studio-setting-row span {
    display: flex;
    flex-direction: column;
  }
  .studio-setting-row strong {
    font-size: 13px;
    font-weight: 500;
  }
  .studio-setting-row small {
    color: var(--bs-secondary-color);
    font-size: 11px;
  }
  .studio-setting-row input {
    flex-shrink: 0;
    margin-left: 0;
  }
  details {
    font-size: 12px;
    margin: 12px 0;
  }
  pre {
    font-size: 11px;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    margin: 10px 0;
  }
  @media (max-width: 1000px) {
    .studio-settings-caption {
      display: none;
    }
  }
</style>
