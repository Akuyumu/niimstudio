import test from "node:test";
import assert from "node:assert/strict";
import { code128b, ean13 } from "../src/utils/barcode.ts";
import { isUserCancelled, UserCancelledError } from "../src/desktop/cancellation.ts";

test("every printable Code 128 character, including dollar and parenthesis, produces binary bars", () => {
  for (let code = 32; code <= 126; code++) {
    const encoded = code128b(String.fromCharCode(code));
    assert.match(encoded, /^[01]+$/, `ASCII ${code}`);
    assert.equal(encoded.length, 46);
  }
  assert.equal(code128b("$").slice(11, 22), "10010001100");
  assert.equal(code128b(")").slice(11, 22), "11001001000");
});

test("short URL barcodes preserve punctuation and reject unsupported content", () => {
  assert.match(code128b("https://a.co?q=$)"), /^[01]+$/);
  assert.throws(() => code128b("水"), /Invalid character/);
  assert.throws(() => code128b("a".repeat(230)), /too long/);
});

test("EAN-13 calculates and verifies its check digit", () => {
  const encoded = ean13("590123412345");
  assert.equal(encoded.text, "5901234123457");
  assert.equal(encoded.bandcode.length, 95);
  assert.match(encoded.bandcode, /^[01]+$/);
  assert.deepEqual(ean13("5901234123457"), encoded);
  assert.throws(() => ean13("5901234123450"), /checksum/);
});

test("intentional dismissals are distinguished from real connection errors", () => {
  assert.equal(isUserCancelled(new UserCancelledError()), true);
  assert.equal(isUserCancelled(new DOMException("Dismissed", "AbortError")), true);
  assert.equal(isUserCancelled(new Error("USB permission denied")), false);
  assert.equal(isUserCancelled(new Error("Printer selection cancelled")), false);
});
