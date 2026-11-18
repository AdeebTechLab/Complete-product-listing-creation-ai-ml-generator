// Browser-side photo preparation. Vercel functions reject request bodies over 4.5 MB, so photos
// are resized and re-encoded as JPEG here (EXIF rotation applied) before they are uploaded.
export const MAX_FILES = 6;
export const ACCEPTED = ["image/jpeg", "image/png", "image/webp"];
export const MAX_SOURCE_MB = 25; // what we accept from the user; the upload itself is far smaller
export const UPLOAD_BUDGET_BYTES = 3.8 * 1024 * 1024; // safely under the 4.5 MB platform limit

// Progressively stronger compression until everything fits the budget.
const PROFILES = [
  { edge: 1568, quality: 0.85 },
  { edge: 1280, quality: 0.75 },
  { edge: 1024, quality: 0.65 },
  { edge: 800, quality: 0.55 },
];

export function validateFiles(files) {
  if (files.length > MAX_FILES) return `Too many photos: ${files.length} selected, the maximum is ${MAX_FILES}.`;
  const bad = files.find((f) => !ACCEPTED.includes(f.type));
  if (bad) return `"${bad.name}" isn't a JPG, PNG or WEBP photo.`;
  const big = files.find((f) => f.size > MAX_SOURCE_MB * 1024 * 1024);
  if (big) return `"${big.name}" is larger than ${MAX_SOURCE_MB} MB. Please choose a smaller file.`;
  return null;
}

async function toJpeg(file, { edge, quality }) {
  let bitmap;
  try {
    bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });
  } catch {
    throw new Error(`"${file.name}" couldn't be read. It may be corrupted.`);
  }
  const scale = Math.min(1, edge / Math.max(bitmap.width, bitmap.height));
  const w = Math.max(1, Math.round(bitmap.width * scale));
  const h = Math.max(1, Math.round(bitmap.height * scale));
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#fff"; // flatten transparency like the server does
  ctx.fillRect(0, 0, w, h);
  ctx.drawImage(bitmap, 0, 0, w, h);
  bitmap.close?.();
  const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", quality));
  if (!blob) throw new Error(`"${file.name}" couldn't be prepared for upload.`);
  return blob;
}

/** Returns [{ blob, name }] whose total size fits UPLOAD_BUDGET_BYTES. */
export async function prepareForUpload(files) {
  for (const profile of PROFILES) {
    const blobs = [];
    for (const file of files) {
      blobs.push({ blob: await toJpeg(file, profile), name: file.name.replace(/\.[^.]+$/, "") + ".jpg" });
    }
    if (blobs.reduce((n, b) => n + b.blob.size, 0) <= UPLOAD_BUDGET_BYTES) return blobs;
  }
  throw new Error("These photos are too large to upload together. Try fewer photos.");
}

export async function makeThumb(file, edge = 480) {
  return URL.createObjectURL(await toJpeg(file, { edge, quality: 0.8 }));
}
