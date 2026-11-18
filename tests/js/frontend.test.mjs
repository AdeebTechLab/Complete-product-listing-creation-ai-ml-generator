import assert from "node:assert";
import { generateListing, expandDescription, generateImages, ApiError } from "../../public/assets/api.js";
import { exportText, imageSrc } from "../../public/assets/text.js";
const blobs = [{ blob: new Blob(["x"]), name: "a.jpg" }];
const mock = (status, body, raw) => { globalThis.fetch = async () => ({ ok: status < 400, status, json: async () => { if (raw) throw new Error("no json"); return body; } }); };

mock(200, { suggested_title: "T" });
assert.equal((await generateListing(blobs)).suggested_title, "T");

mock(422, { error: { code: "no_product_detected", message: "none", request_id: "r1" } });
await assert.rejects(generateListing(blobs), (e) => e instanceof ApiError && e.code === "no_product_detected" && e.requestId === "r1");

mock(413, null, true);
await assert.rejects(generateListing(blobs), (e) => e.code === "request_too_large");
mock(504, null, true);
await assert.rejects(generateListing(blobs), (e) => e.code === "request_timeout");

mock(200, { long_description: "  " });
await assert.rejects(expandDescription({ detected_item: "x" }), (e) => e.code === "invalid_response");
mock(200, { images: [{ data_base64: "AAA", label: "L" }, { label: "bad" }], notice: "n" });
const r = await generateImages(blobs, "phone");
assert.equal(r.images.length, 1);

globalThis.fetch = async () => { throw new TypeError("offline"); };
await assert.rejects(generateListing(blobs), (e) => e.code === "network");

assert.equal(exportText(" Title ", " Desc ", ["a b", "c"]), "Title\n\nDesc\n\n#ab #c\n");
assert.ok(imageSrc({ mime_type: "text/html", data_base64: "AA" }).startsWith("data:image/jpeg"));
console.log("JS module tests passed");
