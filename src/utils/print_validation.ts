export function validatePrintJob(options: {
  width: number;
  height: number;
  direction: "left" | "top";
  copies: number;
  pages: number;
  density: number;
  printheadPixels?: number;
  densityMin?: number;
  densityMax?: number;
}): string | undefined {
  const { width, height, direction, copies, pages, density, printheadPixels, densityMin, densityMax } = options;
  if (![width, height, copies, pages].every((value) => Number.isSafeInteger(value) && value > 0)) {
    return "Label dimensions, copies, and page count must be positive whole numbers.";
  }
  if (copies * pages > 65535) {
    return "Too many labels in one job. Copies × designs must not exceed 65,535; split the batch into smaller jobs.";
  }
  const headSize = direction === "top" ? width : height;
  if (printheadPixels !== undefined && headSize > printheadPixels) {
    return `This label needs ${headSize} printhead pixels; the selected printer supports ${printheadPixels}. Adjust label dimensions or DPI first.`;
  }
  if (
    !Number.isFinite(density) ||
    (densityMin !== undefined && density < densityMin) ||
    (densityMax !== undefined && density > densityMax)
  ) {
    return "Print density is outside the selected printer’s supported range.";
  }
  return undefined;
}
