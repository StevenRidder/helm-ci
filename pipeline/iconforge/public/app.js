/* Helm Clean-room Symbol Catalog — PUBLIC static build (FORGE-59).
 * Reads one DB-derived record per symbol from proof/site-index.json (symbols[]),
 * with explicit art paths. No client-side dedup, no directory guessing, no backend,
 * no local sign-off (:9017) hooks — that lives only in the local review prototype.
 */
(() => {
  "use strict";

  const REPO = "StevenRidder/helm-public";
  const REVIEW_KEY = "helm-forge59-public-reviews";
  const PALETTES = ["day", "dusk", "night"];
  const state = { q: "", family: "", geometry: "", gate: "", page: 0, pageSize: 60 };
  let DATA = null;
  let SYMS = [];
  let filtered = [];
  const reviews = loadReviews();

  const el = (id) => document.getElementById(id);
  const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  async function init() {
    bindControls();
    applyTheme(localStorage.getItem("helm-theme") || "light");
    try {
      const res = await fetch("proof/site-index.json", { headers: { Accept: "application/json" } });
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      DATA = await res.json();
    } catch (err) {
      el("alert").innerHTML =
        `<div class="alert alert-danger"><h4 class="alert-title">Catalog data failed to load</h4>
         <div class="text-secondary">proof/site-index.json is required; there is no fallback. ${esc(err.message)}</div></div>`;
      return;
    }
    SYMS = DATA.symbols || [];
    el("schemaTag").textContent = DATA.schema || "";
    renderStats();
    buildFilters();
    apply();
    updateDock();
  }

  /* ---------- stats + filters ---------- */
  function statCard(label, value, sub, tone) {
    return `<div class="col-6 col-sm-4 col-xl"><div class="card card-sm"><div class="card-body">
      <div class="subheader">${esc(label)}</div>
      <div class="h1 mb-0 mt-1 ${tone ? "text-" + tone : ""}">${esc(value)}</div>
      <div class="text-secondary small">${sub || ""}</div></div></div></div>`;
  }
  function renderStats() {
    const c = DATA.coverage || {};
    const g = c.proof_gate_counts || {};
    const contexts = SYMS.reduce((n, s) => n + (s.uses || 1), 0);
    el("stats").innerHTML = [
      statCard("Symbols", SYMS.length.toLocaleString(), "unique final icons"),
      statCard("Chart contexts", contexts.toLocaleString(), "reuse instances"),
      statCard("Owner signoff", (c.human_review_approved_symbols ?? 0).toLocaleString(), c.human_review_status || "not recorded", "green"),
      statCard("Registry symbols", (c.registry_symbols ?? 0).toLocaleString(), `${(c.registry_blocked_candidates ?? 0).toLocaleString()} non-symbol candidates`),
      statCard("Proof gates", `${g.green ?? 0}/${g.yellow ?? 0}/${g.red ?? 0}`, "green / yellow / red (by context)"),
      statCard("Runtime export", (c.runtime_export_rows ?? 0).toLocaleString(), "fail-closed", "danger"),
    ].join("");
  }
  function buildFilters() {
    const f = DATA.facets || {};
    fillSelect("family", f.family_counts);
    fillSelect("geometry", f.geometry_counts);
  }
  function fillSelect(id, counts) {
    const sel = el(id);
    const keep = sel.querySelector("option").outerHTML;
    sel.innerHTML = keep + Object.keys(counts || {}).sort().map((k) => `<option value="${esc(k)}">${esc(k)} (${counts[k]})</option>`).join("");
  }

  /* ---------- filter + render ---------- */
  function matches(s) {
    if (state.family && !(s.families || [s.family]).includes(state.family)) return false;
    if (state.geometry && !(s.geometries || [s.geometry]).includes(state.geometry)) return false;
    if (state.gate && ((s.gate || {}).proof || "red") !== state.gate) return false;
    if (state.q) {
      const hay = JSON.stringify([s.id, s.name, s.object_class, s.family, s.s52_refs, s.s101]).toLowerCase();
      if (!hay.includes(state.q.toLowerCase())) return false;
    }
    return true;
  }
  function apply() {
    filtered = SYMS.filter(matches);
    if (state.page * state.pageSize >= filtered.length) state.page = 0;
    render();
  }
  function gateBadge(kind, val) {
    const tone = val === "green" ? "green" : val === "yellow" ? "yellow" : val === "red" ? "red" : "secondary";
    return `<span class="badge bg-${tone}-lt">${esc(kind)} ${esc(val || "—")}</span>`;
  }
  function triptych(art) {
    return `<div class="trip mb-2">${PALETTES.map((p) =>
      `<div class="sw">${art && art[p] ? `<img loading="lazy" src="${esc(art[p])}" alt="${p}">` : `<div class="empty"></div>`}</div>`
    ).join("")}</div>`;
  }
  function card(s) {
    const parts = [];
    if (s.object_class && s.object_class !== s.id) parts.push(s.object_class);
    else if (s.family && s.family !== s.id) parts.push(s.family);
    if (s.geometry) parts.push(s.geometry);
    const reviewed = reviews[s.id] ? `<span class="badge bg-azure-lt">${esc(reviews[s.id].decision)}</span>` : "";
    const ownerApproved = (s.human_review || {}).final_approved ? `<span class="badge bg-green-lt">owner final</span>` : "";
    const uses = s.uses > 1 ? `<span class="badge bg-secondary-lt" title="${s.uses} chart contexts use this symbol">${s.uses} uses</span>` : "";
    return `<div class="col-6 col-md-4 col-lg-3 col-xxl-2">
      <div class="card sym-card" data-id="${esc(s.id)}"><div class="card-body p-2">
        ${triptych(s.art)}
        <div class="sym-id text-truncate" title="${esc(s.id)}">${esc(s.name || s.id)}</div>
        <div class="text-secondary small text-truncate">${esc(parts.join(" · "))}</div>
        <div class="mt-1 d-flex flex-wrap gap-1">${gateBadge("proof", (s.gate || {}).proof)} ${uses} ${ownerApproved} ${reviewed} ${s.s101_promoted ? '<span class="badge bg-yellow-lt">S-101→HELM</span>' : ""}</div>
      </div></div></div>`;
  }
  function render() {
    const total = filtered.length;
    const start = state.page * state.pageSize;
    const pageSyms = filtered.slice(start, start + state.pageSize);
    el("grid").innerHTML = pageSyms.map(card).join("") || `<div class="col-12"><div class="text-secondary p-4 text-center">No symbols match these filters.</div></div>`;
    el("count").textContent = total ? `${(start + 1).toLocaleString()}–${(start + pageSyms.length).toLocaleString()} of ${total.toLocaleString()} symbols` : "0 symbols";
    renderPager(total);
    for (const c of document.querySelectorAll(".sym-card")) c.addEventListener("click", () => openDetail(c.dataset.id));
  }
  function renderPager(total) {
    const pages = Math.ceil(total / state.pageSize) || 1;
    const cur = state.page;
    const item = (p, label, disabled, active) => `<li class="page-item ${disabled ? "disabled" : ""} ${active ? "active" : ""}"><a class="page-link" href="#" data-p="${p}">${label}</a></li>`;
    const parts = [item(cur - 1, "‹", cur === 0)];
    for (let p = Math.max(0, cur - 2); p <= Math.min(pages - 1, cur + 2); p++) parts.push(item(p, p + 1, false, p === cur));
    parts.push(item(cur + 1, "›", cur >= pages - 1));
    const pager = el("pager");
    pager.innerHTML = parts.join("");
    for (const a of pager.querySelectorAll("a.page-link")) a.addEventListener("click", (e) => { e.preventDefault(); const p = +a.dataset.p; if (p >= 0 && p < pages) { state.page = p; render(); window.scrollTo({ top: 0, behavior: "smooth" }); } });
  }

  /* ---------- detail ---------- */
  const offcanvas = () => bootstrap.Offcanvas.getOrCreateInstance(el("detail"));
  function paletteStrip(art) {
    if (!art) return "";
    const cells = PALETTES.map((p) => `<div class="cell"><div class="box">${art[p] ? `<img loading="lazy" src="${esc(art[p])}" alt="${p}">` : "—"}</div><div class="small text-secondary mt-1">${p}</div></div>`).join("");
    return `<div class="mb-3"><div class="fw-bold mb-1">Palette variants (day / dusk / night)</div><div class="strip">${cells}</div></div>`;
  }
  function contextsBlock(s) {
    const ctx = s.contexts || [];
    if (!ctx.length) return "";
    const rows = ctx.slice(0, 40).map((c) => `<tr><td class="sym-id">${esc(c.object_class || "—")}</td><td>${esc(c.geometry || "—")}</td><td>${esc(c.section || "—")}</td><td>${gateBadge("", c.gate)}</td><td class="text-secondary">${c.count > 1 ? "×" + c.count : ""}</td></tr>`).join("");
    return `<div class="hr-text">chart contexts (${s.uses || ctx.length})</div>
      <div class="table-responsive mb-3"><table class="table table-sm"><thead><tr><th>S-57 object</th><th>Geometry</th><th>Section</th><th>Proof</th><th></th></tr></thead><tbody>${rows}</tbody></table>
      ${ctx.length > 40 ? `<div class="small text-secondary">+${ctx.length - 40} more distinct contexts</div>` : ""}</div>`;
  }
  function refChips(refs) {
    if (!refs || !Object.keys(refs).length) return "";
    return `<div class="d-flex flex-wrap mb-3">${Object.entries(refs).map(([k, vals]) =>
      `<div class="me-3 mb-1"><div class="text-secondary small text-uppercase">${esc(k.replace(/_/g, " "))}</div>${vals.map((v) => `<span class="badge bg-secondary-lt me-1 mb-1 sym-id">${esc(v)}</span>`).join("")}</div>`).join("")}</div>`;
  }
  function interpBlocks(hi) {
    if (!hi || typeof hi !== "object") return "";
    const label = (k) => k.replace(/_/g, " ").replace(/\bs(\d+)\b/gi, (_, n) => "S-" + n);
    return Object.entries(hi).filter(([k, v]) => k !== "helm_render_interpretation" && v).map(([k, v]) =>
      `<div class="mb-2"><div class="fw-bold text-capitalize">${esc(label(k))}</div><div class="authority text-secondary small">${esc(String(v))}</div></div>`).join("");
  }
  function comparisonSection(s) {
    return `<div class="hr-text">comparison evidence</div>
      <div class="text-secondary small mb-3">OpenCPN and S-101 comparison renders are recorded in the proof data and local review bundle. The public catalog ships only Helm-owned SVG assets, public-safe registry data, and fail-closed proof summaries.</div>`;
  }
  function openDetail(id) {
    const s = SYMS.find((x) => x.id === id);
    if (!s) return;
    el("detailTitle").textContent = s.name || s.id;
    el("detailKey").textContent = s.id;
    const t = s.s101 || {};
    const reasons = ((s.runtime || {}).reason_codes || []).map((x) => `<span class="badge bg-red-lt me-1 mb-1">${esc(x)}</span>`).join("") || `<span class="text-secondary small">none recorded</span>`;
    const rev = reviews[s.id] || { decision: "", notes: "" };
    const sel = (v) => (rev.decision === v ? "checked" : "");
    el("detailBody").innerHTML = `
      <div class="mb-3 d-flex flex-wrap gap-1 align-items-center">
        ${gateBadge("proof", (s.gate || {}).proof)} ${gateBadge("visual", (s.gate || {}).visual)} ${gateBadge("semantic", (s.gate || {}).semantic)}
        ${(s.human_review || {}).final_approved ? '<span class="badge bg-green-lt">owner final approved</span>' : ''}
        <button class="btn btn-sm btn-outline-primary ms-auto" id="seeFamily">See all “${esc(s.family)}”</button>
      </div>
      ${s.art && s.art.canonical ? `<div class="d-flex align-items-center gap-3 mb-3"><div class="card-icon" style="width:120px;height:120px;flex:none"><img src="${esc(s.art.canonical)}" alt="canonical" onerror="this.style.visibility='hidden'"></div><div><div class="fw-bold">Helm resolved — final art</div><div class="text-secondary small">canonical + day/dusk/night below</div></div></div>` : ""}
      ${paletteStrip(s.art)}
      <div class="hr-text">classification</div>
      <div class="datagrid mb-2">
        <div class="datagrid-item"><div class="datagrid-title">S-57 object class</div><div class="datagrid-content sym-id">${esc(s.object_class || "—")}</div></div>
        <div class="datagrid-item"><div class="datagrid-title">Geometry</div><div class="datagrid-content">${esc(s.geometry || "—")}</div></div>
        <div class="datagrid-item"><div class="datagrid-title">Family</div><div class="datagrid-content">${esc(s.family || "—")}</div></div>
        <div class="datagrid-item"><div class="datagrid-title">Category</div><div class="datagrid-content">${esc(s.category || "—")}</div></div>
      </div>
      ${refChips(s.s52_refs)}
      ${contextsBlock(s)}
      <div class="hr-text">standards &amp; authority</div>
      <div class="datagrid mb-3">
        <div class="datagrid-item"><div class="datagrid-title">S-101 classification</div><div class="datagrid-content">${esc(t.classification || "—")}</div></div>
        <div class="datagrid-item"><div class="datagrid-title">Mapping type</div><div class="datagrid-content">${esc(t.mapping_type || "—")}</div></div>
        <div class="datagrid-item"><div class="datagrid-title">Rule file</div><div class="datagrid-content sym-id">${esc(t.rule_file || "—")}</div></div>
        <div class="datagrid-item"><div class="datagrid-title">Runtime</div><div class="datagrid-content"><span class="badge bg-red-lt">fail-closed</span></div></div>
      </div>
      ${s.authority ? `<div class="mb-2"><div class="fw-bold">Helm authority &amp; interpretation</div><div class="authority text-secondary small">${esc(s.authority)}</div></div>` : ""}
      ${interpBlocks(s.interpretation)}
      <div class="mb-3"><div class="fw-bold mb-1">Runtime block reasons</div><div>${reasons}</div></div>
      ${comparisonSection(s)}
      <div class="card"><div class="card-body">
        <div class="fw-bold mb-2">Reviewer decision <span class="text-secondary fw-normal small">(stored in your browser, exported as JSON)</span></div>
        <div class="btn-group w-100 mb-2" role="group">
          <input type="radio" class="btn-check" name="rev" id="rev-approve" value="approve" ${sel("approve")}><label class="btn btn-outline-green" for="rev-approve">Approve</label>
          <input type="radio" class="btn-check" name="rev" id="rev-needs" value="needs_work" ${sel("needs_work")}><label class="btn btn-outline-yellow" for="rev-needs">Needs work</label>
          <input type="radio" class="btn-check" name="rev" id="rev-reject" value="reject" ${sel("reject")}><label class="btn btn-outline-red" for="rev-reject">Reject</label>
        </div>
        <textarea class="form-control mb-2" id="revNotes" rows="2" placeholder="Notes (optional)">${esc(rev.notes || "")}</textarea>
        <button class="btn btn-primary w-100" id="revSave">Save decision</button>
      </div></div>`;
    el("revSave").addEventListener("click", () => {
      const decision = (document.querySelector('input[name="rev"]:checked') || {}).value;
      if (!decision) return;
      reviews[s.id] = { symbol_id: s.id, family: s.family, decision, notes: el("revNotes").value.trim(), ts: new Date().toISOString() };
      saveReviews(); updateDock(); render(); offcanvas().hide();
    });
    el("seeFamily").addEventListener("click", () => { state.family = s.family; el("family").value = s.family; state.page = 0; apply(); offcanvas().hide(); });
    offcanvas().show();
  }

  /* ---------- reviews ---------- */
  function loadReviews() { try { return JSON.parse(localStorage.getItem(REVIEW_KEY) || "{}"); } catch { return {}; } }
  function saveReviews() { localStorage.setItem(REVIEW_KEY, JSON.stringify(reviews)); }
  function decisionsJson() {
    return JSON.stringify({ schema: "helm.forge.public_review_decisions.v1", site_schema: DATA && DATA.schema, count: Object.keys(reviews).length,
      decisions: Object.entries(reviews).map(([id, v]) => ({ symbol_id: id, ...v })) }, null, 2);
  }
  function updateDock() {
    const n = Object.keys(reviews).length;
    el("reviewDock").hidden = n === 0;
    el("reviewCount").textContent = n;
    el("openIssue").href = `https://github.com/${REPO}/issues/new?title=` + encodeURIComponent(`Symbol review: ${n} decision(s)`) +
      "&body=" + encodeURIComponent(`I reviewed ${n} symbol(s):\n\n\`\`\`json\n` + decisionsJson() + "\n```\n");
  }
  function exportJson() {
    const blob = new Blob([decisionsJson()], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = "helm-symbol-review-decisions.json"; a.click();
    URL.revokeObjectURL(a.href);
  }

  /* ---------- controls ---------- */
  function applyTheme(t) { document.documentElement.setAttribute("data-bs-theme", t); localStorage.setItem("helm-theme", t); }
  function bindControls() {
    el("q").addEventListener("input", (e) => { state.q = e.target.value; state.page = 0; apply(); });
    el("family").addEventListener("change", (e) => { state.family = e.target.value; state.page = 0; apply(); });
    el("geometry").addEventListener("change", (e) => { state.geometry = e.target.value; state.page = 0; apply(); });
    el("gate").addEventListener("change", (e) => { state.gate = e.target.value; state.page = 0; apply(); });
    el("themeToggle").addEventListener("click", () => applyTheme(document.documentElement.getAttribute("data-bs-theme") === "dark" ? "light" : "dark"));
    el("exportJson").addEventListener("click", exportJson);
    el("clearReviews").addEventListener("click", () => { if (confirm("Clear all review decisions stored in this browser?")) { for (const k of Object.keys(reviews)) delete reviews[k]; saveReviews(); updateDock(); render(); } });
  }

  document.addEventListener("DOMContentLoaded", init);
})();
