"""Build a browser checklist for human Icon Forge remediation review.

Run:
  python3 -m forge.human_review_page
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import os
from pathlib import Path

from . import db_review_api


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
OUT = ROOT / "out" / "human_review"
TABLE = CATALOG / "standard_source_table.json"
HTML_OUT = OUT / "icon_review.html"
PASS_HTML_OUT = OUT / "pass_review.html"
DB_HTML_OUT = OUT / "db_review.html"
CSV_OUT = OUT / "icon_review_seed.csv"
FEEDBACK_CSV = OUT / "icon_review_feedback.csv"
FEEDBACK_JSON = OUT / "icon_review_feedback.json"
SIGNOFF_CSV = OUT / "icon_review_signoff.csv"
SIGNOFF_JSON = OUT / "icon_review_signoff.json"
BEACON_TEMPLATE_PREVIEW = CATALOG / "beacon_family_template_preview.json"
LATERAL_BEACON_TEMPLATE_PREVIEW = CATALOG / "lateral_beacon_family_template_preview.json"
STAKE_BEACON_TEMPLATE_PREVIEW = CATALOG / "stake_beacon_family_template_preview.json"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _first_ref_path(refs: list[dict], keys: tuple[str, ...]) -> str | None:
    for ref in refs:
        for key in keys:
            value = ref.get(key)
            if isinstance(value, dict):
                value = value.get("day")
            if value:
                return str(value)
    return None


def _html_path(value: str | None, html_dir: Path = OUT) -> str | None:
    if not value:
        return None
    path = Path(value)
    if path.is_absolute():
        if not path.exists():
            return None
        return os.path.relpath(path, html_dir)
    local = ROOT / value
    if local.exists():
        return os.path.relpath(local, html_dir)
    repo_local = ROOT.parent.parent / value
    if repo_local.exists():
        return os.path.relpath(repo_local, html_dir)
    if value.startswith(("http://", "https://")):
        return value
    return None


def _ref_symbol_id(refs: list[dict]) -> str:
    for ref in refs:
        value = ref.get("symbol_id") or ref.get("label")
        if value:
            return str(value)
    return ""


def _s101_witness_note(refs: list[dict], required_colours: str) -> str:
    if not refs:
        return ""
    first = refs[0]
    status = first.get("status") or first.get("source") or "reference"
    note = "shape witness; raw SVG is not color-resolved portrayal"
    if required_colours and required_colours != "reference-defined":
        note += f"; required colours: {required_colours}"
    if status:
        note += f"; {status}"
    return note


def _status_rank(status: str) -> int:
    order = {
        "repaired_pending_judge_rerun": 0,
        "judge_fail_repair_queue": 1,
        "chart1_fail_repair_queue": 2,
        "pending_judge": 3,
        "judge_pass_pending_final_approval": 4,
        "no_helm_candidate": 5,
    }
    return order.get(status, 99)


def _review_default(status: str) -> bool:
    return status in {
        "repaired_pending_judge_rerun",
        "judge_fail_repair_queue",
        "chart1_fail_repair_queue",
        "pending_judge",
    }


def _priority_default(status: str) -> str:
    if status == "chart1_fail_repair_queue":
        return "high"
    if status in {"judge_fail_repair_queue", "repaired_pending_judge_rerun"}:
        return "medium"
    if status == "pending_judge":
        return "low"
    return ""


def _reason_default(row: dict) -> list[str]:
    status = row["helm_candidate"]["candidate_status"]
    latest = row.get("judge", {}).get("latest") or {}
    repair = row.get("repair_queue_item") or {}
    reasons = list(latest.get("safety_reason_codes") or repair.get("safety_reason_codes") or [])
    if status == "chart1_fail_repair_queue":
        reasons.extend((row.get("chart1_parity_gate") or {}).get("reason_codes") or [])
    return list(dict.fromkeys(str(reason) for reason in reasons if reason))


def _expected_change(row: dict) -> str:
    repair = row.get("repair_queue_item") or {}
    latest = row.get("judge", {}).get("latest") or {}
    chart1 = row.get("chart1_parity_gate") or {}
    return (
        repair.get("required_change")
        or latest.get("required_change")
        or chart1.get("required_change")
        or ""
    )


def _helm_preview_path(asset: str, helm: dict) -> str | None:
    render = (helm.get("renders") or {}).get("day")
    if render:
        return render
    canonical_svg = helm.get("canonical_svg") or ""
    if canonical_svg.startswith("assets/svg/triad_generated/"):
        candidate = ROOT / "out" / "triad_reference_candidate_pack" / "renders" / f"{asset}__day.png"
        if candidate.exists():
            return str(candidate)
        stem_candidate = ROOT / "out" / "triad_reference_candidate_pack" / "renders" / f"{Path(canonical_svg).stem}__day.png"
        if stem_candidate.exists():
            return str(stem_candidate)
    source_batch = helm.get("source_batch")
    if source_batch:
        batch_path = ROOT / source_batch
        if batch_path.exists():
            try:
                batch = _read_json(batch_path)
            except json.JSONDecodeError:
                batch = {}
            for row in batch.get("symbols", []):
                if row.get("asset") == asset:
                    render = (row.get("after_renders") or {}).get("day")
                    if render:
                        return render
                    break
    for candidate in [
        ROOT / "out" / "triad_reference_candidate_pack" / "renders" / f"{asset}__day.png",
        ROOT / "out" / "source_priority_icon_pack" / "renders" / f"{asset}__day.png",
        ROOT / "out" / "multisource_svg_draft" / "renders" / f"{asset}__day.png",
        ROOT / "out" / "owned_symbol_batch50" / "renders" / f"{asset}__day.png",
    ]:
        if candidate.exists():
            return str(candidate)
    return canonical_svg


def _row_payload(row: dict) -> dict:
    refs = row.get("reference_providers") or {}
    s101_refs = refs.get("s101") or []
    helm = row.get("helm_candidate") or {}
    semantic = row.get("semantic_brief") or {}
    latest = row.get("judge", {}).get("latest") or {}
    status = helm.get("candidate_status") or "unknown"
    asset = row["asset"]
    candidate_revision = "towers-smokestack-family-v3" if asset.startswith("TOWERS") else ""
    required_colours = ", ".join(semantic.get("required_colours") or []) or "reference-defined"
    return {
        "asset": asset,
        "name": row.get("name") or "",
        "family": row.get("family") or "",
        "kind": row.get("kind") or "",
        "status": status,
        "needs_remediation_default": _review_default(status),
        "priority_default": _priority_default(status),
        "reason_codes_default": _reason_default(row),
        "expected_change": _expected_change(row),
        "semantic_brief": semantic.get("brief") or "",
        "required_shape": semantic.get("required_shape") or "",
        "required_colours": required_colours,
        "s57_object_class": (row.get("s57_structure") or {}).get("object_class") or "",
        "s57_conditions": "; ".join((row.get("s57_structure") or {}).get("conditions") or []),
        "s101_symbol_id": _ref_symbol_id(s101_refs),
        "s101_witness_note": _s101_witness_note(s101_refs, required_colours),
        "helm_svg": helm.get("canonical_svg") or "",
        "helm_image": _html_path(_helm_preview_path(asset, helm)),
        "opencpn_image": _html_path(_first_ref_path(refs.get("opencpn_render") or [], ("day", "paths"))),
        "s101_image": _html_path(_first_ref_path(s101_refs, ("path",))),
        "aquamap_image": _html_path(_first_ref_path(refs.get("aquamap") or [], ("path",))),
        "source_batch": helm.get("source_batch") or "",
        "latest_judge_batch": latest.get("batch") or "",
        "latest_judge_comments": latest.get("judge_comments") or latest.get("observed") or "",
        "latest_expected": latest.get("expected") or "",
        "candidate_revision": candidate_revision,
    }


def _apply_review_overlays(rows: list[dict]) -> None:
    """Apply human-gated preview candidates without mutating the master table."""
    _apply_template_overlay(
        rows,
        path=BEACON_TEMPLATE_PREVIEW,
        expected_change=(
            "Human approve/reject this BCNGEN6 merged-silhouette template; "
            "run Annex A ratio/proportion check before applying across the full beacon family."
        ),
        source_batch="catalog/beacon_family_template_preview.json",
        judge_batch="beacon_family_template_preview_human_gate",
        candidate_revision="beacon-bcngen6-wide-post-v4-hole-family",
        judge_comments=(
            "Human style gate candidate: user-created BCNGEN6 shape redrawn as a Helm/OpenBridge "
            "merged solid silhouette with S-101-style cut-out head hole. Ratio check against "
            "Annex A remains pending before family-wide rollout."
        ),
    )
    _apply_template_overlay(
        rows,
        path=LATERAL_BEACON_TEMPLATE_PREVIEW,
        expected_change=(
            "Human approve/reject this BCNLAT rectangular lateral-beacon template; "
            "run Annex A ratio/proportion check before applying across the full lateral beacon family."
        ),
        source_batch="catalog/lateral_beacon_family_template_preview.json",
        judge_batch="lateral_beacon_family_template_preview_human_gate",
        candidate_revision="beacon-bcnlat-rectangular-v1-family",
        judge_comments=(
            "Human style gate candidate: user-created BCNLAT shape redrawn as a Helm/OpenBridge "
            "tall rectangular lateral beacon with centered dot and family color bands. Ratio check "
            "against Annex A remains pending before family-wide rollout."
        ),
    )
    _apply_template_overlay(
        rows,
        path=STAKE_BEACON_TEMPLATE_PREVIEW,
        expected_change=(
            "Human approve/reject this BCNSTK stake template redrawn from the user-provided "
            "BNKSTK pattern with a skinny stick shaft and tiny lower crossing cutout; previous "
            "BCNSTK approvals were superseded by this revision."
        ),
        source_batch="catalog/stake_beacon_family_template_preview.json",
        judge_batch="stake_beacon_family_template_preview_human_gate",
        candidate_revision="beacon-bcnstk-lower-cutout-v4-family",
        judge_comments=(
            "Human style gate candidate: BCNSTK shape redrawn from the user-provided BNKSTK "
            "pattern: skinny vertical stick, small lower block, horizontal foot, tiny S-101-style "
            "cutout at the lower crossing like BCNGEN, and family color bands."
        ),
    )


def _apply_template_overlay(
    rows: list[dict],
    *,
    path: Path,
    expected_change: str,
    source_batch: str,
    judge_batch: str,
    candidate_revision: str,
    judge_comments: str,
) -> None:
    if not path.exists():
        return
    try:
        preview = _read_json(path)
    except json.JSONDecodeError:
        return
    samples = {sample.get("asset"): sample for sample in preview.get("samples", [])}
    if not samples:
        return
    for row in rows:
        sample = samples.get(row["asset"])
        if not sample:
            continue
        renders = sample.get("renders") or {}
        row["status"] = "judge_pass_pending_final_approval"
        row["needs_remediation_default"] = False
        row["priority_default"] = ""
        row["reason_codes_default"] = []
        row["expected_change"] = expected_change
        row["helm_svg"] = sample.get("svg") or row["helm_svg"]
        row["helm_image"] = _html_path(renders.get("day"))
        row["source_batch"] = source_batch
        row["latest_judge_batch"] = judge_batch
        row["candidate_revision"] = candidate_revision
        row["latest_judge_comments"] = judge_comments


def build(*, limit: int | None = None) -> dict:
    table = _read_json(TABLE)
    rows = [_row_payload(row) for row in table["rows"]]
    _apply_review_overlays(rows)
    rows.sort(key=lambda row: (_status_rank(row["status"]), row["asset"]))
    if limit is not None:
        rows = rows[:limit]
    OUT.mkdir(parents=True, exist_ok=True)
    _write_csv(rows)
    _write_html(rows, table.get("summary") or {})
    _write_pass_html([row for row in rows if row["status"] == "judge_pass_pending_final_approval"], table.get("summary") or {})
    _write_db_review_html()
    return {
        "status": "human_review_page_written",
        "summary": {
            "rows": len(rows),
            "default_remediation_rows": sum(1 for row in rows if row["needs_remediation_default"]),
            "pass_pending_human_rows": sum(1 for row in rows if row["status"] == "judge_pass_pending_final_approval"),
        },
        "outputs": {
            "html": str(HTML_OUT.relative_to(ROOT)),
            "pass_html": str(PASS_HTML_OUT.relative_to(ROOT)),
            "db_html": str(DB_HTML_OUT.relative_to(ROOT)),
            "csv": str(CSV_OUT.relative_to(ROOT)),
        },
    }


def _write_csv(rows: list[dict]) -> None:
    fields = [
        "asset",
        "name",
        "status",
        "needs_remediation",
        "priority",
        "reason_codes",
        "feedback",
        "expected_change",
        "s57_object_class",
        "s57_conditions",
        "source_batch",
        "helm_svg",
    ]
    with CSV_OUT.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "asset": row["asset"],
                "name": row["name"],
                "status": row["status"],
                "needs_remediation": "true" if row["needs_remediation_default"] else "false",
                "priority": row["priority_default"],
                "reason_codes": ";".join(row["reason_codes_default"]),
                "feedback": "",
                "expected_change": row["expected_change"],
                "s57_object_class": row["s57_object_class"],
                "s57_conditions": row["s57_conditions"],
                "source_batch": row["source_batch"],
                "helm_svg": row["helm_svg"],
            })



def _e(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def _image_box_v2(label: str, src: str | None, note: str = "") -> str:
    if not src:
        note_html = f'<div class="imageNote">{_e(note)}</div>' if note else ""
        return f'<div class="imageBox missingBox"><div class="missing">no {_e(label)} evidence</div><div class="label">{_e(label)}</div>{note_html}</div>'
    note_html = f'<div class="imageNote">{_e(note)}</div>' if note else ""
    return (
        f'<div class="imageBox"><img src="{_e(src)}" alt="{_e(label)}">'
        f'<div class="label">{_e(label)}</div>{note_html}</div>'
    )


def _status_class_v2(status: str) -> str:
    if "pass" in status:
        return "pass"
    if "chart1" in status:
        return "chart1"
    if "fail" in status:
        return "fail"
    if "pending" in status or "rerun" in status:
        return "pending"
    return ""


def _base_css_v2() -> str:
    return """
