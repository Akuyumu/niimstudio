/** One bounded retry loop; never retries prints or opens a pairing dialog. */
export class ReconnectController {
  private enabled = false;
  private running = false;
  private timer?: ReturnType<typeof setTimeout>;
  private failures = 0;
  private readonly delays = [2_000, 5_000, 10_000, 30_000, 60_000];
  private readonly attempt: () => Promise<void>;
  private readonly canAttempt: () => boolean;
  private readonly status: (delayMs: number, attempting: boolean) => void;

  constructor(
    attempt: () => Promise<void>,
    canAttempt: () => boolean,
    status: (delayMs: number, attempting: boolean) => void,
  ) {
    this.attempt = attempt;
    this.canAttempt = canAttempt;
    this.status = status;
  }

  arm() {
    this.enabled = true;
    this.failures = 0;
  }
  start() {
    this.enabled = true;
    if (!this.running) this.schedule(0);
  }
  pause() {
    this.enabled = false;
    clearTimeout(this.timer);
    this.timer = undefined;
    this.status(0, false);
  }

  private schedule(delay: number) {
    clearTimeout(this.timer);
    if (!this.enabled) return;
    this.status(delay, delay === 0);
    this.timer = setTimeout(() => void this.run(), delay);
  }

  private async run() {
    this.timer = undefined;
    if (!this.enabled) return;
    // Do not reconnect midway through a still-settling print job or manual link.
    if (!this.canAttempt()) {
      this.schedule(5_000);
      return;
    }
    this.running = true;
    this.status(0, true);
    try {
      await this.attempt();
      this.failures = 0;
      this.status(0, false);
    } catch {
      if (this.enabled) this.schedule(this.delays[Math.min(this.failures++, this.delays.length - 1)]);
    } finally {
      this.running = false;
    }
  }
}
