// Vision Cart UI. All model and user text is inserted as plain text nodes, never as markup.
import { ApiError, expandDescription, generateImages, generateListing } from "./api.js";
import { MAX_FILES, makeThumb, prepareForUpload, validateFiles } from "./images.js";
import { CONDITION_TONE, ERROR_HINTS, exportText, imageSrc } from "./text.js";

const $ = (id) => document.getElementById(id);
const el = (tag, cls, text) => {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text != null) node.textContent = text;
  return node;
};
const STEPS = [["listing", "Reading your photos"], ["expand", "Writing the full description"], ["images", "Creating related visuals"]];
const AI_NOTICE = "AI-generated illustrations based on your photo. They are not photos of the actual item, so don't present them to buyers as real photos.";

const state = {
  files: [], // [{ id, file, thumb }]
  prepared: null, // compressed upload blobs, cached per file set
  runId: 0,
  abort: null,
  busy: false,
  steps: {}, // listing|expand|images -> ok|error|skipped|active
  listing: null,
  long: null,
  images: null,
  aiNotice: AI_NOTICE,
};

const opts = () => ({ auto: $("opt-auto").checked, expand: $("opt-expand").checked, images: $("opt-images").checked });

// ------------------------------------------------------------------ files
async function addFiles(list) {
  const incoming = [...list];
  const all = [...state.files.map((f) => f.file), ...incoming];
  const problem = validateFiles(all);
  showUploadError(problem);
  if (problem) return;
  for (const file of incoming) {
    try {
      state.files.push({ id: crypto.randomUUID(), file, thumb: await makeThumb(file) });
    } catch (e) {
      showUploadError(e.message);
    }
  }
  filesChanged();
}

function removeFile(id) {
  const item = state.files.find((f) => f.id === id);
  if (item) URL.revokeObjectURL(item.thumb);
  state.files = state.files.filter((f) => f.id !== id);
  showUploadError(null);
  filesChanged();
}

function showUploadError(message) {
  const box = $("upload-error");
  box.textContent = message || "";
  box.hidden = !message;
}

function filesChanged() {
  cancelRun();
  state.prepared = null;
  resetResults();
  renderPicked();
  $("create-btn").disabled = state.files.length === 0;
  if (state.files.length && opts().auto) run();
  else render();
}

function renderPicked() {
  const list = $("picked");
  list.replaceChildren(
    ...state.files.map(({ id, file, thumb }) => {
      const li = el("li", "thumb");
      const img = el("img");
      img.src = thumb;
      img.alt = file.name;
      const btn = el("button", null, "×");
      btn.type = "button";
      btn.setAttribute("aria-label", `Remove ${file.name}`);
      btn.addEventListener("click", () => removeFile(id));
      li.append(img, btn);
      return li;
    }),
  );
}

// --------------------------------------------------------------- pipeline
function resetResults() {
  state.steps = {};
  state.listing = null;
  state.long = null;
  state.images = null;
  state.error = null;
  state.expandError = null;
  state.imagesError = null;
}

function cancelRun() {
  state.runId += 1;
  state.abort?.abort();
  state.abort = null;
  state.busy = false;
}

async function ensurePrepared() {
  if (!state.prepared) state.prepared = await prepareForUpload(state.files.map((f) => f.file));
  return state.prepared;
}

async function run() {
  if (!state.files.length) return;
  cancelRun();
  resetResults();
  const id = state.runId;
  const ctrl = new AbortController();
  state.abort = ctrl;
  state.busy = true;
  const live = () => id === state.runId;

  state.steps.listing = "active";
  render();
  try {
    const blobs = await ensurePrepared();
    const listing = await generateListing(blobs, ctrl.signal);
    if (!live()) return;
    state.listing = listing;
    state.steps.listing = "ok";
  } catch (e) {
    if (!live() || e.code === "cancelled") return;
    state.steps.listing = "error";
    state.error = e instanceof ApiError ? e : { message: e.message, code: "invalid_image" };
    state.busy = false;
    render();
    return;
  }
  render();

  if (opts().expand) await writeFull(id, ctrl.signal);
  else state.steps.expand = "skipped";
  if (!live()) return;
  if (opts().images) await makeImages(id, ctrl.signal);
  else state.steps.images = "skipped";
  if (!live()) return;
  state.busy = false;
  render();
}