:root { color-scheme: light; --ink: #172033; --muted: #586174; --line: #d8dee8; --soft: #f6f8fb; --blue: #165dff; --red: #b42318; --green: #027a48; }
* { box-sizing: border-box; }
body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; color: var(--ink); background: white; }
header { position: sticky; top: 0; z-index: 2; background: rgba(255,255,255,.97); border-bottom: 1px solid var(--line); padding: 14px 18px 12px; }
h1 { margin: 0 0 8px; font-size: 21px; letter-spacing: 0; }
a { color: var(--blue); text-decoration: none; }
.toolbar { display: grid; grid-template-columns: minmax(220px, 1fr) 190px 160px auto auto auto auto; gap: 8px; align-items: center; }
.toolbar.signoff { grid-template-columns: minmax(220px, 1fr) 190px 170px auto; }
input, select, textarea, button { font: inherit; }
input[type="search"], input[type="text"], select { border: 1px solid #bac3d3; border-radius: 6px; padding: 7px 9px; min-height: 36px; background: white; width: 100%; }
button, .buttonLink { border: 1px solid #aab4c5; border-radius: 6px; padding: 7px 10px; min-height: 36px; background: #fff; cursor: pointer; color: var(--ink); display: inline-flex; align-items: center; justify-content: center; white-space: nowrap; }
button.primary, .buttonLink.primary { background: var(--blue); border-color: var(--blue); color: white; }
.summary { color: var(--muted); font-size: 13px; margin-top: 8px; display: flex; gap: 14px; flex-wrap: wrap; align-items: center; }
.saveStatus, .rowSaveStatus { color: var(--muted); font-size: 12px; }
main { padding: 14px 18px 40px; }
.row { display: grid; grid-template-columns: minmax(520px, 1fr) minmax(360px, .72fr); gap: 14px; border: 1px solid var(--line); border-radius: 8px; margin-bottom: 12px; padding: 12px; background: white; }
.report { display: grid; grid-template-columns: 220px minmax(300px, 1fr); gap: 12px; min-width: 0; }
.meta h2 { margin: 0 0 4px; font-size: 17px; letter-spacing: 0; overflow-wrap: anywhere; }
.status { display: inline-block; font-size: 12px; color: white; background: #475467; border-radius: 999px; padding: 3px 8px; margin: 2px 0 8px; }
.status.pass { background: var(--green); }
.status.fail, .status.chart1 { background: var(--red); }
.status.pending { background: #175cd3; }
.small { color: var(--muted); font-size: 13px; line-height: 1.38; overflow-wrap: anywhere; }
.narrative { grid-column: 1 / -1; display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.note { background: var(--soft); border: 1px solid #edf0f5; border-radius: 6px; padding: 8px; min-height: 54px; }
.images { display: grid; grid-template-columns: repeat(4, minmax(94px, 1fr)); gap: 8px; align-content: start; }
.imageBox { min-height: 128px; border: 1px solid var(--line); background: var(--soft); border-radius: 6px; padding: 6px; text-align: center; }
.imageBox img { width: 90px; height: 90px; object-fit: contain; display: block; margin: 2px auto 6px; background: white; }
.imageBox .label { font-size: 12px; color: #30394a; }
.imageNote { margin-top: 3px; font-size: 10px; line-height: 1.18; color: #8a4b00; }
.missingBox { background: #fff8ed; border-style: dashed; }
.missing { color: #8a4b00; font-size: 12px; padding: 34px 8px 0; text-align: center; line-height: 1.25; }
.review { border-left: 1px solid var(--line); padding-left: 14px; display: grid; grid-template-columns: 150px 130px 1fr; gap: 8px; align-items: start; }
.review.signoffPanel { grid-template-columns: 160px 1fr; }
.review label { font-size: 12px; color: #344054; display: block; margin-bottom: 4px; }
.checkline { display: flex; gap: 7px; align-items: center; padding-top: 23px; }
.review textarea { width: 100%; min-height: 82px; resize: vertical; border: 1px solid #bac3d3; border-radius: 6px; padding: 8px; }
.wide { grid-column: 1 / -1; }
.actions { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.hidden { display: none; }
@media (max-width: 1120px) {
  .toolbar, .toolbar.signoff { grid-template-columns: 1fr 1fr; }
  .row { grid-template-columns: 1fr; }
  .report { grid-template-columns: 1fr; }
  .review { border-left: 0; border-top: 1px solid var(--line); padding-left: 0; padding-top: 12px; }
}
@media (max-width: 720px) {
  .images, .narrative { grid-template-columns: 1fr 1fr; }
  .review, .review.signoffPanel { grid-template-columns: 1fr; }
}
"""


def _reference_report_v2(row: dict) -> str:
    return f"""
      <div class="report">
        <div class="meta">
          <h2>{_e(row['asset'])} <span class="small">{_e(row['name'])}</span></h2>
          <div class="status {_status_class_v2(row['status'])}">{_e(row['status'])}</div>
          <div class="small"><strong>S-57:</strong> {_e(row['s57_object_class'])} {_e(row['s57_conditions'])}</div>
          <div class="small"><strong>S-101:</strong> {_e(row['s101_symbol_id'] or 'none')}</div>
          <div class="small"><strong>Source:</strong> {_e(row['source_batch'] or 'none')}</div>
          <div class="small"><strong>Shape:</strong> {_e(row['required_shape'] or 'reference-defined')}</div>
          <div class="small"><strong>Colours:</strong> {_e(row['required_colours'])}</div>
        </div>
        <div class="images">
          {_image_box_v2('Helm', row['helm_image'])}
          {_image_box_v2('OpenCPN', row['opencpn_image'])}
          {_image_box_v2('S-101 shape witness', row['s101_image'], row['s101_witness_note'])}
          {_image_box_v2('AquaMap', row['aquamap_image'])}
        </div>
        <div class="narrative">
          <div class="note small"><strong>Semantic brief:</strong> {_e(row['semantic_brief'])}</div>
          <div class="note small"><strong>Judge note:</strong> {_e(row['latest_judge_comments'] or row['latest_expected'] or 'none yet')}</div>
        </div>
      </div>
"""


def _row_card_v2(row: dict) -> str:
    haystack = " ".join([
        row["asset"], row["name"], row["status"], row["semantic_brief"], row["required_shape"],
        row["required_colours"], row["s57_object_class"], row["s57_conditions"],
    ]).lower()
    checked = "checked" if row["needs_remediation_default"] else ""
    priority_options = "".join(
        f'<option value="{_e(priority)}" {"selected" if row["priority_default"] == priority else ""}>{_e(priority or "none")}</option>'
        for priority in ["", "high", "medium", "low"]
    )
    reasons = ";".join(row["reason_codes_default"])
    return f"""
<section class="row" data-asset="{_e(row['asset'])}" data-status="{_e(row['status'])}" data-haystack="{_e(haystack)}">
  {_reference_report_v2(row)}
  <div class="review">
    <div class="checkline">
      <input type="checkbox" class="needs" {checked}>
      <label>needs remediation</label>
    </div>
    <div>
      <label>Priority</label>
      <select class="priority">{priority_options}</select>
    </div>
    <div>
      <label>Reason codes</label>
      <input class="reasons" value="{_e(reasons)}" placeholder="wrong_shape;wrong_colour">
    </div>
    <div class="wide">
      <label>Human feedback for render agent</label>
      <textarea class="feedback" placeholder="Tell the next render agent exactly what to fix."></textarea>
    </div>
    <div class="wide">
      <label>Expected change override</label>
      <textarea class="expectedChange">{_e(row['expected_change'])}</textarea>
    </div>
    <div class="wide actions">
      <button class="submitRow primary" type="button">Submit this row</button>
      <span class="rowSaveStatus">Not submitted</span>
    </div>
  </div>
</section>
"""


def _write_html(rows: list[dict], summary: dict) -> None:
    status_options = sorted({row["status"] for row in rows})
    js = """
const storageKey = "helm.iconforge.humanReview.v1";
let state = loadState();
function loadState() {
  try { return JSON.parse(localStorage.getItem(storageKey) || "{}"); }
  catch (_) { return {}; }
}
function saveState() { localStorage.setItem(storageKey, JSON.stringify(state)); }
function rowEls() { return Array.from(document.querySelectorAll(".row")); }
function hydrate() {
  for (const rowEl of rowEls()) {
    const saved = state[rowEl.dataset.asset];
    if (!saved) continue;
    rowEl.querySelector(".needs").checked = !!saved.needs_remediation;
    rowEl.querySelector(".priority").value = saved.priority || "";
    rowEl.querySelector(".reasons").value = saved.reason_codes || "";
    rowEl.querySelector(".feedback").value = saved.feedback || "";
    rowEl.querySelector(".expectedChange").value = saved.expected_change || "";
  }
}
function collectRow(rowEl) {
  return {
    asset: rowEl.dataset.asset,
    name: rowEl.querySelector("h2 .small")?.textContent.trim() || "",
    status: rowEl.dataset.status,
    needs_remediation: rowEl.querySelector(".needs").checked,
    priority: rowEl.querySelector(".priority").value,
    reason_codes: rowEl.querySelector(".reasons").value,
    feedback: rowEl.querySelector(".feedback").value,
    expected_change: rowEl.querySelector(".expectedChange").value
  };
}
function rememberRow(rowEl) {
  const row = collectRow(rowEl);
  state[row.asset] = {
    needs_remediation: row.needs_remediation,
    priority: row.priority,
    reason_codes: row.reason_codes,
    feedback: row.feedback,
    expected_change: row.expected_change
  };
  saveState();
  updateCounts();
}
function updateCounts() {
  const checked = rowEls().filter(rowEl => rowEl.querySelector(".needs").checked).length;
  document.getElementById("checkedCount").textContent = checked;
}
function applyFilters() {
  const q = document.getElementById("q").value.trim().toLowerCase();
  const status = document.getElementById("statusFilter").value;
  const checkedOnly = document.getElementById("checkedOnly").checked;
  let shown = 0;
  for (const rowEl of rowEls()) {
    const row = collectRow(rowEl);
    const haystack = [rowEl.dataset.haystack, row.feedback, row.reason_codes, row.expected_change].join(" ").toLowerCase();
    const visible = (!q || haystack.includes(q)) && (!status || row.status === status) && (!checkedOnly || row.needs_remediation);
    rowEl.classList.toggle("hidden", !visible);
    if (visible) shown += 1;
  }
  document.getElementById("shownCount").textContent = shown;
  updateCounts();
}
function csvEscape(value) {
  const text = String(value ?? "");
  return /[",\\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}
function exportRows(onlyChecked) {
  const header = ["asset","name","status","needs_remediation","priority","reason_codes","feedback","expected_change"];
  const lines = [header.join(",")];
  for (const rowEl of rowEls()) {
    const row = collectRow(rowEl);
    if (onlyChecked && !row.needs_remediation) continue;
    lines.push(header.map(field => csvEscape(row[field])).join(","));
  }
  return lines.join("\\n") + "\\n";
}
function download(name, text, type) {
  const blob = new Blob([text], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
async function saveRowsToServer(rows, statusEl) {
  const status = document.getElementById("saveStatus");
  if (statusEl) statusEl.textContent = "Saving...";
  status.textContent = "Saving...";
  try {
    const response = await fetch("/api/save-review", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ schema: "helm.iconforge.human_review.v1", rows })
    });
    if (!response.ok) throw new Error(await response.text());
    const result = await response.json();
    status.textContent = `Saved ${result.checked_rows} checked rows`;
    if (statusEl) statusEl.textContent = "Submitted";
  } catch (error) {
    status.textContent = "Server save unavailable; use CSV export";
    if (statusEl) statusEl.textContent = "Submit failed";
    console.error(error);
  }
}
document.getElementById("rows").addEventListener("change", event => {
  const rowEl = event.target.closest(".row");
  if (!rowEl) return;
  rememberRow(rowEl);
  applyFilters();
});
document.getElementById("rows").addEventListener("input", event => {
  if (!event.target.matches("textarea,input.reasons")) return;
  const rowEl = event.target.closest(".row");
  if (rowEl) rememberRow(rowEl);
});
document.getElementById("rows").addEventListener("click", event => {
  const button = event.target.closest(".submitRow");
  if (!button) return;
  const rowEl = button.closest(".row");
  rememberRow(rowEl);
  saveRowsToServer([collectRow(rowEl)], rowEl.querySelector(".rowSaveStatus"));
});
document.getElementById("q").addEventListener("input", applyFilters);
document.getElementById("statusFilter").addEventListener("change", applyFilters);
document.getElementById("checkedOnly").addEventListener("change", applyFilters);
document.getElementById("exportChecked").addEventListener("click", () => download("icon_review_remediation.csv", exportRows(true), "text/csv"));
document.getElementById("exportAll").addEventListener("click", () => download("icon_review_all.csv", exportRows(false), "text/csv"));
document.getElementById("exportJson").addEventListener("click", () => download("icon_review_feedback.json", JSON.stringify({ schema: "helm.iconforge.human_review.v1", rows: rowEls().map(collectRow) }, null, 2), "application/json"));
document.getElementById("saveServer").addEventListener("click", () => saveRowsToServer(rowEls().map(collectRow)));
document.getElementById("reset").addEventListener("click", () => {
  if (confirm("Clear local review checkboxes and feedback?")) {
    state = {};
    saveState();
    location.reload();
  }
});
hydrate();
applyFilters();
"""
    options = "\n".join(f'<option value="{_e(status)}">{_e(status)}</option>' for status in status_options)
    row_cards = "\n".join(_row_card_v2(row) for row in rows)
    pass_count = sum(1 for row in rows if row["status"] == "judge_pass_pending_final_approval")
    body = f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<title>Helm Icon Forge Human Review</title>
<style>{_base_css_v2()}</style>
<header>
  <h1>Helm Icon Forge Human Review</h1>
  <div class="toolbar">
    <input id="q" type="search" placeholder="Search asset, name, status, feedback">
    <select id="statusFilter"><option value="">all statuses</option>{options}</select>
    <label class="checkline"><input id="checkedOnly" type="checkbox"> checked only</label>
    <button id="exportChecked" class="primary">Export checked CSV</button>
    <button id="saveServer">Save to server</button>
    <a class="buttonLink primary" href="pass_review.html" target="_blank">Final sign-off ({pass_count})</a>
    <a class="buttonLink" href="db_review.html" target="_blank">DB evidence</a>
    <button id="exportAll">Export all CSV</button>
    <button id="exportJson">Export JSON</button>
  </div>
  <div class="summary">
    <span>Rows: {summary.get("rows", len(rows))}</span>
    <span>Visible: <strong id="shownCount">0</strong></span>
    <span>Checked: <strong id="checkedCount">0</strong></span>
    <span>Feedback autosaves in this browser. Submit a row while scrolling or save all rows.</span>
    <span class="saveStatus" id="saveStatus">Server save: not yet saved</span>
    <button id="reset">Reset local feedback</button>
  </div>
</header>
<main id="rows">{row_cards}</main>
<script>{js}</script>
</html>
"""
    HTML_OUT.write_text(body)


def _write_db_review_html() -> None:
    try:
        source = db_review_api.build_review_payload(limit=0)["summary"]
        source_note = (
            f"DB rows: {source['total_candidates']}; runtime eligible: "
            f"{source['runtime_eligible']}; DB hash: {source['db_sha256'][:16]}"
        )
    except Exception as exc:  # noqa: BLE001 - page should fail loud at runtime too.
        source_note = f"DB summary unavailable at build time: {exc}"
    js = """
const rowsEl = document.getElementById("rows");
const statusEl = document.getElementById("status");
const qEl = document.getElementById("q");
const statusFilterEl = document.getElementById("statusFilter");
let allRows = [];

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
}
function text(value, fallback = "missing") {
  if (value === null || value === undefined || value === "") return `<span class="missingText">${esc(fallback)}</span>`;
  if (Array.isArray(value)) return esc(value.join(", "));
  if (typeof value === "object") return esc(JSON.stringify(value));
  return esc(value);
}
function image(label, src) {
  if (!src) return `<div class="imageBox missingBox"><div class="missing">missing ${esc(label)}</div><div class="label">${esc(label)}</div></div>`;
  return `<div class="imageBox"><img src="${esc(src)}" alt="${esc(label)}"><div class="label">${esc(label)}</div></div>`;
}
function gateList(row) {
  const style = row.qa.style_contract || {};
  const styleGate = `<li class="${esc(style.gate_status || "pending")}"><strong>style_contract</strong>: ${esc(style.gate_status || "pending")} - ${esc(style.status || "missing")} ${esc((style.issues || []).join(", "))}</li>`;
  return styleGate + (row.qa.gates || []).map(gate =>
    `<li class="${esc(gate.status)}"><strong>${esc(gate.name)}</strong>: ${esc(gate.status)} - ${esc(gate.detail)}</li>`
  ).join("");
}
function renderRow(row) {
  const interp = row.helm.interpretation?.sections || {};
  const missing = row.qa.missing_evidence || [];
  const style = row.qa.style_contract || {};
  return `<section class="row" data-status="${esc(row.status)}" data-haystack="${esc([
      row.symbol_id, row.opencpn.description, row.s57.description, row.s101.feature_type,
      row.s101.rule_file, row.helm.interpretation_status, row.helm.recipe_status,
      style.status, style.gate_status, (style.issues || []).join(" "),
      missing.join(" ")
    ].join(" ").toLowerCase())}">
    <div class="report">
      <div class="meta">
        <h2>${esc(row.symbol_id)} <span class="small">${esc(row.opencpn.description || row.s57.description)}</span></h2>
        <div class="status ${row.qa.runtime_eligible ? "pass" : "pending"}">${esc(row.status)}</div>
        <div class="small"><strong>OpenCPN:</strong> ${text(row.opencpn.object_name || row.opencpn.description)}</div>
        <div class="small"><strong>S-57:</strong> ${text(row.s57.object_class)} ${text(row.s57.geometry, "")}</div>
        <div class="small"><strong>S-52:</strong> ${text(row.s52.instruction)}</div>
        <div class="small"><strong>S-101:</strong> ${text(row.s101.feature_type || row.s101.direct_symbol_id || row.s101.mapping_type)}</div>
        <div class="small"><strong>Rule:</strong> ${text(row.s101.rule_file, "no rule file")}</div>
        <div class="small"><strong>Helm:</strong> ${text(row.helm.interpretation_status)} / ${text(row.helm.recipe_status)}</div>
        <div class="small"><strong>Style contract:</strong> ${text(style.status)} / ${text(style.gate_status)}</div>
      </div>
      <div class="images">
        ${image("Helm", row.images.helm.backend_url)}
        ${image("OpenCPN", row.images.opencpn.backend_url)}
        ${image("S-101", row.images.s101.backend_url)}
      </div>
      <div class="narrative">
        <div class="note small"><strong>S-57 description:</strong> ${text(row.s57.description)}</div>
        <div class="note small"><strong>Helm interpretation:</strong> ${text(interp.what_it_is || interp.clean_room_render_notes || row.helm.interpretation_status)}</div>
        <div class="note small"><strong>S-101 evidence:</strong> ${text(row.s101.portrayal_evidence)}</div>
        <div class="note small"><strong>Runtime gate:</strong> ${text(row.qa.runtime_gate_summary)}</div>
        <div class="note small"><strong>Style contract:</strong> ${text(style)}</div>
      </div>
    </div>
    <div class="review signoffPanel">
      <div class="wide"><label>Gate states</label><ul class="gateList">${gateList(row)}</ul></div>
      <div class="wide"><label>Missing evidence</label><div class="small">${missing.length ? esc(missing.join("; ")) : "none"}</div></div>
      <div class="wide"><label>Approval state</label><div class="small">${text(row.approval.state, "not reviewed")}</div></div>
      <div class="wide actions">
        <button type="button" disabled>${row.qa.runtime_eligible ? "Runtime eligible" : "Runtime blocked"}</button>
        <span class="rowSaveStatus">Approval writes use existing sign-off endpoints</span>
      </div>
    </div>
  </section>`;
}
function applyFilters() {
  const q = qEl.value.trim().toLowerCase();
  const status = statusFilterEl.value;
  const visible = allRows.filter(row => {
    const haystack = JSON.stringify(row).toLowerCase();
    return (!q || haystack.includes(q)) && (!status || row.status === status);
  });
  rowsEl.innerHTML = visible.map(renderRow).join("");
  document.getElementById("shownCount").textContent = visible.length;
}
async function loadRows() {
  statusEl.textContent = "Loading DB evidence...";
  try {
    const response = await fetch("/api/proof-review/rows?limit=100");
    if (!response.ok) throw new Error(await response.text());
    const payload = await response.json();
    if (payload.schema !== "helm.iconforge.db_review_api.v1") throw new Error(`unexpected schema ${payload.schema}`);
    allRows = payload.rows;
    statusEl.textContent = `Loaded ${payload.pagination.returned} rows from ${payload.summary.total_candidates} DB candidates; runtime eligible ${payload.summary.runtime_eligible}`;
    const statuses = [...new Set(allRows.map(row => row.status))].sort();
    statusFilterEl.innerHTML = `<option value="">all statuses</option>` + statuses.map(s => `<option value="${esc(s)}">${esc(s)}</option>`).join("");
    applyFilters();
  } catch (error) {
    statusEl.textContent = `DB evidence load failed: ${error}`;
    rowsEl.innerHTML = `<section class="row"><div class="note small"><strong>Failure:</strong> ${esc(error)}</div></section>`;
  }
}
qEl.addEventListener("input", applyFilters);
statusFilterEl.addEventListener("change", applyFilters);
loadRows();
"""
    body = f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<title>Helm Icon Forge DB Evidence Review</title>
<style>{_base_css_v2()}
.gateList {{ margin: 0; padding-left: 18px; }}
.gateList li {{ margin-bottom: 5px; }}
.gateList .blocked, .gateList .failed, .gateList .pending {{ color: var(--red); }}
.gateList .warn {{ color: #8a4b00; }}
.missingText {{ color: var(--red); }}
</style>
<header>
  <h1>Helm Icon Forge DB Evidence Review</h1>
  <div class="toolbar signoff">
    <input id="q" type="search" placeholder="Search DB evidence, mappings, gates">
    <select id="statusFilter"><option value="">all statuses</option></select>
    <a class="buttonLink" href="icon_review.html">Human review</a>
    <a class="buttonLink" href="pass_review.html">Final sign-off</a>
  </div>
  <div class="summary">
    <span>{_e(source_note)}</span>
    <span>Visible: <strong id="shownCount">0</strong></span>
    <span class="saveStatus" id="status">Not loaded</span>
  </div>
</header>
<main id="rows"></main>
<script>{js}</script>
</html>
"""
    DB_HTML_OUT.write_text(body)


def _signoff_card_v2(row: dict) -> str:
    haystack = " ".join([
        row["asset"], row["name"], row["status"], row["semantic_brief"], row["required_shape"],
        row["required_colours"], row["s57_object_class"], row["s57_conditions"],
    ]).lower()
    return f"""
<section class="row" data-asset="{_e(row['asset'])}" data-status="{_e(row['status'])}" data-candidate-revision="{_e(row['candidate_revision'])}" data-haystack="{_e(haystack)}">
  {_reference_report_v2(row)}
  <div class="review signoffPanel">
    <div>
      <label>Final decision</label>
      <select class="decision">
        <option value="pending">pending</option>
        <option value="approve">approve</option>
        <option value="reject_remediate">reject / remediate</option>
      </select>
    </div>
    <div class="small" style="padding-top: 24px;">Approve removes it from this queue; reject sends feedback to repair intake.</div>
    <div class="wide">
      <label>Human final-review feedback</label>
      <textarea class="signoffComment" placeholder="Approve, or explain what must go back to the repair queue."></textarea>
    </div>
    <div class="wide">
      <label>Expected change if rejected</label>
      <textarea class="expectedChange">{_e(row['expected_change'])}</textarea>
    </div>
    <div class="wide actions">
      <button class="approveRow primary" type="button">Approve</button>
      <button class="rejectRow" type="button">Reject to repair</button>
      <button class="submitSignoff" type="button">Save decision</button>
      <span class="rowSaveStatus">Not submitted</span>
    </div>
  </div>
</section>
"""


def _signoff_seed_state(rows: list[dict]) -> dict[str, dict]:
    if not SIGNOFF_JSON.exists():
        return {}
    try:
        payload = _read_json(SIGNOFF_JSON)
    except json.JSONDecodeError:
        return {}
    state = {}
    current_revisions = {row["asset"]: row.get("candidate_revision") or "" for row in rows}
    for row in payload.get("rows") or []:
        asset = row.get("asset")
        if not asset:
            continue
        if (row.get("candidate_revision") or "") != current_revisions.get(str(asset), ""):
            continue
        if row.get("final_decision") == "pending" and not row.get("feedback"):
            continue
        state[str(asset)] = row
    return state


def _write_pass_html(rows: list[dict], summary: dict) -> None:
    seed_state = json.dumps(_signoff_seed_state(rows), sort_keys=True)
    js = """
const storageKey = "helm.iconforge.humanSignoff.v1";
const serverState = __SERVER_STATE__;
let state = {{ ...loadState(), ...serverState }};
saveState();
function loadState() {
  try {{ return JSON.parse(localStorage.getItem(storageKey) || "{{}}"); }}
  catch (_) {{ return {{}}; }}
}
function saveState() {{ localStorage.setItem(storageKey, JSON.stringify(state)); }}
function rowEls() {{ return Array.from(document.querySelectorAll(".row")); }}
function hydrate() {{
  for (const rowEl of rowEls()) {
    const saved = state[rowEl.dataset.asset];
    if (!saved) continue;
    if ((saved.candidate_revision || "") !== (rowEl.dataset.candidateRevision || "")) {
      delete state[rowEl.dataset.asset];
      continue;
    }
    rowEl.querySelector(".decision").value = saved.final_decision || "pending";
    rowEl.querySelector(".signoffComment").value = saved.feedback || "";
    rowEl.querySelector(".expectedChange").value = saved.expected_change || "";
  }
}}
function collectRow(rowEl) {{
  return {{
    asset: rowEl.dataset.asset,
    candidate_revision: rowEl.dataset.candidateRevision || "",
    name: rowEl.querySelector("h2 .small")?.textContent.trim() || "",
    status: rowEl.dataset.status,
    final_decision: rowEl.querySelector(".decision").value,
    final_approved: rowEl.querySelector(".decision").value === "approve",
    needs_remediation: rowEl.querySelector(".decision").value === "reject_remediate",
    priority: rowEl.querySelector(".decision").value === "reject_remediate" ? "high" : "",
    reason_codes: rowEl.querySelector(".decision").value === "reject_remediate" ? "human_final_reject;final_approval_rejected" : "",
    feedback: rowEl.querySelector(".signoffComment").value,
    expected_change: rowEl.querySelector(".expectedChange").value
  }};
}}
function rememberRow(rowEl) {{
  const row = collectRow(rowEl);
  state[row.asset] = row;
  saveState();
  updateCounts();
}}
function updateCounts() {{
  const rows = rowEls().map(collectRow);
  document.getElementById("approvedCount").textContent = rows.filter(row => row.final_decision === "approve").length;
  document.getElementById("rejectedCount").textContent = rows.filter(row => row.final_decision === "reject_remediate").length;
}}
function applyFilters() {{
  const q = document.getElementById("q").value.trim().toLowerCase();
  const decision = document.getElementById("decisionFilter").value;
  let shown = 0;
  for (const rowEl of rowEls()) {
    const row = collectRow(rowEl);
    const haystack = [rowEl.dataset.haystack, row.feedback, row.expected_change].join(" ").toLowerCase();
    const visible = (!q || haystack.includes(q)) && (!decision || row.final_decision === decision);
    rowEl.classList.toggle("hidden", !visible);
    if (visible) shown += 1;
  }
  document.getElementById("shownCount").textContent = shown;
  updateCounts();
}}
async function saveSignoffRows(rows, statusEl) {{
  const status = document.getElementById("saveStatus");
  if (statusEl) statusEl.textContent = "Saving...";
  status.textContent = "Saving...";
  try {{
    const response = await fetch("/api/save-signoff", {
      method: "POST",
      headers: {{ "Content-Type": "application/json" }},
      body: JSON.stringify({{ schema: "helm.iconforge.human_signoff.v1", rows }})
    });
    if (!response.ok) throw new Error(await response.text());
    const result = await response.json();
    status.textContent = `Saved ${result.approved_rows} approvals, ${result.rejected_rows} repair rejections`;
    if (statusEl) statusEl.textContent = "Submitted";
    applyFilters();
  }} catch (error) {{
    status.textContent = "Server save failed";
    if (statusEl) statusEl.textContent = "Submit failed";
    console.error(error);
  }
}}
document.getElementById("rows").addEventListener("change", event => {{
  const rowEl = event.target.closest(".row");
  if (!rowEl) return;
  rememberRow(rowEl);
  applyFilters();
}});
document.getElementById("rows").addEventListener("input", event => {{
  const rowEl = event.target.closest(".row");
  if (rowEl) rememberRow(rowEl);
}});
document.getElementById("rows").addEventListener("click", event => {{
  const approve = event.target.closest(".approveRow");
  const reject = event.target.closest(".rejectRow");
  const button = event.target.closest(".submitSignoff, .approveRow, .rejectRow");
  if (!button) return;
  const rowEl = button.closest(".row");
  if (approve) {
    rowEl.querySelector(".decision").value = "approve";
  }
  if (reject) {
    rowEl.querySelector(".decision").value = "reject_remediate";
  }
  rememberRow(rowEl);
  saveSignoffRows([collectRow(rowEl)], rowEl.querySelector(".rowSaveStatus"));
}});
document.getElementById("q").addEventListener("input", applyFilters);
document.getElementById("decisionFilter").addEventListener("change", applyFilters);
document.getElementById("saveServer").addEventListener("click", () => saveSignoffRows(rowEls().map(collectRow)));
hydrate();
applyFilters();
"""
    js = js.replace("{{", "{").replace("}}", "}").replace("__SERVER_STATE__", seed_state)
    row_cards = "\n".join(_signoff_card_v2(row) for row in rows)
    body = f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<title>Helm Icon Forge Final Sign-Off</title>
<style>{_base_css_v2()}</style>
<header>
  <h1>Helm Icon Forge Final Sign-Off</h1>
  <div class="toolbar signoff">
    <input id="q" type="search" placeholder="Search asset, name, semantic brief">
    <select id="decisionFilter">
      <option value="">all decisions</option>
      <option value="pending" selected>pending queue</option>
      <option value="approve">approve</option>
      <option value="reject_remediate">reject / remediate</option>
    </select>
    <a class="buttonLink" href="icon_review.html">Back to remediation</a>
    <button id="saveServer" class="primary">Save all sign-offs</button>
  </div>
  <div class="summary">
    <span>Queue: {len(rows)} pass-pending-human rows</span>
    <span>Approve the day shape only; dusk/night are palette renders from the same SVG after approval.</span>
    <span>Visible: <strong id="shownCount">0</strong></span>
    <span>Approved: <strong id="approvedCount">0</strong></span>
    <span>Rejected: <strong id="rejectedCount">0</strong></span>
    <span class="saveStatus" id="saveStatus">Server save: not yet saved</span>
  </div>
</header>
<main id="rows">{row_cards}</main>
<script>{js}</script>
</html>
"""
    PASS_HTML_OUT.write_text(body)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args(argv)
    print(json.dumps(build(limit=args.limit), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
