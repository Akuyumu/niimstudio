/** Display-only label zoom. Never changes label pixels or exported dimensions. */
export const MIN_ZOOM = 0.05;
export const MAX_ZOOM = 4;
export const MAX_FIT_ZOOM = 2;

export function fitZoom(
  naturalWidth: number,
  naturalHeight: number,
  availableWidth: number,
  availableHeight: number,
): number | undefined {
  if (
    ![naturalWidth, naturalHeight, availableWidth, availableHeight].every(
      (value) => Number.isFinite(value) && value > 0,
    )
  ) {
    return;
  }
  const ratio = Math.min(availableWidth / naturalWidth, availableHeight / naturalHeight, MAX_FIT_ZOOM);
  return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, ratio));
}
