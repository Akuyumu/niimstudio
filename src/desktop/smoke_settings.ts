/** Simulated printer settings; never calls a physical transport or prints. */
import { tick } from "svelte";
import { get } from "svelte/store";
import type { NiimbotAbstractClient } from "@mmote/niimbluelib";
import { printerClient, printJobActive } from "$/stores";
import { nativeRequest } from "$/desktop/bridge";

const waitFor = async (condition: () => boolean) => {
  const deadline = Date.now() + 5000;
  while (!condition()) {
    if (Date.now() > deadline) throw new Error("Settings UI did not settle");
    await new Promise((resolve) => setTimeout(resolve, 20));
    await tick();
  }
};
const checkbox = (name: string) => document.querySelector<HTMLInputElement>(`[data-setting="${name}"]`)!;

export async function runSettingsSmoke() {
  const originalClient = get(printerClient);
  const originalPrinting = get(printJobActive);
  const writes: unknown[] = [];
  let mode = 1;
  let powerSound = true;
  let connectionSound = true;
  const fakeClient = {
    protocol: {
      isSoundEnabled: async (type: number) => (type === 2 ? powerSound : connectionSound),
      setSoundEnabled: async (type: number, enabled: boolean) => {
        writes.push([type, enabled]);
        if (type === 2) powerSound = enabled;
        else connectionSound = enabled;
      },
      getAutoShutDownTime: async () => mode,
      setAutoShutDownTime: async (value: number) => {
        writes.push(value);
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
    await nativeRequest("setReconnectPolicy", { enabled: previous });
    document.querySelector<HTMLButtonElement>('[data-action="settings-close"]')!.click();
    await waitFor(() => !document.querySelector(".modal.show"));
    return {
      settingsReadOnlyOnOpen,
      soundSettingVerified,
      settingsLockedDuringPrint,
      sleepSettingVerified,
      settingsReconnectWorks,
    };
  } finally {
    printJobActive.set(originalPrinting);
    printerClient.set(originalClient);
  }
}
