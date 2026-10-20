/** User dismissal is control flow, not a printer failure. */
export class UserCancelledError extends Error {
  constructor(message = "Action cancelled") {
    super(message);
    this.name = "UserCancelledError";
  }
}

export function isUserCancelled(error: unknown): boolean {
  return error instanceof UserCancelledError || (error instanceof DOMException && error.name === "AbortError");
}
