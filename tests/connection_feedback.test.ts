import test from "node:test";
import assert from "node:assert/strict";
import { connectionFeedback } from "../src/desktop/connection_feedback.ts";

test("authentication errors suggest BLE pairing without inventing a PIN", () => {
  const result = connectionFeedback(new Error("org.bluez.Error.AuthenticationRejected"));
  assert.match(result.detail, /AuthenticationRejected/);
  assert.match(result.tip, /Pair/);
  assert.match(result.tip, /Bluetooth LE/);
  assert.doesNotMatch(result.tip, /0000|1234|PIN/);
});
test("classic entries point to the LE entry instead of more pairing", () => {
  assert.match(connectionFeedback("classic Serial Port entry").tip, /Pairing the classic entry will not enable BLE/);
});
test("unknown failures preserve the actual cause and offer retry or USB", () => {
  const result = connectionFeedback(new Error("Unable to perform initial negotiate: timeout"));
  assert.match(result.detail, /initial negotiate: timeout/);
  assert.match(result.tip, /phone/);
  assert.match(result.tip, /USB/);
});
test("USB permission failures do not suggest Bluetooth pairing", () => {
  const result = connectionFeedback("USB permission denied");
  assert.match(result.tip, /device permissions/);
  assert.doesNotMatch(result.tip, /Pair first/);
});
