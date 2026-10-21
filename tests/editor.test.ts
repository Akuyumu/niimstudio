import test from "node:test";
import assert from "node:assert/strict";
import { csvParse } from "../src/utils/csv.ts";
import { UndoRedo } from "../src/utils/undo_redo.ts";
import { validatePrintJob } from "../src/utils/print_validation.ts";

test("printing refuses invalid copy counts and labels wider than the printhead", () => {
  const job = {
    width: 472,
    height: 354,
    direction: "top" as const,
    copies: 1,
    pages: 1,
    density: 3,
    printheadPixels: 567,
    densityMin: 1,
    densityMax: 5,
  };
  assert.equal(validatePrintJob(job), undefined);
  assert.match(validatePrintJob({ ...job, width: 592 })!, /supports 567/);
  assert.match(validatePrintJob({ ...job, copies: 0 })!, /positive whole/);
  assert.match(validatePrintJob({ ...job, copies: 1.5 })!, /positive whole/);
  assert.match(validatePrintJob({ ...job, density: Infinity })!, /density/);
  assert.match(validatePrintJob({ ...job, density: 6 })!, /density/);
  assert.match(validatePrintJob({ ...job, pages: 0 })!, /positive whole/);
});

test("CSV handles quoted fields, multiline content, missing fields, and Unicode", () => {
  const parsed = csvParse('name,description,empty\r\n"水","line 1\nline 2"\r\n"a,b","double ""quote""",z');
  assert.deepEqual(parsed.columns, ["name", "description", "empty"]);
  assert.deepEqual(parsed[0], { name: "水", description: "line 1\nline 2", empty: "" });
  assert.deepEqual(parsed[1], { name: "a,b", description: 'double "quote"', empty: "z" });
});

test("job copy/page totals cannot overflow the protocol's 16-bit page count", () => {
  const job = { width: 472, height: 354, direction: "top" as const, copies: 65535, pages: 1, density: 3 };
  assert.equal(validatePrintJob(job), undefined);
  assert.match(validatePrintJob({ ...job, copies: 65536 })!, /Too many labels/);
  assert.match(validatePrintJob({ ...job, copies: 1000, pages: 1000 })!, /Copies × designs/);
});

test("CSV treats dangerous property names as ordinary data", () => {
  const parsed = csvParse("__proto__,constructor\nhello,world");
  assert.equal(Object.getPrototypeOf(parsed[0]), Object.prototype);
  assert.equal(parsed[0].__proto__, "hello");
  assert.equal(parsed[0].constructor, "world");
});

test("CSV accepts empty and header-only input without eval", () => {
  assert.deepEqual(csvParse("").columns, []);
  assert.equal(csvParse("name\n").length, 0);
});

test("editing after undoing to the first state discards the abandoned redo branch", async () => {
  const history = new UndoRedo();
  let current = "A";
  const canvas = { toJSON: () => ({ version: "7", objects: [{ value: current }] }) };
  const label = { size: { width: 240, height: 96 }, printDirection: "left" as const };
  history.onLabelUpdate = async (data) => {
    current = (data.canvas.objects[0] as unknown as { value: string }).value;
  };
  // A minimal canvas serializer isolates the history algorithm from the DOM.
  const push = () => history.push(canvas as never, label);
  push();
  current = "B";
  push();
  current = "C";
  push();
  await history.undo();
  await history.undo();
  assert.equal(current, "A");
  current = "D";
  push();
  await history.undo();
  assert.equal(current, "A");
  await history.redo();
  assert.equal(current, "D");
  await history.redo();
  assert.equal(current, "D");
});

test("undo history is bounded to twenty snapshots", async () => {
  const history = new UndoRedo();
  let value = 0;
  const canvas = { toJSON: () => ({ version: "7", objects: [{ value }] }) };
  history.onLabelUpdate = async (data) => {
    value = (data.canvas.objects[0] as unknown as { value: number }).value;
  };
  for (; value < 25; value++)
    history.push(canvas as never, { size: { width: 240, height: 96 }, printDirection: "left" });
  for (let index = 0; index < 30; index++) await history.undo();
  assert.equal(value, 5);
});
