// d3's csvParse generates a Function at runtime. csvParseRows does not, allowing
// us to keep a Content Security Policy without unsafe-eval in the desktop app.
import { csvParseRows, type DSVRowArray } from "d3-dsv";

export function csvParse(text: string): DSVRowArray<string> {
  const [columns = [], ...values] = csvParseRows(text);
  const rows = values.map((row) => Object.fromEntries(columns.map((name, index) => [name, row[index] ?? ""])));
  return Object.assign(rows, { columns });
}
