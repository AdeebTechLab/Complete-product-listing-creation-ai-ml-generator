"""Vision Cart web UI, served by the API itself so the whole product runs on Vercel."""

INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Vision Cart - AI listing generator</title>
<meta name="description" content="Snap a photo. Get a ready-to-post listing.">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Cdefs%3E%3ClinearGradient id='g' x1='0' y1='0' x2='1' y2='1'%3E%3Cstop offset='0' stop-color='%236D5DFB'/%3E%3Cstop offset='1' stop-color='%2314B8A6'/%3E%3C/linearGradient%3E%3C/defs%3E%3Crect width='64' height='64' rx='16' fill='url(%23g)'/%3E%3Cpath d='M13 17h7l4.5 23h21.5l4-16H22' fill='none' stroke='%23fff' stroke-width='3.6' stroke-linecap='round' stroke-linejoin='round'/%3E%3Ccircle cx='35' cy='31.5' r='5.4' fill='none' stroke='%23fff' stroke-width='2.8'/%3E%3Ccircle cx='35' cy='31.5' r='1.9' fill='%23fff'/%3E%3Ccircle cx='27.5' cy='49' r='3.3' fill='%23fff'/%3E%3Ccircle cx='43.5' cy='49' r='3.3' fill='%23fff'/%3E%3C/svg%3E">
<style>
  :root {
    --bg:#F6F7FB; --card:#FFFFFF; --ink:#14172B; --sub:#5B6178; --line:#E5E8F2;
    --primary:#6D5DFB; --teal:#14B8A6; --err:#C0392B; --soft:#F4F3FF;
    --grad:linear-gradient(135deg,#6D5DFB 0%,#14B8A6 100%);
    --shadow:0 1px 2px rgba(20,23,43,.04),0 8px 24px rgba(20,23,43,.06);
  }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#10111A; --card:#1A1C2A; --ink:#EEF0FF; --sub:#A0A5C2; --line:#2C2F45; --soft:#24233F; --shadow:0 8px 24px rgba(0,0,0,.35); }
  }
  * { box-sizing:border-box; }
  html { scroll-behavior:smooth; }
  body {
    margin:0; color:var(--ink); font-family:Inter,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; line-height:1.5;
    background: radial-gradient(1100px 480px at 85% -10%, rgba(109,93,251,.12), transparent 60%),
                radial-gradient(900px 400px at -10% 0%, rgba(20,184,166,.12), transparent 55%), var(--bg);
    min-height:100vh;
  }
  .wrap { max-width:980px; margin:0 auto; padding:20px 18px 56px; }
  header { display:flex; align-items:center; gap:12px; padding:6px 0 4px; }
  header svg { width:44px; height:44px; flex:none; filter:drop-shadow(0 6px 12px rgba(109,93,251,.35)); }
  .brand { font-size:1.55rem; font-weight:800; letter-spacing:-.02em; line-height:1.1; }
  .pill { margin-left:auto; font-size:.8rem; font-weight:600; color:var(--primary); background:var(--soft); border-radius:999px; padding:5px 12px; }
  .hero { text-align:center; padding:34px 0 22px; }
  .hero h1 { font-size:clamp(1.9rem,5vw,2.9rem); line-height:1.12; letter-spacing:-.03em; margin:0 0 12px; font-weight:800; }
  .grad { background:var(--grad); -webkit-background-clip:text; background-clip:text; color:transparent; }
  .hero p { max-width:560px; margin:0 auto; color:var(--sub); font-size:1.05rem; }
  .steps { display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin:22px 0; }
  .step { background:var(--card); border:1px solid var(--line); border-radius:16px; padding:14px 16px; box-shadow:var(--shadow); }
  .step b { display:block; margin-bottom:2px; }
  .step span.t { color:var(--sub); font-size:.9rem; }
  .num { width:26px; height:26px; border-radius:50%; background:var(--grad); color:#fff; font-weight:700; font-size:.85rem; display:grid; place-items:center; margin-bottom:8px; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:18px; padding:20px; box-shadow:var(--shadow); margin-bottom:18px; }
  .drop { display:block; text-align:center; border:2px dashed var(--line); border-radius:16px; padding:34px 16px; cursor:pointer; transition:.15s; }
  .drop:hover, .drop.over { border-color:var(--primary); background:var(--soft); }
  .drop svg { width:42px; height:42px; color:var(--primary); }
  .drop strong { display:block; margin-top:6px; font-size:1.05rem; }
  .drop small { color:var(--sub); }
  .drop input { display:none; }
  .thumbs { display:flex; flex-wrap:wrap; gap:12px; margin-top:16px; }
  .thumb { position:relative; width:92px; height:92px; }
  .thumb img { width:100%; height:100%; object-fit:cover; border-radius:12px; border:1px solid var(--line); }
  .thumb button { position:absolute; top:-8px; right:-8px; width:24px; height:24px; padding:0; border-radius:50%; background:var(--ink); color:var(--card); font-size:14px; line-height:1; box-shadow:none; }
  button { font:inherit; font-weight:600; border:0; border-radius:12px; padding:11px 20px; cursor:pointer; color:#fff; background:var(--grad); box-shadow:0 6px 16px rgba(109,93,251,.30); transition:transform .12s, opacity .12s; }
  button:hover:not(:disabled) { transform:translateY(-1px); }
  button:disabled { opacity:.5; cursor:not-allowed; box-shadow:none; }
  button.ghost { background:var(--card); color:var(--ink); border:1px solid var(--line); box-shadow:none; }
  button.small { padding:6px 12px; font-size:.82rem; }
  .row { display:flex; flex-wrap:wrap; gap:10px; align-items:center; margin-top:16px; }
  .bar { height:4px; border-radius:4px; background:var(--line); overflow:hidden; margin-top:14px; display:none; }
  .bar.on { display:block; }
  .bar i { display:block; height:100%; width:35%; background:var(--grad); border-radius:4px; animation:slide 1.1s ease-in-out infinite; }
  @keyframes slide { 0% { margin-left:-35%; } 100% { margin-left:100%; } }
  .status { color:var(--sub); font-size:.92rem; margin-top:10px; min-height:1.2em; }
  .err { color:var(--err); font-weight:600; margin-top:8px; }
  .res-head { display:flex; flex-wrap:wrap; gap:10px; align-items:center; justify-content:space-between; }
  .res-title { font-size:1.35rem; font-weight:800; letter-spacing:-.02em; margin:6px 0 0; }
  .grid { display:grid; grid-template-columns:1fr 1fr; gap:14px 28px; margin-top:12px; }
  .full { grid-column:1 / -1; }
  .lbl { display:flex; align-items:center; justify-content:space-between; gap:8px; font-size:.75rem; font-weight:700; text-transform:uppercase; letter-spacing:.07em; color:var(--sub); margin-bottom:4px; }
  .val { white-space:pre-wrap; }
  .badge { display:inline-block; border-radius:999px; padding:3px 12px; font-size:.85rem; font-weight:700; background:var(--soft); color:var(--primary); }
  .badge.good { background:rgba(20,184,166,.15); color:#0f9488; }
  .badge.warn { background:rgba(245,158,11,.16); color:#b86e00; }
  .chip { display:inline-block; background:var(--soft); color:var(--primary); border-radius:999px; padding:3px 12px; margin:3px 6px 0 0; font-size:.88rem; font-weight:500; }
  ul.feat { margin:0; padding-left:20px; }
  .long { margin-top:16px; padding:14px 16px; background:var(--soft); border-radius:14px; }
  .gen { display:grid; grid-template-columns:repeat(auto-fill,minmax(180px,1fr)); gap:12px; margin-top:16px; }
  .gen figure { margin:0; }
  .gen img { width:100%; aspect-ratio:1/1; object-fit:cover; border-radius:14px; border:1px solid var(--line); display:block; }
  .gen figcaption { font-size:.8rem; color:var(--sub); margin-top:4px; }
  footer { text-align:center; color:var(--sub); font-size:.85rem; margin-top:28px; }
  [hidden] { display:none !important; }
  @media (max-width:720px) { .steps { grid-template-columns:1fr; } .grid { grid-template-columns:1fr; } .pill { display:none; } }
</style>
</head>
<body>
<div class="wrap">

  <header>
    <svg viewBox="0 0 64 64" role="img" aria-label="Vision Cart logo">
      <defs><linearGradient id="vc-g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#6D5DFB"/><stop offset="1" stop-color="#14B8A6"/></linearGradient></defs>
      <rect width="64" height="64" rx="16" fill="url(#vc-g)"/>
      <path d="M13 17h7l4.5 23h21.5l4-16H22" fill="none" stroke="#fff" stroke-width="3.6" stroke-linecap="round" stroke-linejoin="round"/>
      <circle cx="35" cy="31.5" r="5.4" fill="none" stroke="#fff" stroke-width="2.8"/>
      <circle cx="35" cy="31.5" r="1.9" fill="#fff"/>
      <circle cx="27.5" cy="49" r="3.3" fill="#fff"/>
      <circle cx="43.5" cy="49" r="3.3" fill="#fff"/>
    </svg>
    <div class="brand">Vision Cart</div>
    <span class="pill">AI listing generator</span>
  </header>

  <section class="hero">
    <h1>Snap a photo.<br><span class="grad">Get a ready-to-post listing.</span></h1>
    <p>Upload your product photos and let AI write the title, description and tags, plus extra visuals.</p>
  </section>

  <section class="steps">
    <div class="step"><div class="num">1</div><b>Upload</b><span class="t">Add up to 4 photos of your item.</span></div>
    <div class="step"><div class="num">2</div><b>Generate</b><span class="t">AI detects the item and writes your listing.</span></div>
    <div class="step"><div class="num">3</div><b>Copy &amp; post</b><span class="t">Paste it into your marketplace of choice.</span></div>
  </section>

  <div class="card">
    <label id="drop" class="drop" for="files">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/><path d="M12 4v12"/><path d="M7 9l5-5 5 5"/></svg>
      <strong>Drop photos here or click to browse</strong>
      <small>JPG, PNG or WEBP &middot; up to 4 photos &middot; large photos are resized automatically</small>
      <input id="files" type="file" accept="image/jpeg,image/png,image/webp,.jfif" multiple>
    </label>
    <div id="thumbs" class="thumbs"></div>
    <div class="row">
      <button id="go" disabled>Generate listing</button>
      <button id="clear" class="ghost" hidden>Clear photos</button>
    </div>
    <div id="bar" class="bar"><i></i></div>
    <div id="status" class="status"></div>
    <div id="error" class="err"></div>
  </div>

  <div id="result" class="card" hidden>
    <div class="res-head">
      <div>
        <span id="r_cond" class="badge"></span>
        <h2 id="r_title" class="res-title"></h2>
      </div>
      <button id="copy_all" class="ghost small">Copy full listing</button>
    </div>
    <div class="grid">
      <div><div class="lbl">Detected item</div><div id="r_item" class="val"></div></div>
      <div><div class="lbl">Category</div><div id="r_cat" class="val"></div></div>
      <div class="full"><div class="lbl">Description <button id="copy_desc" class="ghost small">Copy</button></div><div id="r_desc" class="val"></div></div>
      <div><div class="lbl">Key features</div><ul id="r_feat" class="feat"></ul></div>
      <div><div class="lbl">Tags <button id="copy_tags" class="ghost small">Copy</button></div><div id="r_tags"></div></div>
    </div>
    <div class="row">
      <button id="expand" class="ghost">Write long description</button>
      <button id="imgs" class="ghost">Generate AI photos</button>
    </div>
    <div id="long_box" class="long" hidden>
      <div class="lbl">Long description <button id="copy_long" class="ghost small">Copy</button></div>
      <div id="long" class="val"></div>
    </div>
    <div id="gen" class="gen"></div>
  </div>

  <footer>Vision Cart &middot; AI-generated content, please review before posting.</footer>
</div>

<script>
const MAX_FILES = 4, MAX_BYTES = 1024 * 1024, MAX_SIDE = 1600;
const $ = id => document.getElementById(id);
let items = [];      // {blob, url}
let listing = null;
let busy = false;

function refresh() {
  $("go").disabled = busy || !items.length;
  $("expand").disabled = busy; $("imgs").disabled = busy;
  $("clear").hidden = !items.length;
  $("bar").classList.toggle("on", busy);
}
function setBusy(b, msg) { busy = b; $("status").textContent = msg || ""; refresh(); }
function showError(m) { $("error").textContent = m || ""; }

function renderThumbs() {
  $("thumbs").innerHTML = "";
  items.forEach((it, i) => {
    const d = document.createElement("div"); d.className = "thumb";
    const im = document.createElement("img"); im.src = it.url; im.alt = "Product photo " + (i + 1);
    const x = document.createElement("button"); x.type = "button"; x.textContent = "\u00d7"; x.title = "Remove";
    x.onclick = () => { URL.revokeObjectURL(it.url); items.splice(i, 1); renderThumbs(); refresh(); };
    d.append(im, x); $("thumbs").appendChild(d);
  });
}

async function shrink(file) {
  if (file.size <= MAX_BYTES && /jpe?g|webp/.test(file.type)) return file;
  const bmp = await createImageBitmap(file);
  const scale = Math.min(1, MAX_SIDE / Math.max(bmp.width, bmp.height));
  const c = document.createElement("canvas");
  c.width = Math.round(bmp.width * scale); c.height = Math.round(bmp.height * scale);
  c.getContext("2d").drawImage(bmp, 0, 0, c.width, c.height);
  for (let q = 0.85; q >= 0.4; q -= 0.15) {
    const b = await new Promise(r => c.toBlob(r, "image/jpeg", q));
    if (b && b.size <= MAX_BYTES) return new File([b], file.name.replace(/\.\w+$/, "") + ".jpg", { type: "image/jpeg" });
  }
  throw new Error("Could not shrink " + file.name + " below 1 MB. Try a smaller photo.");
}

async function addFiles(fileList) {
  showError("");
  let list = Array.from(fileList).filter(f => /^image\//.test(f.type) || /\.jfif$/i.test(f.name));
  if (!list.length) { showError("Please choose JPG, PNG or WEBP photos."); return; }
  const room = MAX_FILES - items.length;
  if (list.length > room) { showError("Maximum " + MAX_FILES + " photos. Extra photos were skipped."); list = list.slice(0, Math.max(room, 0)); }
  try {
    setBusy(true, "Preparing photos...");
    for (const f of list) { const b = await shrink(f); items.push({ blob: b, url: URL.createObjectURL(b) }); }
  } catch (err) { showError(err.message); }
  renderThumbs(); setBusy(false);
}

$("files").addEventListener("change", e => { addFiles(e.target.files); e.target.value = ""; });
["dragenter", "dragover"].forEach(ev => $("drop").addEventListener(ev, e => { e.preventDefault(); $("drop").classList.add("over"); }));
["dragleave", "drop"].forEach(ev => $("drop").addEventListener(ev, e => { e.preventDefault(); $("drop").classList.remove("over"); }));
$("drop").addEventListener("drop", e => addFiles(e.dataTransfer.files));
$("clear").onclick = () => { items.forEach(i => URL.revokeObjectURL(i.url)); items = []; renderThumbs(); refresh(); showError(""); };

async function call(path, opts) {
  let res;
  try { res = await fetch(path, opts); } catch (e) { throw new Error("Network problem. Please try again."); }
  let body = null; try { body = await res.json(); } catch (e) {}
  if (!res.ok) throw new Error((body && body.error && body.error.message) || ("Request failed (HTTP " + res.status + ")."));
  return body;
}
function form() { const fd = new FormData(); items.forEach(i => fd.append("images", i.blob, i.blob.name)); return fd; }

function condClass(c) { return /new/i.test(c) ? "good" : /unable/i.test(c) ? "" : "warn"; }

$("go").onclick = async () => {
  showError(""); $("result").hidden = true; $("long_box").hidden = true; $("gen").innerHTML = "";
  setBusy(true, "Analysing your photos (10-30 seconds)...");
  try {
    listing = await call("/api/v1/generate-listing/", { method: "POST", body: form() });
    $("r_title").textContent = listing.suggested_title;
    $("r_item").textContent = listing.detected_item;
    $("r_cat").textContent = listing.category;
    $("r_cond").textContent = listing.condition_estimate; $("r_cond").className = "badge " + condClass(listing.condition_estimate);
    $("r_desc").textContent = listing.suggested_description;
    $("r_feat").innerHTML = "";
    (listing.extracted_features || []).forEach(t => { const li = document.createElement("li"); li.textContent = t; $("r_feat").appendChild(li); });
    $("r_tags").innerHTML = "";
    (listing.tags || []).forEach(t => { const s = document.createElement("span"); s.className = "chip"; s.textContent = "#" + t; $("r_tags").appendChild(s); });
    $("result").hidden = false; $("result").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (err) { showError(err.message); }
  setBusy(false);
};

$("expand").onclick = async () => {
  showError(""); setBusy(true, "Writing the long description...");
  try {
    const keys = ["detected_item","category","condition_estimate","suggested_title","suggested_description","extracted_features","tags"];
    const payload = {}; keys.forEach(k => { if (k in listing) payload[k] = listing[k]; });
    const body = await call("/api/v1/expand-description/", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    $("long").textContent = body.long_description; $("long_box").hidden = false;
  } catch (err) { showError(err.message); }
  setBusy(false);
};

$("imgs").onclick = async () => {
  showError(""); $("gen").innerHTML = ""; setBusy(true, "Generating AI photos (up to a minute)...");
  try {
    const fd = form(); if (listing && listing.detected_item) fd.append("detected_item", listing.detected_item);
    const body = await call("/api/v1/generate-images/", { method: "POST", body: fd });
    (body.images || []).forEach(i => {
      const f = document.createElement("figure"), im = document.createElement("img"), cap = document.createElement("figcaption");
      im.src = "data:" + (i.mime_type || "image/png") + ";base64," + i.data_base64; im.alt = i.label || "AI generated photo";
      cap.textContent = (i.label ? i.label + " " : "") + "(AI generated)"; f.append(im, cap); $("gen").appendChild(f);
    });
  } catch (err) { showError(err.message); }
  setBusy(false);
};

async function copy(text, btn) {
  try { await navigator.clipboard.writeText(text); const o = btn.textContent; btn.textContent = "Copied"; setTimeout(() => btn.textContent = o, 1400); }
  catch (e) { showError("Copy failed. Please select the text manually."); }
}
const tagsText = () => (listing.tags || []).map(t => "#" + t).join(" ");
$("copy_desc").onclick = e => copy(listing.suggested_description, e.target);
$("copy_tags").onclick = e => copy(tagsText(), e.target);
$("copy_long").onclick = e => copy($("long").textContent, e.target);
$("copy_all").onclick = e => copy(
  listing.suggested_title + "\n\n" + listing.suggested_description + "\n\n" +
  (listing.extracted_features || []).map(f => "- " + f).join("\n") + "\n\n" + tagsText() +
  ($("long").textContent ? "\n\n" + $("long").textContent : ""), e.target);
refresh();
</script>
</body>
</html>
"""
