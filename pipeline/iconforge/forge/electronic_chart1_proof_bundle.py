"""Build and serve the FORGE-46 Electronic Chart 1 proof bundle.

The browser page is intentionally thin: it fetches backend payloads and renders
them. It does not infer chart meaning, substitute static JSON, or promote rows
to runtime eligibility.

Run:
  python3 -m forge.electronic_chart1_proof_bundle
  python3 -m forge.electronic_chart1_proof_bundle --serve --port 9020
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import mimetypes
import shutil
from collections import Counter
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse


ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = ROOT.parent.parent
CATALOG = ROOT / "catalog"
DEFAULT_OUT = ROOT / "out" / "electronic_chart1_proof_bundle"
DEFAULT_CATALOG_JSON = CATALOG / "electronic_chart1_proof_bundle.json"
DEFAULT_CATALOG_MD = CATALOG / "electronic_chart1_proof_bundle.md"

DIFF_JSON = CATALOG / "electronic_chart1_diff_engine.json"
AUTHORITY_JSON = CATALOG / "electronic_chart1_authority_corpus.json"
OPENCPN_JSON = CATALOG / "electronic_chart1_opencpn_reference.json"
HELM_S57_JSON = CATALOG / "electronic_chart1_helm_s57_render.json"
HELM_S101_JSON = CATALOG / "electronic_chart1_helm_s101_render.json"

SCHEMA = "helm.forge.electronic_chart1_proof_bundle.v1"
API_SCHEMA = "helm.forge.electronic_chart1_proof_api.v1"
PALETTES = ("day", "dusk", "night")
REVIEW_CSV_FIELDS = [
    "row_key",
    "chart1_row_id",
    "decision",
    "needs_remediation",
    "feedback",
    "expected_change",
]


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _repo_path(value: str | None) -> Path | None:
    if not value:
        return None
    candidate = (ROOT / value).resolve()
    try:
        candidate.relative_to(ROOT.resolve())
    except ValueError:
        return None
    return candidate


def _safe(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in value).strip("_") or "row"


def _index_rows(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["row_key"]: row for row in payload.get("rows") or []}


def _index_all(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for bucket in ("rows", "hard_pile", "source_hard_pile"):
        for row in payload.get(bucket) or []:
            row_key = row.get("row_key")
            if row_key:
                rows[str(row_key)] = row
    return rows


def _section(authority_row: dict[str, Any], s101_row: dict[str, Any] | None) -> str:
    row_taxonomy = authority_row["row_taxonomy"]
    if row_taxonomy == "point_symbol":
        feature = ((s101_row or {}).get("s101_trace") or {}).get("feature_type") or ""
        row_key = authority_row["row_key"]
        if "Topmark" in feature or row_key.startswith(("TOPMAR_", "DAYMAR_")):
            return "topmarks_daymarks"
        return "point_symbols"
    if row_taxonomy == "line_style":
        return "line_styles"
    if row_taxonomy == "area_fill":
        return "area_fills"
    if row_taxonomy == "conditional_rule":
        return "conditional_rules"
    if row_taxonomy == "text_rule":
        return "text_rules"
    if row_taxonomy == "runtime_overlay":
        return "runtime_overlays"
    if row_taxonomy == "placeholder_manual":
        return "manual_placeholders"
    return row_taxonomy


def _copy_media(
    *,
    source_path: str | None,
    source_sha256: str | None,
    out_dir: Path,
    bucket: str,
    row_key: str,
    palette: str,
    copy_images: bool,
    copy_state: dict[str, int],
    image_copy_limit: int | None,
) -> dict[str, Any]:
    source = _repo_path(source_path)
    media = {
        "source_path": source_path,
        "source_sha256": source_sha256,
        "exists": bool(source and source.exists()),
        "copied": False,
        "url": None,
        "gap": None,
        "role": bucket,
    }
    if not media["exists"]:
        media["gap"] = f"media_missing:{bucket}:{palette}"
        return media
    if not copy_images:
        media["gap"] = f"media_not_copied:{bucket}:{palette}"
        return media
    if image_copy_limit is not None and copy_state["copied"] >= image_copy_limit:
        media["gap"] = f"media_copy_limit:{bucket}:{palette}"
        return media
    target = out_dir / "images" / bucket / f"{_safe(row_key)}__{palette}{source.suffix}"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    copy_state["copied"] += 1
    media.update({
        "copied": True,
        "url": target.relative_to(out_dir).as_posix(),
        "bundle_path": target.relative_to(out_dir).as_posix(),
        "bundle_sha256": _sha256(target),
    })
    return media


def _palette_media(
    *,
    diff_row: dict[str, Any],
    s101_row: dict[str, Any] | None,
    out_dir: Path,
    copy_images: bool,
    copy_state: dict[str, int],
    image_copy_limit: int | None,
) -> dict[str, Any]:
    s101_outputs = (((s101_row or {}).get("helm_candidate_render") or {}).get("palette_outputs") or {})
    media: dict[str, Any] = {}
    for diff in diff_row["palette_diffs"]:
        palette = diff["palette"]
        inputs = diff["inputs"]
        media[palette] = {
            "opencpn": _copy_media(
                source_path=inputs.get("opencpn_path"),
                source_sha256=inputs.get("opencpn_sha256"),
                out_dir=out_dir,
                bucket="opencpn",
                row_key=diff_row["row_key"],
                palette=palette,
                copy_images=copy_images,
                copy_state=copy_state,
                image_copy_limit=image_copy_limit,
            ),
            "helm_s57": _copy_media(
                source_path=inputs.get("helm_path"),
                source_sha256=inputs.get("helm_sha256"),
                out_dir=out_dir,
                bucket="helm-s57",
                row_key=diff_row["row_key"],
                palette=palette,
                copy_images=copy_images,
                copy_state=copy_state,
                image_copy_limit=image_copy_limit,
            ),
            "helm_s101": _copy_media(
                source_path=(s101_outputs.get(palette) or {}).get("path"),
                source_sha256=(s101_outputs.get(palette) or {}).get("sha256"),
                out_dir=out_dir,
                bucket="helm-s101",
                row_key=diff_row["row_key"],
                palette=palette,
                copy_images=copy_images,
                copy_state=copy_state,
                image_copy_limit=image_copy_limit,
            ),
            "visual_diff": _copy_media(
                source_path=(diff.get("diff_output") or {}).get("path"),
                source_sha256=(diff.get("diff_output") or {}).get("sha256"),
                out_dir=out_dir,
                bucket="visual-diff",
                row_key=diff_row["row_key"],
                palette=palette,
                copy_images=copy_images,
                copy_state=copy_state,
                image_copy_limit=image_copy_limit,
            ),
            "metrics": diff["metrics"],
            "visual_palette_gate": diff["gate"],
        }
    return media


def _media_gaps(media: dict[str, Any]) -> list[str]:
    gaps = []
    for palette_payload in media.values():
        for key in ("opencpn", "helm_s57", "helm_s101", "visual_diff"):
            gap = (palette_payload.get(key) or {}).get("gap")
            if gap:
                gaps.append(gap)
    return sorted(set(gaps))


def _review_controls(row_key: str) -> dict[str, Any]:
    return {
        "row_key": row_key,
        "feedback_endpoint": "/api/electronic-chart1-proof/feedback",
        "allowed_decisions": ["needs_repair", "evidence_gap", "visual_ok_not_runtime"],
        "runtime_approval_allowed": False,
        "reason": "FORGE-46 is proof review only; FORGE-47 owns runtime promotion.",
    }


def _verdict_row(
    *,
    authority_row: dict[str, Any],
    diff_row: dict[str, Any],
    s101_row: dict[str, Any] | None,
    out_dir: Path,
    copy_images: bool,
    copy_state: dict[str, int],
    image_copy_limit: int | None,
) -> dict[str, Any]:
    media = _palette_media(
        diff_row=diff_row,
        s101_row=s101_row,
        out_dir=out_dir,
        copy_images=copy_images,
        copy_state=copy_state,
        image_copy_limit=image_copy_limit,
    )
    visible_gaps = sorted(set(
        diff_row["visual_gate"].get("reason_codes", [])
        + diff_row["semantic_gate"].get("reason_codes", [])
        + diff_row["proof_gate"].get("reason_codes", [])
        + (authority_row.get("source_language_gaps") or [])
        + _media_gaps(media)
    ))
    return {
        "chart1_row_id": authority_row["chart1_row_id"],
        "s52_lookup_id": authority_row["s52_lookup_id"],
        "row_key": authority_row["row_key"],
        "row_taxonomy": authority_row["row_taxonomy"],
        "section": _section(authority_row, s101_row),
        "status": "proof_row",
        "display": {
            "title": authority_row["row_key"],
            "subtitle": authority_row.get("s57_object_class") or "",
            "authority_summary": (authority_row.get("helm_authority") or {}).get("text") or "",
            "helm_interpretation": (authority_row.get("helm_interpretation") or {}).get("sections") or {},
        },
        "gates": {
            "visual": diff_row["visual_gate"],
            "semantic": diff_row["semantic_gate"],
            "proof": diff_row["proof_gate"],
            "runtime": diff_row["runtime_gate"],
            "authority_status": (authority_row.get("helm_interpretation") or {}).get("status"),
            "human_review_status": (authority_row.get("helm_interpretation") or {}).get("review_status"),
        },
        "standards": {
            "s52": authority_row.get("s52_authority") or {},
            "s57": authority_row.get("s57_authority") or {},
            "s101": {
                "present": s101_row is not None,
                "trace": (s101_row or {}).get("s101_trace") or {},
                "colour_transform_authority": (s101_row or {}).get("colour_transform_authority") or {},
                "topmark_daymark_context": (s101_row or {}).get("topmark_daymark_context") or {},
            },
        },
        "media": media,
        "visible_gaps": visible_gaps,
        "review_controls": _review_controls(authority_row["row_key"]),
        "runtime_promotion_allowed": False,
    }


def _hard_pile_row(
    *,
    authority_row: dict[str, Any],
    diff_hard: dict[str, Any] | None,
    opencpn_row: dict[str, Any] | None,
    helm_s57_row: dict[str, Any] | None,
    s101_row: dict[str, Any] | None,
) -> dict[str, Any]:
    reasons = sorted(set(
        (diff_hard or {}).get("reason_codes", [])
        + (authority_row.get("source_language_gaps") or [])
    ))
    return {
        "chart1_row_id": authority_row["chart1_row_id"],
        "s52_lookup_id": authority_row["s52_lookup_id"],
        "row_key": authority_row["row_key"],
        "row_taxonomy": authority_row["row_taxonomy"],
        "section": _section(authority_row, s101_row),
        "status": "proof_hard_pile",
        "reason_codes": reasons,
        "available_inputs": {
            "authority": True,
            "opencpn_reference": opencpn_row is not None,
            "helm_s57_render": helm_s57_row is not None,
            "helm_s101_trace": s101_row is not None,
            "diff_verdict": False,
        },
        "display": {
            "title": authority_row["row_key"],
            "subtitle": authority_row.get("s57_object_class") or "",
            "authority_summary": (authority_row.get("helm_authority") or {}).get("text") or "",
            "helm_interpretation": (authority_row.get("helm_interpretation") or {}).get("sections") or {},
        },
        "gates": {
            "visual": {"gate": "red", "reason_codes": reasons},
            "semantic": {"gate": "red", "reason_codes": reasons},
            "proof": {
                "gate": "red",
                "reason_codes": reasons,
                "runtime_promoted": False,
                "runtime_promotion_allowed": False,
            },
            "runtime": {
                "runtime_eligible": False,
                "fail_closed": True,
                "runtime_promotion_allowed": False,
            },
            "authority_status": (authority_row.get("helm_interpretation") or {}).get("status"),
            "human_review_status": (authority_row.get("helm_interpretation") or {}).get("review_status"),
        },
        "standards": {
            "s52": authority_row.get("s52_authority") or {},
            "s57": authority_row.get("s57_authority") or {},
            "s101": {
                "present": s101_row is not None,
                "trace": (s101_row or {}).get("s101_trace") or {},
                "colour_transform_authority": (s101_row or {}).get("colour_transform_authority") or {},
                "topmark_daymark_context": (s101_row or {}).get("topmark_daymark_context") or {},
            },
        },
        "media": {},
        "visible_gaps": reasons,
        "review_controls": _review_controls(authority_row["row_key"]),
        "runtime_promotion_allowed": False,
    }


def _coverage(rows: list[dict[str, Any]], hard_pile: list[dict[str, Any]], copy_state: dict[str, int]) -> dict[str, Any]:
    all_rows = rows + hard_pile
    hard_reasons: Counter[str] = Counter()
    visible_gaps: Counter[str] = Counter()
    for row in hard_pile:
        hard_reasons.update(row["reason_codes"])
    for row in all_rows:
        visible_gaps.update(row.get("visible_gaps") or [])
    return {
        "authority_rows": len(all_rows),
        "proof_rows": len(rows),
        "hard_pile_rows": len(hard_pile),
        "runtime_eligible_rows": 0,
        "runtime_promotion_allowed_rows": 0,
        "section_counts": dict(sorted(Counter(row["section"] for row in all_rows).items())),
        "row_taxonomy_counts": dict(sorted(Counter(row["row_taxonomy"] for row in all_rows).items())),
        "visual_gate_counts": dict(sorted(Counter(row["gates"]["visual"]["gate"] for row in rows).items())),
        "semantic_gate_counts": dict(sorted(Counter(row["gates"]["semantic"]["gate"] for row in rows).items())),
        "proof_gate_counts": dict(sorted(Counter(row["gates"]["proof"]["gate"] for row in rows).items())),
        "hard_pile_reason_counts": dict(hard_reasons.most_common(60)),
        "visible_gap_counts": dict(visible_gaps.most_common(80)),
        "image_files_copied": copy_state["copied"],
        "missing_media_references": sum(
            1 for row in rows for gap in row.get("visible_gaps", []) if gap.startswith("media_missing:")
        ),
    }


def _manifest(
    *,
    coverage: dict[str, Any],
    source: dict[str, Any],
    out_dir: Path,
    copy_images: bool,
    image_copy_limit: int | None,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "proof_bundle_ready",
        "policy": {
            "backend_generated": True,
            "browser_business_logic_allowed": False,
            "static_json_fallback_allowed": False,
            "runtime_promotion_allowed": False,
            "missing_data_visible_alert_required": True,
            "opencpn_reference_role": "comparison_target_only",
            "helm_outputs_role": "generated_owned_candidate",
        },
        "local_server": {
            "module": "forge.electronic_chart1_proof_bundle",
            "command": "python3 -m forge.electronic_chart1_proof_bundle --serve --port 9020",
            "url": "http://127.0.0.1:9020/out/electronic_chart1_proof_bundle/index.html",
            "api": {
                "summary": "/api/electronic-chart1-proof/summary",
                "rows": "/api/electronic-chart1-proof/rows",
                "hard_pile": "/api/electronic-chart1-proof/hard-pile",
                "manifest": "/api/electronic-chart1-proof/manifest",
                "feedback": "/api/electronic-chart1-proof/feedback",
            },
        },
        "bundle": {
            "out_dir": _display_path(out_dir),
            "copy_images": copy_images,
            "image_copy_limit": image_copy_limit,
            "files": {
                "manifest": "manifest.json",
                "coverage": "coverage.json",
                "rows": "rows.json",
                "hard_pile": "hard-pile.json",
                "schema": "schema.json",
                "index": "index.html",
            },
        },
        "coverage": coverage,
        "source": source,
    }


def _schema() -> dict[str, Any]:
    return {
        "schema": "json-schema-lite",
        "title": SCHEMA,
        "required_top_level_files": [
            "manifest.json",
            "coverage.json",
            "rows.json",
            "hard-pile.json",
            "schema.json",
            "index.html",
        ],
        "row_required_fields": [
            "row_key",
            "row_taxonomy",
            "section",
            "gates",
            "standards",
            "media",
            "visible_gaps",
            "review_controls",
            "runtime_promotion_allowed",
        ],
        "frontend_contract": {
            "must_fetch_backend": True,
            "static_json_fallback_allowed": False,
            "business_logic_allowed": False,
            "visible_error_required": True,
        },
    }


def _index_html() -> str:
    return r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Electronic Chart 1 Proof Review</title>
  <style>
    :root{color-scheme:light;--border:#d4dbe6;--muted:#5f6b7a;--red:#b42318;--yellow:#9a6700;--green:#067647;--blue:#175cd3}
    *{box-sizing:border-box}body{margin:0;font-family:system-ui,-apple-system,Segoe UI,sans-serif;background:#f5f7fa;color:#182230}
    header{position:sticky;top:0;z-index:4;background:#fff;border-bottom:1px solid var(--border);padding:14px 18px}
    h1{font-size:22px;margin:0 0 8px}.summary{display:flex;flex-wrap:wrap;gap:8px}.pill{border:1px solid var(--border);border-radius:999px;background:#f8fafc;padding:4px 9px;font-size:13px}
    .toolbar{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}input,select,button,textarea{font:inherit;border:1px solid #bcc7d6;border-radius:6px;background:#fff;padding:8px}
    button{background:#175cd3;color:#fff;border-color:#175cd3;cursor:pointer}.secondary{background:#fff;color:#182230;border-color:#bcc7d6}
    main{padding:16px 18px}.alert{border:1px solid #f6c0b8;background:#fff3f0;color:#912018;border-radius:6px;padding:10px;margin:0 0 12px}.hidden{display:none!important}
    .tabs{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px}.tab{background:#fff;color:#182230;border-color:var(--border)}.tab.active{background:#182230;color:#fff}
    .row{display:grid;grid-template-columns:300px repeat(4,minmax(140px,1fr));gap:10px;background:#fff;border:1px solid var(--border);border-radius:8px;margin-bottom:12px;padding:12px}
    .row h2{font-size:17px;margin:0 0 6px}.meta{font-size:12px;color:var(--muted);line-height:1.35}.badge{display:inline-block;margin:2px 4px 2px 0;border-radius:999px;background:#edf2f7;padding:2px 7px;font-size:11px}
    .gate-red{background:#fff1f0;color:var(--red)}.gate-yellow{background:#fff8db;color:var(--yellow)}.gate-green{background:#e7f8ef;color:var(--green)}
    figure{margin:0;border:1px solid #e2e8f0;border-radius:6px;min-height:170px;padding:8px;display:flex;flex-direction:column;align-items:center;justify-content:center;background:#fff}
    figcaption{font-size:12px;font-weight:700;margin-bottom:6px}img{width:112px;height:112px;object-fit:contain;image-rendering:auto}.missing{font-size:12px;color:var(--red);padding:18px;text-align:center}
    details{margin-top:8px}.feedback{grid-column:1/-1;display:grid;grid-template-columns:220px 1fr 1fr auto;gap:8px;border-top:1px solid #edf1f5;padding-top:10px}
    @media(max-width:1100px){.row{grid-template-columns:1fr 1fr}.feedback{grid-template-columns:1fr}}
    @media(max-width:700px){.row{grid-template-columns:1fr}}
  </style>
</head>
<body data-framework="bootstrap-compatible">
<header>
  <h1>Electronic Chart 1 Proof Review</h1>
  <div id="summary" class="summary"></div>
  <div class="toolbar">
    <input id="q" type="search" placeholder="Search row, S-52, object, rule">
    <select id="gate"><option value="">all gates</option><option value="red">red</option><option value="yellow">yellow</option><option value="green">green</option></select>
    <select id="taxonomy"><option value="">all row types</option></select>
    <button id="refresh" class="secondary" type="button">Refresh</button>
    <a href="manifest.json">manifest</a>
    <a href="coverage.json">coverage</a>
    <a href="hard-pile.json">hard pile</a>
  </div>
</header>
<main>
  <div id="alert" class="alert hidden"></div>
  <nav id="tabs" class="tabs"></nav>
  <section id="rows"></section>
</main>
<script>
const API='/api/electronic-chart1-proof';
const state={section:'',q:'',gate:'',taxonomy:''};
const alertBox=document.getElementById('alert');
function showAlert(message){alertBox.textContent=message;alertBox.classList.remove('hidden');}
function clearAlert(){alertBox.classList.add('hidden');alertBox.textContent='';}
async function getJson(url){const res=await fetch(url,{headers:{'Accept':'application/json'}});if(!res.ok){throw new Error(`${res.status} ${res.statusText}`);}return await res.json();}
function pill(label,value){return `<span class="pill">${label} ${value}</span>`;}
function esc(v){return String(v ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function image(cell,label){if(!cell||!cell.url){return `<div class="missing">${esc((cell&&cell.gap)||'missing')}</div>`;}return `<img loading="lazy" src="${esc(cell.url)}" alt="${esc(label)}">`;}
function gateClass(g){return `badge gate-${esc(g||'red')}`;}
function renderSummary(summary){
  document.getElementById('summary').innerHTML=[
    pill('authority',summary.authority_rows),pill('proof rows',summary.proof_rows),pill('hard pile',summary.hard_pile_rows),
    pill('runtime eligible',summary.runtime_eligible_rows),pill('copied images',summary.image_files_copied)
  ].join('');
  const tax=document.getElementById('taxonomy');
  tax.innerHTML='<option value="">all row types</option>'+Object.keys(summary.row_taxonomy_counts||{}).map(k=>`<option value="${esc(k)}">${esc(k)}</option>`).join('');
  const tabs=document.getElementById('tabs');
  const sections=['',...Object.keys(summary.section_counts||{})];
  tabs.innerHTML=sections.map(s=>`<button type="button" class="tab ${state.section===s?'active':''}" data-section="${esc(s)}">${esc(s||'all')} ${(summary.section_counts||{})[s]||summary.authority_rows}</button>`).join('');
  tabs.querySelectorAll('button').forEach(b=>b.addEventListener('click',()=>{state.section=b.dataset.section;loadRows();}));
}
function renderRow(row){
  const day=(row.media||{}).day||{};
  const gates=row.gates||{};
  const gaps=(row.visible_gaps||[]).slice(0,8).map(g=>`<span class="badge gate-red">${esc(g)}</span>`).join('');
  return `<article class="row">
    <div><h2>${esc(row.row_key)}</h2><p class="meta">${esc(row.chart1_row_id)} · ${esc(row.row_taxonomy)} · ${esc(row.section)}</p>
      <span class="${gateClass(gates.visual&&gates.visual.gate)}">visual ${esc(gates.visual&&gates.visual.gate)}</span>
      <span class="${gateClass(gates.semantic&&gates.semantic.gate)}">semantic ${esc(gates.semantic&&gates.semantic.gate)}</span>
      <span class="${gateClass(gates.proof&&gates.proof.gate)}">proof ${esc(gates.proof&&gates.proof.gate)}</span>
      <p class="meta">runtime promotion: ${row.runtime_promotion_allowed?'allowed':'blocked'}</p>
      <details><summary>Evidence and gaps</summary><p class="meta">${esc(row.display&&row.display.authority_summary)}</p><div>${gaps||'<span class="badge gate-green">no visible gaps</span>'}</div></details>
    </div>
    <figure><figcaption>OpenCPN day</figcaption>${image(day.opencpn,'OpenCPN day')}<small class="meta">comparison target only</small></figure>
    <figure><figcaption>Helm S-57 day</figcaption>${image(day.helm_s57,'Helm S-57 day')}</figure>
    <figure><figcaption>Helm S-101 trace</figcaption>${image(day.helm_s101,'Helm S-101 trace')}<small class="meta">${esc(((row.standards||{}).s101||{}).trace && ((row.standards||{}).s101||{}).trace.classification)}</small></figure>
    <figure><figcaption>Visual diff</figcaption>${image(day.visual_diff,'Visual diff day')}<small class="meta">${esc(day.visual_palette_gate||'')}</small></figure>
    <form class="feedback" data-row="${esc(row.row_key)}">
      <select name="decision"><option value="needs_repair">needs repair</option><option value="evidence_gap">evidence gap</option><option value="visual_ok_not_runtime">visual OK, not runtime</option></select>
      <textarea name="feedback" placeholder="Reviewer feedback"></textarea>
      <textarea name="expected_change" placeholder="Expected repair or missing evidence"></textarea>
      <button type="submit">Save feedback</button>
    </form>
  </article>`;
}
async function loadRows(){
  clearAlert();
  const params=new URLSearchParams({limit:'80'});
  if(state.section)params.set('section',state.section); if(state.q)params.set('q',state.q); if(state.gate)params.set('gate',state.gate); if(state.taxonomy)params.set('taxonomy',state.taxonomy);
  try{
    const payload=await getJson(`${API}/rows?${params}`);
    if(payload.status!=='ok'){showAlert(payload.error||'backend returned non-ok status');return;}
    document.getElementById('rows').innerHTML=payload.rows.map(renderRow).join('')||'<div class="alert">No backend rows matched this filter.</div>';
    document.querySelectorAll('form.feedback').forEach(form=>form.addEventListener('submit',saveFeedback));
  }catch(err){showAlert(`Backend proof API is unavailable. No static JSON fallback is allowed. ${err.message}`);}
}
async function saveFeedback(ev){
  ev.preventDefault();
  const form=ev.currentTarget;
  const body={rows:[{row_key:form.dataset.row,decision:form.decision.value,feedback:form.feedback.value,expected_change:form.expected_change.value,needs_remediation:form.decision.value!=='visual_ok_not_runtime'}]};
  try{const res=await fetch(`${API}/feedback`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});if(!res.ok)throw new Error(await res.text());form.querySelector('button').textContent='Saved';}
  catch(err){showAlert(`Feedback save failed loudly: ${err.message}`);}
}
async function init(){
  try{const payload=await getJson(`${API}/summary`);renderSummary(payload.summary);await loadRows();}
  catch(err){showAlert(`Backend proof API is required. No static JSON fallback is allowed. ${err.message}`);}
}
document.getElementById('q').addEventListener('input',e=>{state.q=e.target.value;loadRows();});
document.getElementById('gate').addEventListener('change',e=>{state.gate=e.target.value;loadRows();});
document.getElementById('taxonomy').addEventListener('change',e=>{state.taxonomy=e.target.value;loadRows();});
document.getElementById('refresh').addEventListener('click',loadRows);
init();
</script>
</body>
</html>
"""