async function writeFull(id = state.runId, signal) {
  const own = !signal;
  if (own) {
    state.abort?.abort();
    state.abort = new AbortController();
    signal = state.abort.signal;
  }
  state.steps.expand = "active";
  state.expandError = null;
  render();
  try {
    state.long = await expandDescription(currentListing(), signal);
    state.steps.expand = "ok";
  } catch (e) {
    if (id !== state.runId || e.code === "cancelled") return;
    state.expandError = e.message;
    state.steps.expand = "error";
  }
  if (id === state.runId) render();
}

async function makeImages(id = state.runId, signal) {
  if (!signal) {
    state.abort = new AbortController();
    signal = state.abort.signal;
  }
  state.steps.images = "active";
  state.imagesError = null;
  state.images = null;
  render();
  try {
    const blobs = await ensurePrepared();
    const { images, notice } = await generateImages(blobs, state.listing?.detected_item, signal);
    if (id !== state.runId) return;
    state.images = images;
    state.aiNotice = notice || AI_NOTICE;
    state.steps.images = "ok";
  } catch (e) {
    if (id !== state.runId || e.code === "cancelled") return;
    state.imagesError = "Related visuals aren't available right now. Your listing is unaffected. " + e.message;
    state.steps.images = "error";
  }
  if (id === state.runId) render();
}

// ----------------------------------------------------------------- render
function currentListing() {
  return { ...state.listing, suggested_title: $("title").value.trim() || state.listing.suggested_title, suggested_description: $("short").value.trim() || state.listing.suggested_description };
}

function tile(item, ai) {
  const fig = el("figure", "tile");
  const img = el("img");
  img.src = item.src;
  img.alt = item.label;
  fig.append(img, el("figcaption", null, item.label));
  if (ai) fig.append(el("span", "ai-badge", "AI"));
  return fig;
}

function renderStepper() {
  const box = $("stepper");
  const any = Object.keys(state.steps).length > 0;
  box.hidden = !any;
  box.replaceChildren(
    ...STEPS.map(([key, label]) => {
      const s = state.steps[key] || "pending";
      const step = el("div", `step step-${s}`);
      step.append(el("span", "dot", { ok: "✓", error: "!", skipped: "–" }[s] || ""), document.createTextNode(label));
      return step;
    }),
  );
}

function render() {
  renderStepper();
  const loadingListing = state.steps.listing === "active";
  $("hero").hidden = loadingListing || !!state.listing || !!state.error;
  $("loading").hidden = !loadingListing;
  $("error-box").hidden = !state.error;
  $("results").hidden = !state.listing;
  $("create-btn").textContent = state.error ? "Try again" : state.listing ? "Regenerate listing" : "Create listing";
  $("create-btn").disabled = state.files.length === 0 || state.busy;

  if (loadingListing) {
    $("loading-gallery").replaceChildren(
      ...state.files.map((f, i) => tile({ src: f.thumb, label: `Your photo ${i + 1}` }, false)),
      ...(opts().images ? [1, 2, 3].map(() => Object.assign(el("div", "tile skeleton"), { ariaHidden: "true" })) : []),
    );
  }
  if (state.error) renderError(state.error);
  if (state.listing) renderListing();
}

function renderError(err) {
  $("error-msg").textContent = err.message;
  $("error-hint").textContent = ERROR_HINTS[err.code] || "";
  $("error-ref").textContent = err.requestId ? `Reference: ${err.requestId} (quote this if you contact support)` : "";
}

