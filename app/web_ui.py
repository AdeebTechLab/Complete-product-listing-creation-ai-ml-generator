"""Single-page web UI served by the API itself, so the whole product runs on Vercel."""

INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Marketplace Listing</title>
<style>
  :root { --bg:#F6F7FB; --card:#fff; --text:#14172B; --muted:#6b7089; --brand:#6D5DFB; --line:#e4e6f0; --err:#c0392b; }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#12131c; --card:#1b1d2b; --text:#eef0ff; --muted:#9a9fbd; --line:#2c2f44; }
  }
  * { box-sizing:border-box; }
  body { margin:0; font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif; background:var(--bg); color:var(--text); }
  main { max-width:760px; margin:0 auto; padding:24px 16px 64px; }
  h1 { font-size:1.6rem; margin:8px 0 4px; }
  p.sub { color:var(--muted); margin:0 0 20px; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:18px; margin-bottom:16px; }
  button { background:var(--brand); color:#fff; border:0; border-radius:10px; padding:11px 18px; font-size:1rem; cursor:pointer; }
  button.secondary { background:transparent; color:var(--brand); border:1px solid var(--brand); }
  button:disabled { opacity:.5; cursor:not-allowed; }
  input[type=file] { width:100%; padding:14px; border:2px dashed var(--line); border-radius:10px; background:transparent; color:var(--text); }
  .thumbs { display:flex; flex-wrap:wrap; gap:8px; margin:12px 0; }
  .thumbs img, .gen img { width:96px; height:96px; object-fit:cover; border-radius:8px; border:1px solid var(--line); }
  .gen img { width:180px; height:180px; }
  .row { display:flex; gap:10px; flex-wrap:wrap; margin-top:10px; }
  .label { font-size:.8rem; text-transform:uppercase; letter-spacing:.05em; color:var(--muted); margin-top:14px; }
  .value { margin:4px 0; white-space:pre-wrap; }
  .chip { display:inline-block; background:rgba(109,93,251,.12); color:var(--brand); border-radius:999px; padding:3px 11px; margin:3px 4px 0 0; font-size:.88rem; }
  .err { color:var(--err); margin-top:10px; }
  .note { color:var(--muted); font-size:.85rem; margin-top:8px; }
  ul { margin:4px 0; padding-left:20px; }
</style>
</head>
<body>
<main>
  <h1>AI Marketplace Listing</h1>
  <p class="sub">Upload product photos and get a ready-to-post title, description and tags.</p>

  <div class="card">
    <input id="files" type="file" accept="image/jpeg,image/png,image/webp" multiple>
    <div class="note">Up to 4 photos (JPG, PNG or WEBP). Large photos are resized automatically.</div>
    <div id="thumbs" class="thumbs"></div>
    <div class="row"><button id="go" disabled>Generate listing</button></div>
    <div id="status" class="note"></div>
    <div id="error" class="err"></div>
  </div>

  <div id="result" class="card" hidden>
    <div class="label">Title</div><div id="r_title" class="value"></div>
    <div class="label">Detected item</div><div id="r_item" class="value"></div>
    <div class="label">Category</div><div id="r_cat" class="value"></div>
    <div class="label">Condition</div><div id="r_cond" class="value"></div>
    <div class="label">Description</div><div id="r_desc" class="value"></div>
    <div class="label">Features</div><ul id="r_feat"></ul>
    <div class="label">Tags</div><div id="r_tags"></div>
    <div class="row">
      <button id="copy" class="secondary">Copy listing</button>
      <button id="expand" class="secondary">Write long description</button>
      <button id="imgs" class="secondary">Generate AI photos</button>
    </div>
    <div id="long" class="value" style="margin-top:14px"></div>
    <div id="gen" class="gen row"></div>
  </div>
</main>

<script>
const MAX_FILES = 4, MAX_BYTES = 1024 * 1024, MAX_SIDE = 1600;
const $ = id => document.getElementById(id);
let blobs = [], listing = null;

function setBusy(busy, msg) {
  ["go", "expand", "imgs"].forEach(id => { $(id).disabled = busy || (id === "go" && !blobs.length); });
  $("status").textContent = msg || "";
}
function showError(msg) { $("error").textContent = msg || ""; }

async function shrink(file) {
  if (file.size <= MAX_BYTES && /jpe?g|webp/.test(file.type)) return file;
  const bmp = await createImageBitmap(file);
  const scale = Math.min(1, MAX_SIDE / Math.max(bmp.width, bmp.height));
  const c = document.createElement("canvas");
  c.width = Math.round(bmp.width * scale); c.height = Math.round(bmp.height * scale);
  c.getContext("2d").drawImage(bmp, 0, 0, c.width, c.height);
  for (let q = 0.85; q >= 0.4; q -= 0.15) {
    const b = await new Promise(r => c.toBlob(r, "image/jpeg", q));
    if (b.size <= MAX_BYTES) return new File([b], file.name.replace(/\.\w+$/, "") + ".jpg", { type: "image/jpeg" });
  }
  throw new Error("Could not shrink " + file.name + " below 1 MB. Try a smaller photo.");
}

$("files").addEventListener("change", async e => {
  showError(""); blobs = []; $("thumbs").innerHTML = "";
  let list = Array.from(e.target.files);
  if (list.length > MAX_FILES) { showError("Only the first " + MAX_FILES + " photos are used."); list = list.slice(0, MAX_FILES); }
  try {
    setBusy(true, "Preparing photos...");
    for (const f of list) {
      const s = await shrink(f); blobs.push(s);
      const img = document.createElement("img"); img.src = URL.createObjectURL(s); $("thumbs").appendChild(img);
    }
  } catch (err) { showError(err.message); blobs = []; }
  setBusy(false);
});

async function call(path, opts) {
  let res;
  try { res = await fetch(path, opts); }
  catch (e) { throw new Error("Network problem. Please try again."); }
  let body = null;
  try { body = await res.json(); } catch (e) {}
  if (!res.ok) throw new Error((body && body.error && body.error.message) || ("Request failed (HTTP " + res.status + ")."));
  return body;
}
function form() { const fd = new FormData(); blobs.forEach(b => fd.append("images", b, b.name)); return fd; }

$("go").addEventListener("click", async () => {
  showError(""); $("result").hidden = true; $("long").textContent = ""; $("gen").innerHTML = "";
  setBusy(true, "Analysing your photos (10-30 seconds)...");
  try {
    listing = await call("/api/v1/generate-listing/", { method: "POST", body: form() });
    $("r_title").textContent = listing.suggested_title;
    $("r_item").textContent = listing.detected_item;
    $("r_cat").textContent = listing.category;
    $("r_cond").textContent = listing.condition_estimate;
    $("r_desc").textContent = listing.suggested_description;
    $("r_feat").innerHTML = ""; (listing.extracted_features || []).forEach(t => { const li = document.createElement("li"); li.textContent = t; $("r_feat").appendChild(li); });
    $("r_tags").innerHTML = ""; (listing.tags || []).forEach(t => { const s = document.createElement("span"); s.className = "chip"; s.textContent = "#" + t; $("r_tags").appendChild(s); });
    $("result").hidden = false;
  } catch (err) { showError(err.message); }
  setBusy(false);
});

$("expand").addEventListener("click", async () => {
  showError(""); setBusy(true, "Writing the long description...");
  try {
    const keys = ["detected_item","category","condition_estimate","suggested_title","suggested_description","extracted_features","tags"];
    const payload = {}; keys.forEach(k => { if (k in listing) payload[k] = listing[k]; });
    const body = await call("/api/v1/expand-description/", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    $("long").textContent = body.long_description;
  } catch (err) { showError(err.message); }
  setBusy(false);
});

$("imgs").addEventListener("click", async () => {
  showError(""); $("gen").innerHTML = ""; setBusy(true, "Generating AI photos (up to a minute)...");
  try {
    const fd = form(); if (listing && listing.detected_item) fd.append("detected_item", listing.detected_item);
    const body = await call("/api/v1/generate-images/", { method: "POST", body: fd });
    (body.images || []).forEach(i => { const im = document.createElement("img"); im.src = "data:" + (i.mime_type || "image/png") + ";base64," + i.data_base64; im.alt = i.label || "AI generated"; im.title = (i.label || "") + " (AI generated)"; $("gen").appendChild(im); });
  } catch (err) { showError(err.message); }
  setBusy(false);
});

$("copy").addEventListener("click", async () => {
  if (!listing) return;
  const text = listing.suggested_title + "\n\n" + listing.suggested_description + "\n\n" + (listing.extracted_features || []).map(f => "- " + f).join("\n") + "\n\n" + (listing.tags || []).map(t => "#" + t).join(" ") + ($("long").textContent ? "\n\n" + $("long").textContent : "");
  try { await navigator.clipboard.writeText(text); $("status").textContent = "Copied."; } catch (e) { showError("Copy failed. Select the text manually."); }
});
</script>
</body>
</html>
"""