def _markdown(manifest: dict[str, Any]) -> str:
    c = manifest["coverage"]
    lines = [
        "# Electronic Chart 1 Proof Bundle",
        "",
        "FORGE-46 backend-fed proof UI/public bundle contract.",
        "",
        f"- schema: `{manifest['schema']}`",
        f"- status: `{manifest['status']}`",
        f"- authority_rows: `{c['authority_rows']}`",
        f"- proof_rows: `{c['proof_rows']}`",
        f"- hard_pile_rows: `{c['hard_pile_rows']}`",
        f"- runtime_eligible_rows: `{c['runtime_eligible_rows']}`",
        f"- image_files_copied: `{c['image_files_copied']}`",
        "",
        "## Policy",
        "",
        "- Browser business logic is forbidden; the page renders backend payloads.",
        "- Static JSON fallback is forbidden; backend/API failures are visible alerts.",
        "- OpenCPN images are comparison targets only.",
        "- Helm images are generated-owned candidates.",
        "- Runtime promotion remains blocked until FORGE-47.",
        "",
        "## Sections",
        "",
        "| Section | Count |",
        "| --- | ---: |",
    ]
    for section, count in c["section_counts"].items():
        lines.append(f"| `{section}` | {count} |")
    lines.extend(["", "## Hard Pile Reasons", "", "| Reason | Count |", "| --- | ---: |"])
    for reason, count in c["hard_pile_reason_counts"].items():
        lines.append(f"| `{reason}` | {count} |")
    return "\n".join(lines) + "\n"


