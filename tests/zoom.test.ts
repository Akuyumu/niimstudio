import test from "node:test";
import assert from "node:assert/strict";
import { fitZoom, MAX_FIT_ZOOM, MIN_ZOOM } from "../src/desktop/zoom.ts";

test("fit zoom shows the whole label without exceeding the readability cap", () => {
  assert.equal(fitZoom(240, 96, 1000, 500), MAX_FIT_ZOOM);
  const wide = fitZoom(576, 354, 900, 500)!;
  assert.equal(wide, Math.min(900 / 576, 500 / 354));
  const tall = fitZoom(300, 900, 1000, 480)!;
  assert.equal(tall, 480 / 900);
  assert.equal(fitZoom(100000, 100000, 1000, 500), MIN_ZOOM);
});
test("fit zoom rejects unavailable dimensions", () => {
  for (const values of [
    [0, 100, 100, 100],
    [100, 0, 100, 100],
    [100, 100, 0, 100],
    [100, 100, 100, 0],
    [NaN, 100, 100, 100],
    [100, Infinity, 100, 100],
  ]) {
    assert.equal(fitZoom(...(values as [number, number, number, number])), undefined);
  }
});
