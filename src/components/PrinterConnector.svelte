<script lang="ts">
  import {
    LabelType,
    NiimbotCapacitorBleClient,
    SoundSettingsItemType,
    Utils,
    type AvailableTransports,
  } from "@mmote/niimbluelib";
  import {
    printerClient,
    connectedPrinterName,
    connectionState,
    initClient,
    heartbeatData,
    printerInfo,
    printerMeta,
    heartbeatFails,
    automation,
    rfidInfo,
    printJobActive,
  } from "$/stores";
  import type { ConnectionType } from "$/types";
  import { tr, type TranslationKey } from "$/utils/i18n";
  import MdIcon from "$/components/basic/MdIcon.svelte";
  import { Toasts } from "$/utils/toasts";
  import { onMount, onDestroy } from "svelte";
  import { get } from "svelte/store";
  import { LocalStoragePersistence } from "$/utils/persistence";
  import type { MaterialIcon } from "material-icons";
  import FirmwareUpdater from "$/components/basic/FirmwareUpdater.svelte";
  import PrinterVerboseInfo from "$/components/PrinterVerboseInfo.svelte";
  import { isNative, nativeRequest, onNativeEvent } from "$/desktop/bridge";
  import { NativeNiimbotClient } from "$/desktop/client";
  import { ReconnectController } from "$/desktop/reconnect";
  import { isUserCancelled } from "$/desktop/cancellation";
  import { connectionFeedback } from "$/desktop/connection_feedback";

  let connectionType = $state<ConnectionType>("bluetooth");
  let featureSupport = $state<AvailableTransports>({ webBluetooth: false, webSerial: false, capacitorBle: false });
  let verboseInfoShow = $state<boolean>(false);
  let reconnectStatus = $state("");
  let reconnect: ReconnectController | undefined;
  let unlisten: (() => void) | undefined;
  let autoAllowed = true;
  let hasRememberedDevice = false;
  let failure = $state<ReturnType<typeof connectionFeedback>>();
  let connectionAttempt = 0;

  const percentage = (cur?: number, total?: number) => {
    if (cur === undefined || total === undefined) {
      return 0;
    }
    const usage = Math.floor((cur / total) * 100);
    return Math.min(Math.max(usage, 0), 100);
  };

  const onConnectClicked = async (automatic = false) => {
    const attempt = ++connectionAttempt;
    if (!automatic) {
      reconnect?.pause();
      failure = undefined;
    }
    initClient(connectionType);
    connectionState.set("connecting");

    try {
      if ($printerClient instanceof NativeNiimbotClient) {
        await $printerClient.connect({ automatic });
        if (attempt !== connectionAttempt) return;
        failure = undefined;
        const history = await nativeRequest<{ enabled: boolean; device: unknown }>("knownDevice");
        hasRememberedDevice = !!history.device;
        autoAllowed = history.enabled;
        if (!automatic && autoAllowed) reconnect?.arm();
      } else if (
        $printerClient instanceof NiimbotCapacitorBleClient &&
        $automation?.autoConnectDeviceId !== undefined
      ) {
        await $printerClient.connect({ deviceId: $automation.autoConnectDeviceId });
      } else {
        await $printerClient.connect();
      }
    } catch (e) {
      if (attempt !== connectionAttempt) return;
      connectionState.set("disconnected");
      if (isUserCancelled(e)) return;
      if (automatic) throw e;
      else if (isNative) failure = connectionFeedback(e);
      else Toasts.error(e);
    }
  };

  const onDisconnectClicked = async () => {
    if ($printJobActive) {
      Toasts.error("Finish or cancel the current print job first.");
      return;
    }
    reconnect?.pause();
    try {
      if ($printerClient instanceof NativeNiimbotClient) await $printerClient.disconnect({ intentional: true });
      else await $printerClient.disconnect();
    } catch (error) {
      Toasts.error(error);
    }
  };

  const onManageDevices = async () => {
    if ($printJobActive) return;
    reconnect?.pause();
    if ($connectionState === "connecting") {
      try {
        await nativeRequest<{ cancelled: boolean }>("cancelConnect");
      } catch (error) {
        connectionState.set("disconnected");
        failure = connectionFeedback(error);
        return;
      }
      connectionState.set("disconnected");
    }
    if ($connectionState === "connected") await onDisconnectClicked();
    await onConnectClicked();
  };

  const startHeartbeat = async () => {
    $printerClient.startHeartbeat();
  };

  const stopHeartbeat = async () => {
    $printerClient.stopHeartbeat();
  };

  const reset = async () => {
    await $printerClient.protocol.printerReset();
  };

  const switchConnectionType = (c: ConnectionType) => {
    LocalStoragePersistence.saveLastConnectionType(c);
    connectionType = c;
  };

  const batteryIcon = (value: number): MaterialIcon => {
    if (value >= 90) return "battery_full";
    if (value >= 65) return "battery_5_bar";
    if (value >= 40) return "battery_3_bar";
    if (value >= 15) return "battery_2_bar";
    return "battery_0_bar";
  };

  onMount(() => {
    featureSupport = isNative
      ? { webBluetooth: true, webSerial: true, capacitorBle: false }
      : Utils.getAvailableTransports();

    connectionType = isNative ? "bluetooth" : (LocalStoragePersistence.loadLastConnectionType() ?? "bluetooth");

    if (!featureSupport.capacitorBle && connectionType === "capacitor-ble") {
      connectionType = "bluetooth";
    }
    if (!featureSupport.webSerial && connectionType === "serial") {
      connectionType = "bluetooth";
    }
    if (!featureSupport.webBluetooth && connectionType === "bluetooth" && featureSupport.capacitorBle) {
      connectionType = "capacitor-ble";
    }

    if ($automation !== undefined && $automation.autoConnect && connectionType === "capacitor-ble") {
      onConnectClicked();
    }
    if (isNative) {
      reconnect = new ReconnectController(
        () => onConnectClicked(true),
        () => get(connectionState) === "disconnected" && !get(printJobActive),
        (delay, attempting, exhausted, error) => {
          if (exhausted) {
            const final = connectionFeedback(error ?? "Automatic reconnect stopped after five attempts.");
            reconnectStatus = "";
            failure = {
              detail: `Automatic reconnect stopped after five attempts. ${final.detail}`,
              tip: `${final.tip} You can also choose a different printer in Devices.`,
            };
            return;
          }
          if (attempting) failure = undefined;
          reconnectStatus = attempting ? "Auto-connecting…" : delay ? `Retrying in ${delay / 1000}s` : "";
        },
      );
      unlisten = onNativeEvent((message) => {
        if (message.event === "disconnect" && autoAllowed && hasRememberedDevice) reconnect?.start();
        if (message.event === "reconnect-policy") {
          autoAllowed = message.enabled === true;
          if (!autoAllowed) reconnect?.pause();
          else if (hasRememberedDevice) {
            if (get(connectionState) === "connected") reconnect?.arm();
            else reconnect?.start();
          }
        }
      });
      nativeRequest<{ enabled: boolean; device: unknown }>("knownDevice")
        .then((history) => {
          hasRememberedDevice = !!history.device;
          autoAllowed = history.enabled;
          if (autoAllowed && hasRememberedDevice) reconnect?.start();
        })
        .catch(console.warn);
    }
  });
  onDestroy(() => {
    reconnect?.pause();
    unlisten?.();
  });
