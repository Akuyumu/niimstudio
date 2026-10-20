/** Only a packaged GTK view exposes this bridge. Never a network service. */
import { UserCancelledError } from "./cancellation";
type Palette = Record<string, string>;
type NativeMessage = {
  id?: number;
  value?: unknown;
  error?: string;
  cancelled?: boolean;
  event?: "data" | "disconnect" | "theme" | "reconnect-policy" | "fonts" | "update" | "updateProgress";
  enabled?: boolean;
  data?: number[];
  palette?: Palette;
  families?: string[];
  version?: string;
  tag?: string;
  state?: "ready" | "failed";
  message?: string;
  reason?: string;
};

declare global {
  interface Window {
    __NIIMSTUDIO_NATIVE__?: boolean;
    __NIIMSTUDIO_SMOKE__?: boolean;
    __NIIMSTUDIO_DEMO__?: boolean;
    __NIIMSTUDIO_RESTART_VERIFY__?: boolean;
    __NIIMSTUDIO_BENCHMARK__?: boolean;
    __NIIMSTUDIO_LIFECYCLE_MODE__?: string;
    __niimstudioPrepareClose?: () => boolean;
    __niimstudioReceive?: (message: NativeMessage) => void;
    __niimstudioSmokeTest?: () => Promise<Record<string, unknown>>;
    webkit?: { messageHandlers: { studio: { postMessage: (message: unknown) => void } } };
  }
}

export const isNative = window.__NIIMSTUDIO_NATIVE__ === true;
let nextId = 1;
const pending = new Map<
  number,
  { resolve: (value: unknown) => void; reject: (error: Error) => void; timer: ReturnType<typeof setTimeout> }
>();
const listeners = new Set<(message: NativeMessage) => void>();
const paletteKeys = new Set<string>();

if (isNative) {
  window.__niimstudioReceive = (message) => {
    if (message.id !== undefined) {
      const request = pending.get(message.id);
      if (!request) return;
      clearTimeout(request.timer);
      pending.delete(message.id);
      if (message.cancelled) request.reject(new UserCancelledError());
      else if (message.error) request.reject(new Error(message.error));
      else request.resolve(message.value);
    } else {
      if (message.event === "theme" && message.palette) applyPalette(message.palette);
      listeners.forEach((listener) => listener(message));
    }
  };
}

export function nativeRequest<T = void>(
  op: string,
  args: Record<string, unknown> = {},
  timeoutMs = 30_000,
): Promise<T> {
  return new Promise((resolve, reject) => {
    if (!isNative || !window.webkit?.messageHandlers.studio) {
      reject(new Error("Native desktop integration is unavailable"));
      return;
    }
    const id = nextId++;
    const timer = setTimeout(() => {
      pending.delete(id);
      reject(new Error(`Native ${op} request timed out`));
    }, timeoutMs);
    pending.set(id, { resolve: (value) => resolve(value as T), reject, timer });
    try {
      window.webkit.messageHandlers.studio.postMessage({ id, op, ...args });
    } catch (error) {
      pending.delete(id);
      clearTimeout(timer);
      reject(error);
    }
  });
}

export function onNativeEvent(listener: (message: NativeMessage) => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function reportConnectionLoss(reason: string) {
  listeners.forEach((listener) => listener({ event: "disconnect", reason }));
}

export function applyPalette(palette: Palette) {
  const root = document.documentElement;
  for (const key of paletteKeys) root.style.removeProperty(key);
  paletteKeys.clear();
  root.dataset.bsTheme = palette.mode === "light" ? "light" : "dark";
  for (const [name, color] of Object.entries(palette)) {
    if (/^[a-z_]+$/.test(name) && /^#[0-9a-f]{6}$/i.test(color)) {
      const key = `--studio-${name.replaceAll("_", "-")}`;
      root.style.setProperty(key, color);
      paletteKeys.add(key);
    }
  }
}

export async function initializeDesktop() {
  if (!isNative) return;
  document.documentElement.classList.add("studio-native");
  const { palette } = await nativeRequest<{ palette: Palette }>("ready");
  applyPalette(palette);
}
