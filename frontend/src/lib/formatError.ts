/** Normalize thrown values for UI / JSON — avoids "[object Event]" and non-string API errors. */

function isDomEvent(err: unknown): boolean {
  if (err == null || typeof err !== "object") return false;
  const tag = Object.prototype.toString.call(err);
  return (
    tag === "[object Event]" ||
    tag === "[object PointerEvent]" ||
    tag === "[object KeyboardEvent]" ||
    tag === "[object MouseEvent]" ||
    tag === "[object TouchEvent]" ||
    tag === "[object FocusEvent]" ||
    tag === "[object SubmitEvent]"
  );
}

export function formatThrown(err: unknown): string {
  if (err == null) return "Unknown error.";
  if (typeof err === "string") return err;
  if (err instanceof Error) {
    const m = err.message?.trim();
    return m || "Unknown error.";
  }
  if (typeof DOMException !== "undefined" && err instanceof DOMException) {
    return err.message || "Request was interrupted.";
  }
  if (isDomEvent(err)) {
    return "Unexpected browser event; please try again.";
  }
  if (typeof err === "object" && err !== null && "message" in err) {
    const m = (err as { message?: unknown }).message;
    if (typeof m === "string" && m.trim()) return m;
  }
  return "Something went wrong. Try again.";
}

export function isAbortError(err: unknown): boolean {
  if (err == null) return false;
  if (typeof DOMException !== "undefined" && err instanceof DOMException) {
    return err.name === "AbortError";
  }
  return err instanceof Error && err.name === "AbortError";
}
