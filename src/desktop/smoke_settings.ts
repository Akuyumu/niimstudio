/** Simulated printer settings; never calls a physical transport or prints. */
import { tick } from "svelte";
import { get } from "svelte/store";
import type { NiimbotAbstractClient } from "@mmote/niimbluelib";
import { printerClient, printerInfo, printJobActive } from "$/stores";
import { nativeRequest } from "$/desktop/bridge";

const waitFor = async (condition: () => boolean) => {
  await tick();
  const deadline = Date.now() + 5000;
  while (!condition()) {
    if (Date.now() > deadline)
      throw new Error(
        `Settings UI did not settle: ${document.querySelector(".modal.show")?.textContent?.slice(0, 1400)}`,
      );
    await new Promise((resolve) => setTimeout(resolve, 20));
    await tick();
  }
};
const checkbox = (name: string) => document.querySelector<HTMLInputElement>(`[data-setting="${name}"]`)!;

export async function runSettingsSmoke() {
  const originalClient = get(printerClient);
  const originalPrinting = get(printJobActive);
  const originalInfo = get(printerInfo);
  const writes: unknown[] = [];
  let mode = 1;
  let powerSound = true;
  let connectionSound = true;
  let rejectSoundWrite = false;
  let soundReadFails = false;
  let allReadsFail = false;
  let rejectSleepWrite = false;
  const fakeClient = {
    protocol: {
      isSoundEnabled: async (type: number) => {
        if (allReadsFail || (type === 2 && soundReadFails)) throw new Error("Synthetic unsupported read");
        return type === 2 ? powerSound : connectionSound;
      },
      setSoundEnabled: async (type: number, enabled: boolean) => {
        writes.push([type, enabled]);
        if (rejectSoundWrite) return;
        if (type === 2) powerSound = enabled;
        else connectionSound = enabled;
      },
      getAutoShutDownTime: async () => {
        if (allReadsFail) throw new Error("Synthetic unsupported sleep");
        return mode;
      },
      setAutoShutDownTime: async (value: number) => {
        writes.push(value);
        if (rejectSleepWrite) return;
        mode = value;
      },
    },
  } as unknown as NiimbotAbstractClient;
  printerClient.set(fakeClient);
  try {
    document.querySelector<HTMLButtonElement>('[data-action="settings"]')!.click();
    await waitFor(
      () => !!document.querySelector('.modal.show [data-setting="power-sound"]') && !checkbox("power-sound").disabled,
    );
    const settingsReadOnlyOnOpen = writes.length === 0;
    checkbox("power-sound").click();
    await waitFor(() => !checkbox("power-sound").disabled);
    const soundSettingVerified = !powerSound && !checkbox("power-sound").checked;
    printJobActive.set(true);
    await tick();
    const before = writes.length;
    checkbox("connection-sound").click();
    const settingsLockedDuringPrint = checkbox("connection-sound").disabled && writes.length === before;
    printJobActive.set(false);
    await tick();
    const sleep = document.querySelector<HTMLSelectElement>('[data-setting="sleep-mode"]')!;
    sleep.value = "4";
    sleep.dispatchEvent(new Event("change", { bubbles: true }));
    await waitFor(() => !sleep.disabled);
    const sleepSettingVerified =
      mode === 4 && sleep.value === "4" && !!sleep.selectedOptions[0].textContent?.includes("firmware");
    await nativeRequest("testSnapshot", { name: "settings" });
    const reconnect = checkbox("reconnect");
    const previous = reconnect.checked;
    reconnect.click();
    await waitFor(() => !reconnect.disabled);
    const policy = await nativeRequest<{ enabled: boolean }>("knownDevice");
    const settingsReconnectWorks = policy.enabled === !previous && reconnect.checked === !previous;
    await waitFor(() => !document.querySelector(".modal.show .alert-info"));
    const settingsNoticeExpires =
      !document.querySelector(".modal.show .alert-info") &&
      !!document.querySelector('[data-feedback="powerSound"].text-success');
    await nativeRequest("setReconnectPolicy", { enabled: previous });

    rejectSoundWrite = true;
    checkbox("power-sound").click();
    await waitFor(() => !checkbox("power-sound").disabled);
    const soundFailureVisible =
      !checkbox("power-sound").checked &&
      !!document.querySelector('[data-feedback="powerSound"].text-danger') &&
      document.querySelector('[role="alert"]')?.textContent?.includes("printer reports off") === true;
    await nativeRequest("testSnapshot", { name: "settings-failure" });
    rejectSoundWrite = false;
    soundReadFails = true;
    checkbox("power-sound").click();
    await waitFor(() => !checkbox("reconnect").disabled);
    const unconfirmedSettingHidden =
      !document.querySelector('[data-setting="power-sound"]') &&
      document.querySelector('[data-feedback="powerSound"]')?.textContent?.includes("current value is unknown") ===
        true;

    document.querySelector<HTMLButtonElement>('[data-action="settings-refresh"]')!.click();
    await waitFor(() => !checkbox("reconnect").disabled);
    const unsupportedSettingsHidden =
      !document.querySelector('[data-setting="power-sound"]') &&
      !!document.querySelector('[data-setting="connection-sound"]');

    rejectSleepWrite = true;
    const currentSleep = document.querySelector<HTMLSelectElement>('[data-setting="sleep-mode"]')!;
    currentSleep.value = "2";
    currentSleep.dispatchEvent(new Event("change", { bubbles: true }));
    await waitFor(() => !currentSleep.disabled);
    const sleepFailureVisible =
      currentSleep.value === "4" && !!document.querySelector('[data-feedback="sleepMode"].text-danger');
    rejectSleepWrite = false;

    mode = 1;
    printerInfo.update((info) => ({
      ...info,
      capabilities: { ...info.capabilities, autoShutdownRange: { min: 1, max: 3 } },
    }));
    document.querySelector<HTMLButtonElement>('[data-action="settings-refresh"]')!.click();
    await waitFor(() => !checkbox("reconnect").disabled);
    const constrainedSleep = document.querySelector<HTMLSelectElement>('[data-setting="sleep-mode"]')!;
    const unsupportedSleepModesHidden =
      Array.from(constrainedSleep.options)
        .map((option) => option.value)
        .join(",") === "1,2,3";
    allReadsFail = true;
    document.querySelector<HTMLButtonElement>('[data-action="settings-refresh"]')!.click();
    await waitFor(() => !checkbox("reconnect").disabled);
    const allUnsupportedSettingsHidden =
      !!document.querySelector('[data-testid="no-printer-settings"]') &&
      !document.querySelector('[data-setting="connection-sound"]') &&
      !document.querySelector('[data-setting="sleep-mode"]');
    await nativeRequest("testSnapshot", { name: "settings-unavailable" });
    document.querySelector<HTMLButtonElement>('[data-action="settings-close"]')!.click();
    await waitFor(() => !document.querySelector(".modal.show"));
    return {
      settingsReadOnlyOnOpen,
      soundSettingVerified,
      settingsLockedDuringPrint,
      sleepSettingVerified,
      settingsReconnectWorks,
      settingsNoticeExpires,
      soundFailureVisible,
      unconfirmedSettingHidden,
      unsupportedSettingsHidden,
      sleepFailureVisible,
      unsupportedSleepModesHidden,
      allUnsupportedSettingsHidden,
    };
  } finally {
    printJobActive.set(originalPrinting);
    printerClient.set(originalClient);
    printerInfo.set(originalInfo);
  }
}
