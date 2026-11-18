// Thin client for the Vision Cart API. Same-origin only: no address, key or secret ever lives here.
export const PATHS = {
  listing: "/api/v1/generate-listing/",
  expand: "/api/v1/expand-description/",
  images: "/api/v1/generate-images/",
};

export class ApiError extends Error {
  constructor(code, message, requestId = null, status = 0) {
    super(message);
    this.code = code;
    this.requestId = requestId;
    this.status = status;
  }
}

// Platform-level failures (not produced by our own error envelope).
const STATUS_FALLBACK = {
  413: ["request_too_large", "The photos are too large to upload. Try fewer or smaller photos."],
  429: ["rate_limited", "Too many requests. Please wait a moment and try again."],
  504: ["request_timeout", "That took too long. Try fewer or smaller photos."],
};

async function send(path, init, timeoutMs, signal) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort("timeout"), timeoutMs);
  const onAbort = () => ctrl.abort("cancelled");
  signal?.addEventListener("abort", onAbort, { once: true });
  let res;
  try {
    res = await fetch(path, { ...init, signal: ctrl.signal });
  } catch {
    if (signal?.aborted) throw new ApiError("cancelled", "Cancelled.");
    if (ctrl.signal.reason === "timeout") throw new ApiError("request_timeout", "The service took too long to respond. Please try again.");
    throw new ApiError("network", "We can't reach the listing service right now. Check your connection and try again.");
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener("abort", onAbort);
  }
  let body = null;
  try { body = await res.json(); } catch { /* non-JSON body */ }
  if (!res.ok) {
    const err = body?.error;
    if (err?.code) throw new ApiError(String(err.code), String(err.message || "Request failed."), err.request_id ?? null, res.status);
    const [code, message] = STATUS_FALLBACK[res.status] || ["http_error", `The service returned an error (HTTP ${res.status}).`];
    throw new ApiError(code, message, null, res.status);
  }
  if (!body || typeof body !== "object") throw new ApiError("invalid_response", "The service returned an unexpected response.");
  return body;
}

const multipart = (blobs, extra = {}) => {
  const form = new FormData();
  blobs.forEach(({ blob, name }) => form.append("images", blob, name));
  Object.entries(extra).forEach(([k, v]) => v && form.append(k, v));
  return form;
};

export const generateListing = (blobs, signal) =>
  send(PATHS.listing, { method: "POST", body: multipart(blobs) }, 120_000, signal);

export async function expandDescription(listing, signal) {
  const keys = ["detected_item", "category", "condition_estimate", "suggested_title", "suggested_description", "extracted_features", "tags"];
  const payload = Object.fromEntries(keys.filter((k) => k in listing).map((k) => [k, listing[k]]));
  const body = await send(PATHS.expand, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
  }, 90_000, signal);
  if (typeof body.long_description !== "string" || !body.long_description.trim()) {
    throw new ApiError("invalid_response", "The service returned an empty description.");
  }
  return body.long_description;
}

export async function generateImages(blobs, detectedItem, signal) {
  const body = await send(PATHS.images, { method: "POST", body: multipart(blobs, { detected_item: detectedItem }) }, 150_000, signal);
  const images = Array.isArray(body.images) ? body.images.filter((i) => i && i.data_base64) : [];
  if (!images.length) throw new ApiError("invalid_response", "The service returned no images.");
  return { images, notice: typeof body.notice === "string" ? body.notice : "" };
}