</script>

{#if isNative && failure}
  <div class="studio-connection-failure" role="alert" data-testid="connection-failure">
    <strong>Could not connect to the printer</strong>
    <p>{failure.detail}</p>
    <p>{failure.tip}</p>
    <div>
      <button class="btn btn-sm btn-secondary" onclick={onManageDevices} disabled={$printJobActive}
        >Open Devices / retry</button>
      <button class="btn btn-sm btn-link" aria-label="Dismiss connection error" onclick={() => (failure = undefined)}
        >Dismiss</button>
    </div>
  </div>
{/if}

<div class="studio-device-controls">
  {#if isNative && (reconnectStatus || $connectionState === "connecting")}
    <div class="studio-auto-connect" role="status" aria-live="polite" data-testid="auto-connect-status">
      <MdIcon icon="autorenew" />
      <span>{reconnectStatus || "Connecting…"}</span>
      <button
        class="btn btn-link btn-sm studio-auto-cancel"
        type="button"
        data-action="cancel-auto-connect"
        disabled={$printJobActive}
        aria-label="Cancel automatic connection and choose a printer"
        title="Stop the automatic connection attempt and open Devices"
        onclick={onManageDevices}>Cancel</button>
    </div>
  {/if}
  <div class="input-group w-auto input-group-sm flex-nowrap justify-content-end">
    {#if isNative}
      <button
        class="btn btn-secondary"
        onclick={onManageDevices}
        disabled={$printJobActive}
        title={$connectionState === "connecting"
          ? "A connection attempt is in progress. Click to cancel it and choose a printer."
          : reconnectStatus || "Select printer, pair Bluetooth, or manage reconnect"}
        aria-label={$connectionState === "connecting" ? "Cancel connection and open Devices" : "Devices"}
        data-action="devices"><MdIcon icon="print" /> Devices</button>
    {/if}
    {#if $connectionState === "connected"}
      {#if !isNative}
        <button class="btn btn-secondary" data-bs-toggle="dropdown" data-bs-auto-close="outside">
          <MdIcon icon="settings" />
        </button>

        <div class="dropdown-menu p-3">
          {#if $printerInfo}
            <div class="text-secondary">{$tr("connector.device_version")}</div>

            <div class="d-flex border rounded">
              <div class="px-1 bg-light-subtle border-end">HW</div>
              <div class="px-1 flex-grow-1 border-end text-center">{$printerInfo.hardwareVersion}</div>
              <div class="px-1 flex-grow-1 border-end text-center">{$printerInfo.softwareVersion}</div>
              <div class="px-1 bg-body-secondary">FW</div>
            </div>
          {/if}

          <div class="text-secondary mt-2">
            {$tr("connector.rfid.paper")}
            <button class="btn btn-sm p-0" onclick={() => $printerClient.fetchRfidInfo()}
              ><MdIcon icon="loop" /></button>
          </div>

          {#if $rfidInfo.labelRfidInfo?.tagPresent}
            <div class="d-flex border rounded mt-1">
              <div class="px-1 bg-light-subtle border-end">{$tr("connector.rfid.usage")}</div>
              <div class="px-1 flex-grow-1 d-flex align-items-center gap-1">
                <div class="progress flex-grow-1" role="progressbar" style:height="0.6rem">
                  <div
                    class="progress-bar"
                    style:width={`${percentage($rfidInfo.labelRfidInfo.usedPaper, $rfidInfo.labelRfidInfo.allPaper)}%`}>
                  </div>
                </div>
                <div class="fs-08">
                  {$rfidInfo.labelRfidInfo?.usedPaper} / {$rfidInfo.labelRfidInfo?.allPaper}
                </div>
              </div>
            </div>

            <div class="d-flex border rounded mt-1">
              <div class="px-1 bg-light-subtle border-end">{$tr("connector.rfid.type")}</div>
              <div class="px-1 flex-grow-1 text-center">
                {$tr(`preview.label_type.${LabelType[$rfidInfo.labelRfidInfo?.consumablesType]}` as TranslationKey)} ({$rfidInfo
                  .labelRfidInfo?.consumablesType})
              </div>
            </div>

            {#if $rfidInfo.paperInfo?.paperWidth !== undefined && $rfidInfo.paperInfo?.paperHeight !== undefined}
              <div class="d-flex border rounded mt-1">
                <div class="px-1 bg-light-subtle border-end">{$tr("connector.rfid.dimensions")}</div>
                <div class="px-1 flex-grow-1 text-center">
                  {$rfidInfo.paperInfo.paperWidth}x{$rfidInfo.paperInfo.paperHeight}mm
                </div>
              </div>
            {/if}
          {:else}
            {$tr("connector.rfid.no_tag")}
          {/if}

          {#if $rfidInfo.ribbonRfidInfo?.tagPresent}
            <div class="text-secondary mt-2">
              {$tr("connector.rfid.ribbon")}
              <button class="btn btn-sm p-0" onclick={() => $printerClient.fetchRfidInfo()}
                ><MdIcon icon="loop" /></button>
            </div>

            <div class="d-flex border rounded mt-1">
              <div class="px-1 bg-light-subtle border-end">{$tr("connector.rfid.usage")}</div>
              <div class="px-1 flex-grow-1 d-flex align-items-center gap-1">
                <div class="progress flex-grow-1" role="progressbar" style:height="0.6rem">
                  <div
                    class="progress-bar"
                    style:width={`${percentage($rfidInfo.ribbonRfidInfo.usedPaper, $rfidInfo.ribbonRfidInfo.allPaper)}%`}>
                  </div>
                </div>
                <div class="fs-08">
                  {$rfidInfo.ribbonRfidInfo?.usedPaper} / {$rfidInfo.ribbonRfidInfo?.allPaper}
                </div>
              </div>
            </div>
          {/if}

          <div class="text-secondary mt-2">{$tr("connector.settings")}</div>

          <div class="form-check form-switch">
            <input
              class="form-check-input"
              type="checkbox"
              role="switch"
              id="power-sound-switch"
              checked={$printerInfo.settings.powerSound}
              onchange={() =>
                $printerClient.setSoundEnabled(SoundSettingsItemType.PowerSound, !$printerInfo.settings.powerSound)} />
            <label class="form-check-label" for="power-sound-switch">{$tr("connector.settings.power_sound")}</label>
          </div>

          <div class="form-check form-switch">
            <input
              class="form-check-input"
              type="checkbox"
              role="switch"
              id="connection-sound-switch"
              checked={$printerInfo.settings.connectionSound}
              onchange={() =>
                $printerClient.setSoundEnabled(
                  SoundSettingsItemType.BluetoothConnectionSound,
                  !$printerInfo.settings.connectionSound,
                )} />
            <label class="form-check-label" for="connection-sound-switch"
              >{$tr("connector.settings.connection_sound")}</label>
          </div>

          <button class="btn btn-sm btn-outline-secondary w-100 mt-3" onclick={() => (verboseInfoShow = true)}
            >{$tr("connector.open_verbose")}</button>

          <button
            class="btn btn-sm btn-outline-secondary d-block w-100 mt-1"
            type="button"
            data-bs-toggle="collapse"
            data-bs-target="#firmware_flashing">
            {$tr("connector.firmware_flashing")}
            <MdIcon icon="expand_more" />
          </button>

          <div class="collapse" id="firmware_flashing">
            <FirmwareUpdater />
          </div>

          <button
            class="btn btn-sm btn-outline-secondary d-block w-100 mt-1"
            type="button"
            data-bs-toggle="collapse"
            data-bs-target="#tests">
            {$tr("debug.title")}
            <MdIcon icon="expand_more" />
          </button>

          <div class="collapse" id="tests">
            <div class="d-flex flex-wrap gap-1 mt-1">
              <button class="btn btn-sm btn-primary" onclick={startHeartbeat}>Heartbeat on</button>
              <button class="btn btn-sm btn-primary" onclick={stopHeartbeat}>Heartbeat off</button>
              <button class="btn btn-sm btn-primary" onclick={reset}>Reset</button>
            </div>
          </div>
        </div>
      {/if}

      <span class="input-group-text">
        {#if connectionType === "serial" || ($printerClient instanceof NativeNiimbotClient && $printerClient.getTransportKind() === "serial")}
          <MdIcon icon="usb" />
        {:else}
          <MdIcon icon="bluetooth" />
        {/if}
      </span>
      <span class="input-group-text {$heartbeatFails > 0 ? 'text-warning' : ''}">
        {$printerMeta?.model ?? $connectedPrinterName}
      </span>
      <span class="input-group-text">
        <MdIcon icon={batteryIcon($heartbeatData?.batteryPercents ?? $printerInfo?.batteryPercents ?? 0)} class="r-90"
        ></MdIcon>
      </span>
    {:else}
      {#if featureSupport.webBluetooth && !isNative}
        <button
          disabled={$connectionState === "connecting"}
          class="btn text-nowrap {connectionType === 'bluetooth' ? 'btn-light' : 'btn-outline-secondary'}"
          onclick={() => switchConnectionType("bluetooth")}>
          <MdIcon icon="bluetooth" />
          {$tr("connector.bluetooth")}
        </button>
      {/if}
      {#if featureSupport.webSerial && !isNative}
        <button
          disabled={$connectionState === "connecting"}
          class="btn text-nowrap {connectionType === 'serial' ? 'btn-light' : 'btn-outline-secondary'}"
          onclick={() => switchConnectionType((connectionType = "serial"))}>
          <MdIcon icon="usb" />
          {$tr("connector.serial")}
        </button>
      {/if}
      {#if featureSupport.capacitorBle}
        <button
          disabled={$connectionState === "connecting"}
          class="btn text-nowrap {connectionType === 'capacitor-ble' ? 'btn-light' : 'btn-outline-secondary'}"
          onclick={() => switchConnectionType((connectionType = "capacitor-ble"))}>
          <MdIcon icon="usb" />
          Capacitor BLE
        </button>
      {/if}
    {/if}

    {#if $connectionState !== "connected" && !isNative}
      <button
        class="btn btn-primary"
        disabled={$connectionState === "connecting" ||
          (!featureSupport.capacitorBle && !featureSupport.webBluetooth && !featureSupport.webSerial)}
        onclick={() => onConnectClicked()}>
        <MdIcon icon="power" />
        {#if isNative}{$connectionState === "connecting" ? "Connecting…" : "Select printer"}{/if}
      </button>
    {/if}

    {#if $connectionState === "connected"}
      <button class="btn btn-danger" onclick={onDisconnectClicked}>
        <MdIcon icon="power_off" />
      </button>
    {/if}

    {#if verboseInfoShow}
      <PrinterVerboseInfo bind:show={verboseInfoShow} />
    {/if}
  </div>
</div>

<style>
  .studio-device-controls {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 8px;
    min-width: 0;
  }
  .studio-auto-connect {
    display: flex;
    align-items: center;
    gap: 4px;
    color: var(--bs-secondary-color);
    font-size: 11px;
    white-space: nowrap;
  }
  .studio-auto-connect :global(.mdi) {
    font-size: 16px;
  }
  .studio-auto-cancel {
    padding: 0 2px;
    font-size: 11px;
    line-height: 1.2;
    text-decoration: none;
  }
  .studio-auto-cancel:hover {
    text-decoration: underline;
  }
  .studio-connection-failure {
    position: fixed;
    right: 20px;
    bottom: 24px;
    z-index: 1080;
    width: min(440px, calc(100vw - 40px));
    padding: 16px;
    border: 1px solid var(--studio-red);
    border-radius: 12px;
    background: var(--studio-background);
    color: var(--studio-foreground);
    box-shadow: 0 6px 24px #0003;
    font-size: 12px;
    white-space: normal;
    overflow-wrap: anywhere;
  }
  .studio-connection-failure p {
    margin: 8px 0;
  }
  .studio-connection-failure > div {
    display: flex;
    gap: 8px;
  }
  .dropdown-menu {
    width: 100vw;
    max-width: 300px;
  }
</style>
