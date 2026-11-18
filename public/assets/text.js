// Pure helpers (no DOM): easy to reason about and to test.
export const ERROR_HINTS = {
  invalid_image: "Check that each file is a real JPG, PNG or WEBP photo and not corrupted.",
  invalid_request: "Upload at least one photo.",
  image_too_large: "Use a smaller photo.",
  request_too_large: "Use fewer or smaller photos.",
  no_product_detected: "Upload a clearer photo where one product is the main subject.",
  ai_output_invalid: "The AI answer didn't pass our quality checks. Try again or use a clearer photo.",
  vision_rate_limited: "We're getting a lot of requests. Wait about 30 seconds and try again.",
  rate_limited: "You're going a bit fast. Wait a few seconds and try again.",
  vision_timeout: "The AI was slow. Try again.",
  request_timeout: "That took too long. Try fewer or smaller photos.",
  vision_unavailable: "The AI service is temporarily unavailable. Try again shortly.",
  vision_misconfigured: "The service is being set up. Please try again later.",
  feature_disabled: "This feature is switched off.",
};

export const CONDITION_TONE = {
  "Brand New": "good", "Like New": "good", "Used - Good Condition": "ok",
  "Used - Fair Condition": "warn", "Poor Condition": "bad", "Unable to Determine": "muted",
};

export function exportText(title, description, tags) {
  const lines = [title.trim(), "", description.trim()];
  if (tags?.length) lines.push("", tags.map((t) => "#" + t.replace(/\s+/g, "")).join(" "));
  return lines.join("\n").trim() + "\n";
}

export function imageSrc(image) {
  const mime = ["image/jpeg", "image/png", "image/webp"].includes(image.mime_type) ? image.mime_type : "image/jpeg";
  return `data:${mime};base64,${image.data_base64}`;
}