def build_bundle(
    *,
    out_dir: Path = DEFAULT_OUT,
    catalog_json_path: Path | None = DEFAULT_CATALOG_JSON,
    catalog_markdown_path: Path | None = DEFAULT_CATALOG_MD,
    copy_images: bool = True,
    row_limit: int | None = None,
    image_copy_limit: int | None = None,
) -> dict[str, Any]:
    authority = _load_json(AUTHORITY_JSON)
    diff = _load_json(DIFF_JSON)
    opencpn = _load_json(OPENCPN_JSON)
    helm_s57 = _load_json(HELM_S57_JSON)
    helm_s101 = _load_json(HELM_S101_JSON)

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    diff_rows = _index_rows(diff)
    diff_all = _index_all(diff)
    opencpn_all = _index_all(opencpn)
    helm_s57_all = _index_all(helm_s57)
    helm_s101_all = _index_all(helm_s101)
    copy_state = {"copied": 0}
    rows: list[dict[str, Any]] = []
    hard_pile: list[dict[str, Any]] = []

    for authority_row in (authority.get("rows") or [])[:row_limit]:
        key = authority_row["row_key"]
        diff_row = diff_rows.get(key)
        s101_row = helm_s101_all.get(key)
        if diff_row:
            rows.append(_verdict_row(
                authority_row=authority_row,
                diff_row=diff_row,
                s101_row=s101_row,
                out_dir=out_dir,
                copy_images=copy_images,
                copy_state=copy_state,
                image_copy_limit=image_copy_limit,
            ))
            continue
        hard_pile.append(_hard_pile_row(
            authority_row=authority_row,
            diff_hard=diff_all.get(key),
            opencpn_row=opencpn_all.get(key),
            helm_s57_row=helm_s57_all.get(key),
            s101_row=s101_row,
        ))

    source = {
        "authority_corpus": {"path": _display_path(AUTHORITY_JSON), "schema": authority["schema"], "sha256": _sha256(AUTHORITY_JSON)},
        "diff_engine": {"path": _display_path(DIFF_JSON), "schema": diff["schema"], "sha256": _sha256(DIFF_JSON)},
        "opencpn_reference": {"path": _display_path(OPENCPN_JSON), "schema": opencpn["schema"], "sha256": _sha256(OPENCPN_JSON)},
        "helm_s57_render": {"path": _display_path(HELM_S57_JSON), "schema": helm_s57["schema"], "sha256": _sha256(HELM_S57_JSON)},
        "helm_s101_render": {"path": _display_path(HELM_S101_JSON), "schema": helm_s101["schema"], "sha256": _sha256(HELM_S101_JSON)},
    }
    coverage = _coverage(rows, hard_pile, copy_state)
    manifest = _manifest(
        coverage=coverage,
        source=source,
        out_dir=out_dir,
        copy_images=copy_images,
        image_copy_limit=image_copy_limit,
    )
    _write_json(out_dir / "manifest.json", manifest)
    _write_json(out_dir / "coverage.json", coverage)
    _write_json(out_dir / "rows.json", {"schema": SCHEMA, "status": "ok", "rows": rows})
    _write_json(out_dir / "hard-pile.json", {"schema": SCHEMA, "status": "ok", "rows": hard_pile})
    _write_json(out_dir / "schema.json", _schema())
    (out_dir / "index.html").write_text(_index_html())

    if catalog_json_path:
        _write_json(catalog_json_path, manifest)
    if catalog_markdown_path:
        catalog_markdown_path.parent.mkdir(parents=True, exist_ok=True)
        catalog_markdown_path.write_text(_markdown(manifest))

    return {
        "status": "proof_bundle_written",
        "out_dir": _display_path(out_dir),
        "manifest": _display_path(out_dir / "manifest.json"),
        "coverage": coverage,
        "catalog_json": _display_path(catalog_json_path) if catalog_json_path else None,
        "catalog_markdown": _display_path(catalog_markdown_path) if catalog_markdown_path else None,
    }


