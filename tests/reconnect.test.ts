import test from "node:test";
import assert from "node:assert/strict";
import { ReconnectController } from "../src/desktop/reconnect.ts";

const flush = () => new Promise<void>((resolve) => setImmediate(resolve));

test("reconnect retries use capped backoff and manual disconnect stops the loop", async (context) => {
  context.mock.timers.enable({ apis: ["setTimeout"] });
  let attempts = 0;
  let delay = -1;
  const controller = new ReconnectController(
    async () => {
      attempts++;
      throw new Error("offline");
    },
    () => true,
    (value) => {
      delay = value;
    },
  );
  controller.start();
  context.mock.timers.tick(0);
  await flush();
  assert.equal(attempts, 1);
  assert.equal(delay, 2000);
  for (const [advance, next] of [
    [2000, 5000],
    [5000, 10000],
    [10000, 30000],
    [30000, 60000],
    [60000, 60000],
  ]) {
    context.mock.timers.tick(advance);
    await flush();
    assert.equal(delay, next);
  }
  controller.pause();
  const stoppedAt = attempts;
  context.mock.timers.tick(300000);
  await flush();
  assert.equal(attempts, stoppedAt);
});

test("reconnect waits for printing/manual connection to finish", async (context) => {
  context.mock.timers.enable({ apis: ["setTimeout"] });
  let safe = false;
  let attempts = 0;
  const controller = new ReconnectController(
    async () => {
      attempts++;
    },
    () => safe,
    () => undefined,
  );
  controller.start();
  context.mock.timers.tick(0);
  await flush();
  assert.equal(attempts, 0);
  safe = true;
  context.mock.timers.tick(5000);
  await flush();
  assert.equal(attempts, 1);
  context.mock.timers.tick(300000);
  await flush();
  assert.equal(attempts, 1); // A successful reconnect does not keep polling.
  controller.pause();
});

test("duplicate disconnect signals cannot create concurrent reconnect attempts", async (context) => {
  context.mock.timers.enable({ apis: ["setTimeout"] });
  let attempts = 0;
  let finish: (() => void) | undefined;
  const controller = new ReconnectController(
    async () => {
      attempts++;
      await new Promise<void>((resolve) => {
        finish = resolve;
      });
    },
    () => true,
    () => undefined,
  );
  controller.start();
  context.mock.timers.tick(0);
  await flush();
  controller.start();
  controller.start();
  context.mock.timers.tick(10000);
  await flush();
  assert.equal(attempts, 1);
  finish!();
  await flush();
  controller.pause();
});
