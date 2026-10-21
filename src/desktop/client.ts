/** Reuse NiimBlueLib's complete protocol; GTK owns only raw byte transport. */
import {
  ConnectEvent,
  ConnectResult,
  DisconnectEvent,
  NiimbotAbstractClient,
  RawPacketSentEvent,
  RfidInfoFetchedEvent,
  Utils,
  type ConnectionInfo,
} from "@mmote/niimbluelib";
import { nativeRequest, onNativeEvent, reportConnectionLoss } from "./bridge";
import { mediaReadReport, readMedia } from "./media_reads";

export class NativeNiimbotClient extends NiimbotAbstractClient {
  private connected = false;
  private established = false;
  private unlisten?: () => void;
  private transportKind?: string;

  getTransportKind() {
    return this.transportKind;
  }

  override async fetchRfidInfo() {
    const { info, errors } = await readMedia(this.protocol);
    this.rfidInfo = info;
    mediaReadReport.set(errors);
    this.emit("rfidinfofetched", new RfidInfoFetchedEvent(info));
    return info;
  }

  async connect(options?: { automatic?: boolean }): Promise<ConnectionInfo> {
    if (this.connected) await this.disconnect();
    this.unlisten?.();
    this.unlisten = onNativeEvent((message) => {
      if (message.event === "data" && message.data) this.processRawPacket(new Uint8Array(message.data));
      if (message.event === "disconnect" && this.connected) this.markDisconnected();
    });
    try {
      const device = await nativeRequest<{ name: string; kind: string }>(
        "connect",
        { automatic: options?.automatic === true },
        options?.automatic ? 90_000 : 600_000,
      );
      this.transportKind = device.kind;
      this.connected = true;
      await this.negotiateAndGetPrinterInfo(() => void this.disconnect({ intentional: true }));
      const info: ConnectionInfo = {
        deviceName: device.name,
        result: this.printerInfo.connectResult ?? ConnectResult.FirmwareErrors,
      };
      if (
        !this.connected ||
        ![ConnectResult.Connected, ConnectResult.ConnectedNew, ConnectResult.ConnectedV3].includes(info.result)
      ) {
        throw new Error(
          `Printer handshake did not establish a connection (${ConnectResult[info.result] ?? info.result}).`,
        );
      }
      await nativeRequest("remember").catch(console.warn);
      this.established = true;
      this.emit("connect", new ConnectEvent(info));
      return info;
    } catch (error) {
      await this.disconnect({ intentional: true }).catch(() => undefined);
      throw error;
    }
  }

  private markDisconnected() {
    const wasConnected = this.connected;
    this.connected = false;
    this.established = false;
    this.transportKind = undefined;
    mediaReadReport.set({});
    this.stopHeartbeat();
    this.unlisten?.();
    this.unlisten = undefined;
    if (wasConnected) this.emit("disconnect", new DisconnectEvent());
  }

  async disconnect(options?: { intentional?: boolean }): Promise<void> {
    const lostEstablishedSession = this.established;
    this.markDisconnected();
    await nativeRequest("disconnect");
    // NiimBlueLib also calls disconnect after exhausted heartbeat failures.
    if (lostEstablishedSession && !options?.intentional) reportConnectionLoss("Printer stopped responding");
  }

  isConnected(): boolean {
    return this.connected;
  }

  // Stable identity; the native chooser can select either USB or BLE.
  getType(): "bluetooth" {
    return "bluetooth";
  }

  async sendRaw(data: Uint8Array, force?: boolean): Promise<void> {
    const send = async () => {
      if (!this.connected) throw new Error("Printer is disconnected");
      await Utils.sleep(this.packetIntervalMs);
      await nativeRequest("write", { data: Array.from(data) });
      this.emit("rawpacketsent", new RawPacketSentEvent(data));
    };
    if (force) await send();
    else await this.mutex.runExclusive(send);
  }
}