def _load_bundle(out_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    if not (out_dir / "manifest.json").exists():
        build_bundle(out_dir=out_dir)
    manifest = _load_json(out_dir / "manifest.json")
    rows = _load_json(out_dir / "rows.json").get("rows") or []
    hard_pile = _load_json(out_dir / "hard-pile.json").get("rows") or []
    return manifest, rows, hard_pile


def api_summary(out_dir: Path = DEFAULT_OUT) -> dict[str, Any]:
    manifest, _, _ = _load_bundle(out_dir)
    return {
        "schema": API_SCHEMA,
        "status": "ok",
        "summary": manifest["coverage"],
        "source": manifest["source"],
        "policy": manifest["policy"],
    }


def api_manifest(out_dir: Path = DEFAULT_OUT) -> dict[str, Any]:
    manifest, _, _ = _load_bundle(out_dir)
    return {
        "schema": API_SCHEMA,
        "status": "ok",
        "manifest": manifest,
    }


def _matches(row: dict[str, Any], params: dict[str, list[str]]) -> bool:
    taxonomy = (params.get("taxonomy") or [""])[0]
    section = (params.get("section") or [""])[0]
    gate = (params.get("gate") or [""])[0]
    query = (params.get("q") or [""])[0].lower().strip()
    if taxonomy and row.get("row_taxonomy") != taxonomy:
        return False
    if section and row.get("section") != section:
        return False
    if gate and (row.get("gates") or {}).get("proof", {}).get("gate") != gate:
        return False
    if query:
        haystack = json.dumps({
            "row_key": row.get("row_key"),
            "s52": row.get("standards", {}).get("s52"),
            "s57": row.get("standards", {}).get("s57"),
            "s101": row.get("standards", {}).get("s101", {}).get("trace"),
            "display": row.get("display"),
            "gaps": row.get("visible_gaps"),
        }, sort_keys=True).lower()
        if query not in haystack:
            return False
    return True


def api_rows(query: str = "", out_dir: Path = DEFAULT_OUT) -> dict[str, Any]:
    _, rows, hard_pile = _load_bundle(out_dir)
    params = parse_qs(query)
    limit = max(0, min(int((params.get("limit") or ["80"])[0]), 500))
    offset = max(0, int((params.get("offset") or ["0"])[0]))
    include_hard = (params.get("include_hard_pile") or ["true"])[0] != "false"
    pool = rows + hard_pile if include_hard else rows
    filtered = [row for row in pool if _matches(row, params)]
    return {
        "schema": API_SCHEMA,
        "status": "ok",
        "pagination": {
            "offset": offset,
            "limit": limit,
            "total_matching": len(filtered),
            "returned": len(filtered[offset:offset + limit]),
        },
        "rows": filtered[offset:offset + limit],
    }


def api_hard_pile(query: str = "", out_dir: Path = DEFAULT_OUT) -> dict[str, Any]:
    _, _, hard_pile = _load_bundle(out_dir)
    params = parse_qs(query)
    limit = max(0, min(int((params.get("limit") or ["200"])[0]), 1000))
    offset = max(0, int((params.get("offset") or ["0"])[0]))
    filtered = [row for row in hard_pile if _matches(row, params)]
    return {
        "schema": API_SCHEMA,
        "status": "ok",
        "pagination": {
            "offset": offset,
            "limit": limit,
            "total_matching": len(filtered),
            "returned": len(filtered[offset:offset + limit]),
        },
        "rows": filtered[offset:offset + limit],
    }


def _write_feedback(out_dir: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    feedback_path = out_dir / "feedback.json"
    existing = {}
    if feedback_path.exists():
        existing_payload = _load_json(feedback_path)
        existing = {row["row_key"]: row for row in existing_payload.get("rows") or [] if row.get("row_key")}
    for row in rows:
        row_key = row.get("row_key")
        if not row_key:
            raise ValueError("feedback row missing row_key")
        existing[str(row_key)] = {
            "row_key": row_key,
            "chart1_row_id": row.get("chart1_row_id") or "",
            "decision": row.get("decision") or "needs_repair",
            "needs_remediation": bool(row.get("needs_remediation", True)),
            "feedback": row.get("feedback") or "",
            "expected_change": row.get("expected_change") or "",
        }
    merged = [existing[key] for key in sorted(existing)]
    payload = {
        "schema": "helm.forge.electronic_chart1_feedback.v1",
        "rows": merged,
        "count": len(merged),
    }
    _write_json(feedback_path, payload)
    csv_path = out_dir / "feedback.csv"
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in merged:
            writer.writerow({field: row.get(field, "") for field in REVIEW_CSV_FIELDS})
    return {
        "schema": API_SCHEMA,
        "status": "saved",
        "rows": len(merged),
        "submitted_rows": len(rows),
        "feedback_json": feedback_path.relative_to(out_dir).as_posix(),
        "feedback_csv": csv_path.relative_to(out_dir).as_posix(),
    }


class ElectronicChart1ProofHandler(SimpleHTTPRequestHandler):
    bundle_out_dir = DEFAULT_OUT

    def do_GET(self) -> None:  # noqa: N802 - http.server API
        parsed = urlparse(self.path)
        if parsed.path == "/api/electronic-chart1-proof/summary":
            self._json(200, api_summary(self.bundle_out_dir))
            return
        if parsed.path == "/api/electronic-chart1-proof/manifest":
            self._json(200, api_manifest(self.bundle_out_dir))
            return
        if parsed.path == "/api/electronic-chart1-proof/rows":
            self._json(200, api_rows(parsed.query, self.bundle_out_dir))
            return
        if parsed.path == "/api/electronic-chart1-proof/hard-pile":
            self._json(200, api_hard_pile(parsed.query, self.bundle_out_dir))
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802 - http.server API
        parsed = urlparse(self.path)
        if parsed.path != "/api/electronic-chart1-proof/feedback":
            self.send_error(404, "unknown endpoint")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            response = _write_feedback(self.bundle_out_dir, payload.get("rows") or [])
        except Exception as exc:  # noqa: BLE001 - visible fail-loud browser response.
            self._json(400, {"schema": API_SCHEMA, "status": "error", "error": str(exc)})
            return
        self._json(200, response)

    def translate_path(self, path: str) -> str:
        parsed = urlparse(path)
        relative = unquote(parsed.path).lstrip("/")
        target = (ROOT / relative).resolve()
        try:
            target.relative_to(ROOT.resolve())
        except ValueError:
            return str(ROOT)
        return str(target)

    def _json(self, status_code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def guess_type(self, path: str) -> str:
        if path.endswith(".svg"):
            return "image/svg+xml"
        return mimetypes.guess_type(path)[0] or "application/octet-stream"


def serve(host: str, port: int, out_dir: Path, *, build_first: bool = True, copy_images: bool = True) -> None:
    if build_first or not (out_dir / "manifest.json").exists():
        build_bundle(out_dir=out_dir, copy_images=copy_images)
    ElectronicChart1ProofHandler.bundle_out_dir = out_dir
    server = ThreadingHTTPServer((host, port), ElectronicChart1ProofHandler)
    print(f"serving http://{host}:{port}/out/electronic_chart1_proof_bundle/index.html")
    print(f"summary http://{host}:{port}/api/electronic-chart1-proof/summary")
    server.serve_forever()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--json", type=Path, default=DEFAULT_CATALOG_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_CATALOG_MD)
    parser.add_argument("--no-copy-images", action="store_true")
    parser.add_argument("--row-limit", type=int)
    parser.add_argument("--image-copy-limit", type=int)
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--no-build", action="store_true")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9020)
    args = parser.parse_args(argv)
    copy_images = not args.no_copy_images
    if args.serve:
        serve(args.host, args.port, args.out, build_first=not args.no_build, copy_images=copy_images)
        return 0
    result = build_bundle(
        out_dir=args.out,
        catalog_json_path=args.json,
        catalog_markdown_path=args.markdown,
        copy_images=copy_images,
        row_limit=args.row_limit,
        image_copy_limit=args.image_copy_limit,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