function renderListing() {
  const l = state.listing;
  const badges = $("badges");
  const cat = el("span", "badge b-primary", l.category);
  const cond = el("span", `badge b-${CONDITION_TONE[l.condition_estimate] || "muted"}`, l.condition_estimate);
  badges.replaceChildren(cat, cond);
  $("detected").textContent = l.detected_item;
  $("cond-note").hidden = l.condition_estimate !== "Unable to Determine";

  // Only seed editable fields when a new listing arrives, so edits are never overwritten.
  if ($("title").dataset.seed !== String(l.__seed ?? (l.__seed = crypto.randomUUID()))) {
    $("title").value = l.suggested_title;
    $("short").value = l.suggested_description;
    $("title").dataset.seed = l.__seed;
    updateTitleCount();
  }

  $("features").replaceChildren(...(l.extracted_features?.length ? l.extracted_features.map((f) => el("li", null, f)) : [el("li", null, "No features were extracted.")]));
  $("tags").replaceChildren(...l.tags.map((t) => el("span", "chip", t)));

  // gallery: user photos + AI visuals
  const gallery = $("gallery");
  const nodes = state.files.map((f, i) => tile({ src: f.thumb, label: `Your photo ${i + 1}` }, false));
  (state.images || []).forEach((img) => nodes.push(tile({ src: imageSrc(img), label: img.label || "AI visual" }, true)));
  if (state.steps.images === "active") for (let i = 0; i < 3; i++) nodes.push(el("div", "tile skeleton"));
  gallery.replaceChildren(...nodes);
  $("ai-note").hidden = !state.images;
  $("ai-note").textContent = state.aiNotice;
  $("images-error").hidden = !state.imagesError;
  $("images-error").textContent = state.imagesError || "";
  $("images-btn").hidden = !(state.images || state.imagesError) || state.steps.images === "active";
  $("images-btn").textContent = state.imagesError ? "Try the visuals again" : "Regenerate visuals";

  // full description
  const expanding = state.steps.expand === "active";
  $("full-loading").hidden = !expanding;
  $("full-error").hidden = !state.expandError || expanding;
  $("full-error").textContent = state.expandError || "";
  $("full-empty").hidden = !!state.long || expanding;
  const full = $("full");
  if (state.long && full.dataset.seed !== state.long) {
    full.value = state.long;
    full.dataset.seed = state.long;
  }
  full.hidden = !state.long || expanding;
  $("full-btn").hidden = expanding;
  $("full-btn").textContent = state.long ? "Rewrite full description" : "✨ Write full description";
  $("full-btn").className = state.long ? "btn" : "btn btn-primary";
}

function updateTitleCount() {
  $("title-count").textContent = $("title").value.length;
}

// ------------------------------------------------------------------ tabs
function selectTab(which) {
  for (const name of ["short", "full"]) {
    const on = name === which;
    $(`tab-${name}`).setAttribute("aria-selected", String(on));
    $(`tab-${name}`).tabIndex = on ? 0 : -1;
    $(`panel-${name}`).hidden = !on;
  }
}

// --------------------------------------------------------------- exports
function exportPayload() {
  const edited = currentListing();
  delete edited.__seed;
  const full = $("full").value.trim();
  return { ...edited, ...(full ? { full_description: full } : {}) };
}

async function copyText() {
  const p = exportPayload();
  const text = exportText(p.suggested_title, p.full_description || p.suggested_description, p.tags);
  try {
    await navigator.clipboard.writeText(text);
    $("copy-status").textContent = "Copied to clipboard.";
  } catch {
    $("copy-status").textContent = "Couldn't copy automatically. Select the text and copy it manually.";
  }
}

function downloadJson() {
  const blob = new Blob([JSON.stringify(exportPayload(), null, 2)], { type: "application/json" });
  const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(blob), download: "listing.json" });
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

// ------------------------------------------------------------------ wiring
function init() {
  const input = $("file-input");
  input.addEventListener("change", () => { addFiles(input.files); input.value = ""; });
  const dz = $("dropzone");
  ["dragenter", "dragover"].forEach((t) => dz.addEventListener(t, (e) => { e.preventDefault(); dz.classList.add("drag"); }));
  ["dragleave", "drop"].forEach((t) => dz.addEventListener(t, (e) => { e.preventDefault(); dz.classList.remove("drag"); }));
  dz.addEventListener("drop", (e) => addFiles(e.dataTransfer.files));
  $("create-btn").addEventListener("click", run);
  $("title").addEventListener("input", updateTitleCount);
  $("tab-short").addEventListener("click", () => selectTab("short"));
  $("tab-full").addEventListener("click", () => selectTab("full"));
  $("tab-short").parentElement.addEventListener("keydown", (e) => {
    if (e.key === "ArrowRight") { selectTab("full"); $("tab-full").focus(); }
    if (e.key === "ArrowLeft") { selectTab("short"); $("tab-short").focus(); }
  });
  $("full-btn").addEventListener("click", () => { selectTab("full"); writeFull(); });
  $("images-btn").addEventListener("click", () => makeImages());
  $("copy-btn").addEventListener("click", copyText);
  $("download-btn").addEventListener("click", downloadJson);
  $("upload-hint").textContent = `JPG, PNG or WEBP · up to ${MAX_FILES} photos. Use different views of the same item. Photos are resized in your browser before upload.`;
  render();
}

init();
