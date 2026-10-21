/** Remember only sizes explicitly associated by the user, never inferred from a SKU. */
import { z } from "zod";
import { writablePersisted } from "$/utils/persistence";
import { stockSizes } from "$/desktop/media";
export { rollStockKey } from "$/desktop/media";

export const savedRollStocks = writablePersisted(
  "studio_roll_stocks",
  z.record(z.string(), z.enum(stockSizes.map((stock) => stock.id))),
  {},
);
