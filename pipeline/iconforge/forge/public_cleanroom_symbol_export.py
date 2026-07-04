"""Build the public clean-room symbol package surface.

FORGE-53 is the publish/package gate. It does not promote runtime symbols and
does not turn OpenCPN or S-101 reference material into Helm-owned artwork. It
exports the machine registry, proof coverage, a hard-pile, and a lightweight
comparison page backed by generated proof data.

Run:
  python3 -m forge.public_cleanroom_symbol_export
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from . import cleanroom_symbol_manifest
from . import electronic_chart1_proof_bundle
from . import electronic_chart1_runtime_promotion_gate


ROOT = Path(__file__).resolve().parent.parent
PROOF_DIR = ROOT / "proof"
REGISTRY_JSON = ROOT / "registry" / "symbols.json"
REGISTRY_SCHEMA = ROOT / "registry" / "symbol.schema.json"
RUNTIME_GATE_JSON = ROOT / "catalog" / "electronic_chart1_runtime_promotion_gate.json"
DEFAULT_PROOF_BUNDLE_DIR = ROOT / "out" / "electronic_chart1_proof_bundle"

SCHEMA = "helm.forge.public_cleanroom_symbol_package.v1"
PROOF_DATA_SCHEMA = "helm.forge.public_cleanroom_symbol_proof_data.v1"


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_canonical_json(payload))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"required public-package artifact is missing: {path}")
    return json.loads(path.read_text())


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _proof_url(source_path: str | None) -> str | None:
    if not source_path:
        return None
    return "../" + source_path.lstrip("/")


def _symbol_id(row: dict[str, Any]) -> str | None:
    tuple_payload = (((row.get("standards") or {}).get("s57") or {}).get("attribute_tuple") or {})
    symbol = tuple_payload.get("s52_symbol_id")
    if symbol:
        return str(symbol)
    refs = (((row.get("standards") or {}).get("s52") or {}).get("refs") or {})
    for key in ("symbols", "area_patterns", "line_styles"):
        values = refs.get(key) or []
        if values:
            return str(values[0])
    return None


def _svg_palette_paths(symbol_id: str | None) -> dict[str, str | None]:
    if not symbol_id:
        return {"day": None, "dusk": None, "night": None}
    out: dict[str, str | None] = {}
    for palette in ("day", "dusk", "night"):
        path = PROOF_DIR / f"svg-{palette}" / f"{symbol_id}.svg"
        out[palette] = f"svg-{palette}/{symbol_id}.svg" if path.exists() else None
    return out


def _media_triplet(row: dict[str, Any], role: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for palette in ("day", "dusk", "night"):
        media = (((row.get("media") or {}).get(palette) or {}).get(role) or {})
        out[palette] = {
            "url": _proof_url(media.get("source_path")),
            "source_path": media.get("source_path"),
            "source_sha256": media.get("source_sha256"),
            "exists": bool(media.get("exists")),
            "gap": media.get("gap"),
        }
    return out


def _index_runtime_blockers(runtime_gate: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row["row_key"]): row for row in runtime_gate.get("blocked_rows") or []}


def _proof_record(row: dict[str, Any], runtime_blocker: dict[str, Any] | None) -> dict[str, Any]:
    symbol_id = _symbol_id(row)
    s101_trace = (((row.get("standards") or {}).get("s101") or {}).get("trace") or {})
    gates = row.get("gates") or {}
    return {
        "chart1_row_id": row.get("chart1_row_id"),
        "row_key": row.get("row_key"),
        "s52_lookup_id": row.get("s52_lookup_id"),
        "symbol_id": symbol_id,
        "row_taxonomy": row.get("row_taxonomy"),
        "section": row.get("section"),
        "status": row.get("status"),
        "display": row.get("display") or {},
        "gates": gates,
        "runtime": {
            "eligible": False,
            "promotion_allowed": False,
            "release_gate": "blocked_until_FORGE47_runtime_gate_and_human_approval_pass",
            "reason_codes": (runtime_blocker or {}).get("reason_codes") or row.get("reason_codes") or [],
            "remediation_hints": (runtime_blocker or {}).get("remediation_hints") or [],
        },
        "standards": {
            "s52": ((row.get("standards") or {}).get("s52") or {}),
            "s57": ((row.get("standards") or {}).get("s57") or {}),
            "s101_trace": {
                "present": ((row.get("standards") or {}).get("s101") or {}).get("present"),
                "classification": s101_trace.get("classification"),
                "mapping_type": s101_trace.get("mapping_type"),
                "resolver_status": s101_trace.get("resolver_status"),
                "feature_type": s101_trace.get("feature_type"),
                "rule_file": s101_trace.get("rule_file"),
                "db_backed": s101_trace.get("db_backed"),
                "filename_only_match": s101_trace.get("filename_only_match"),
            },
        },
        "assets": {
            "helm_svg_palettes": _svg_palette_paths(symbol_id),
            "helm_s57_render": _media_triplet(row, "helm_s57"),
            "helm_s101_render": _media_triplet(row, "helm_s101"),
            "opencpn_reference": _media_triplet(row, "opencpn"),
            "visual_diff": _media_triplet(row, "visual_diff"),
        },
        "clean_room_boundary": {
            "helm_outputs_role": "generated_owned_candidate",
            "opencpn_role": "comparison_target_only",
            "s101_role": "standards_vocabulary_and_rule_trace_only",
            "runtime_promotion": "fail_closed",
        },
    }


def _proof_rows(proof_dir: Path, runtime_gate: dict[str, Any]) -> list[dict[str, Any]]:
    rows_payload = _load_json(proof_dir / "rows.json")
    hard_payload = _load_json(proof_dir / "hard-pile.json")
    blockers = _index_runtime_blockers(runtime_gate)
    rows = []
    for row in (rows_payload.get("rows") or []) + (hard_payload.get("rows") or []):
        rows.append(_proof_record(row, blockers.get(str(row.get("row_key")))))
    return sorted(rows, key=lambda item: (item.get("section") or "", item.get("row_key") or ""))


def _coverage(rows: list[dict[str, Any]], registry: dict[str, Any], runtime_gate: dict[str, Any]) -> dict[str, Any]:
    status_counts = Counter(row["status"] for row in rows)
    taxonomy_counts = Counter(row["row_taxonomy"] for row in rows)
    section_counts = Counter(row["section"] for row in rows)
    s101_counts = Counter((row["standards"]["s101_trace"].get("classification") or "missing") for row in rows)
    proof_gate_counts = Counter(((row.get("gates") or {}).get("proof") or {}).get("gate") for row in rows)
    rows_with_svg = sum(
        1
        for row in rows
        if any((row.get("assets") or {}).get("helm_svg_palettes", {}).values())
    )
    return {
        "total_rows": len(rows),
        "registry_symbols": registry["summary"]["symbols"],
        "registry_blocked_candidates": registry["summary"]["blocked_non_symbol_candidates"],
        "runtime_export_rows": runtime_gate["summary"]["runtime_export_rows"],
        "runtime_blocked_rows": runtime_gate["summary"]["blocked_rows"],
        "rows_with_committed_svg_palette": rows_with_svg,
        "status_counts": dict(sorted(status_counts.items())),
        "row_taxonomy_counts": dict(sorted(taxonomy_counts.items())),
        "section_counts": dict(sorted(section_counts.items())),
        "s101_classification_counts": dict(sorted(s101_counts.items())),
        "proof_gate_counts": dict(sorted((str(k), v) for k, v in proof_gate_counts.items())),
        "gate_status": "release_blocked" if runtime_gate["summary"]["runtime_export_rows"] == 0 else "contains_runtime_rows",
        "gate_blockers": [
            "runtime_export_rows_zero",
            "human_review_pending",
            "visual_or_semantic_diff_not_all_green",
            "hard_pile_not_empty",
        ],
    }


def _manifest(
    *,
    coverage: dict[str, Any],
    registry: dict[str, Any],
    runtime_gate: dict[str, Any],
    proof_bundle_manifest: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "public_review_package_release_blocked",
        "name": "Helm Clean-room Maritime Symbol Package",
        "purpose": "Public proof/export surface for generated Helm symbol assets, mappings, palettes, and runtime gates.",
        "forum_packaging_decision": {
            "package_first": True,
            "not_a_new_official_standard": True,
            "opencpn_comparison_target_only": True,
            "s101_reference_trace_not_bundled_artwork": True,
            "runtime_release_gate": "FORGE-47 runtime promotion gate",
            "visual_page": "proof/compare-opencpn.html",
        },
        "registry_manifest": {
            "path": "registry/symbols.json",
            "schema": registry["schema"],
            "summary": registry["summary"],
        },
        "proof_bundle": {
            "path": "proof/package-proof-data.json",
            "source_schema": proof_bundle_manifest.get("schema"),
            "source_coverage": proof_bundle_manifest.get("coverage"),
        },
        "runtime_gate": {
            "path": "catalog/electronic_chart1_runtime_promotion_gate.json",
            "schema": runtime_gate["schema"],
            "summary": runtime_gate["summary"],
        },
        "render_targets": cleanroom_symbol_manifest.RENDER_TARGETS,
        "standards_profile": {
            "s52": "symbol vocabulary and S-52 instruction evidence",
            "s57": "object class and attribute vocabulary",
            "s101": "resolver trace, feature/rule evidence, and comparison render where available",
            "opencpn": "comparison render only; never source artwork",
        },
        "source_boundary": {
            "generated_outputs": "Helm-owned SVG assets, palette SVGs, and generated proof renders",
            "comparison_references": "OpenCPN render outputs and S-101 rule names are evidence only",
            "forbidden_canonical_sources": [
                "OpenCPN raster or GPL artwork copied as Helm canonical artwork",
                "IHO S-101 official SVG/Lua/catalogue files copied as Helm canonical artwork",
                "private ENC/S-63/oeSENC content",
            ],
        },
        "coverage": coverage,
    }


def _source_boundary_markdown() -> str:
    return """# Source Boundary

This package is a clean-room public review/export surface.

- Helm SVG assets, palette SVGs, generated recipes, and generated proof renders are Helm-owned candidate outputs.
- OpenCPN renders are comparison targets only. They are not canonical Helm artwork.
- S-52, S-57, and S-101 names, object classes, attributes, and rule references are standards vocabulary/evidence.
- S-101 SVG, Lua, catalogue XML, OpenCPN artwork, private ENC, S-63, and oeSENC files must not be bundled as Helm-owned source artwork.
- Runtime/package release remains fail-closed until the FORGE-47 promotion gate and human/QA approval pass.

The comparison page is meant to help reviewers inspect credibility and gaps. It is not an ECDIS certification claim.
"""


def _readme_markdown() -> str:
    return """# Helm Clean-room Symbol Proof Package

This directory is the public proof surface for the generated Helm maritime symbol package.

Open `compare-opencpn.html` after running the Forge proof generators. The page loads
`package-proof-data.json` and renders each row with:

- OpenCPN comparison images where available.
- Helm S-57 generated day/dusk/night renders.
- Helm S-101 trace/render evidence where available.
- Committed Helm SVG palette assets where available.
- Runtime gate reasons and remediation hints.

The page does not approve runtime use. Runtime export is blocked by the FORGE-47 gate until every row has the required proof, provenance, and approval.
"""


def _comparison_html() -> str:
    return r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Helm Clean-room Symbol Proof</title>
  <style>
    :root{color-scheme:light;--border:#d6dee8;--muted:#5f6b7a;--red:#b42318;--yellow:#9a6700;--green:#067647;--blue:#175cd3}
    *{box-sizing:border-box}body{margin:0;font-family:system-ui,-apple-system,Segoe UI,sans-serif;background:#f5f7fa;color:#182230}
    header{position:sticky;top:0;z-index:3;background:#fff;border-bottom:1px solid var(--border);padding:14px 18px}
    h1{font-size:22px;margin:0 0 8px}.summary{display:flex;flex-wrap:wrap;gap:8px}.pill{border:1px solid var(--border);border-radius:999px;background:#f8fafc;padding:4px 9px;font-size:13px}
    .toolbar{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}input,select,button{font:inherit;border:1px solid #bcc7d6;border-radius:6px;background:#fff;padding:8px}
    button{background:#175cd3;color:#fff;border-color:#175cd3;cursor:pointer}.secondary{background:#fff;color:#182230;border-color:#bcc7d6}
    main{padding:16px 18px}.alert{border:1px solid #f6c0b8;background:#fff3f0;color:#912018;border-radius:6px;padding:10px;margin:0 0 12px}.hidden{display:none!important}
    .row{display:grid;grid-template-columns:300px repeat(4,minmax(180px,1fr));gap:10px;background:#fff;border:1px solid var(--border);border-radius:8px;margin-bottom:12px;padding:12px}
    .row h2{font-size:17px;margin:0 0 6px}.meta{font-size:12px;color:var(--muted);line-height:1.35}.badge{display:inline-block;margin:2px 4px 2px 0;border-radius:999px;background:#edf2f7;padding:2px 7px;font-size:11px}
    .gate-red{background:#fff1f0;color:var(--red)}.gate-yellow{background:#fff8db;color:var(--yellow)}.gate-green{background:#e7f8ef;color:var(--green)}
    figure{margin:0;border:1px solid #e2e8f0;border-radius:6px;min-height:210px;padding:8px;background:#fff}
    figcaption{font-size:12px;font-weight:700;margin-bottom:8px}.strip{display:flex;gap:6px;justify-content:center;align-items:flex-start;flex-wrap:wrap}
    .tile{width:54px;text-align:center}.tile img{width:48px;height:48px;object-fit:contain;border:1px solid #edf1f5;border-radius:4px;background:#fff}.tile span{display:block;font-size:10px;color:#667085;margin-top:2px}
    .missing{font-size:11px;color:var(--red);border:1px dashed #efc6bd;border-radius:4px;padding:12px 4px}.reason{max-height:96px;overflow:auto}
    @media(max-width:1200px){.row{grid-template-columns:1fr 1fr}}@media(max-width:720px){.row{grid-template-columns:1fr}}
  </style>
</head>
<body>
<header>
  <h1>Helm Clean-room Symbol Proof</h1>
  <div id="summary" class="summary"></div>
  <div class="toolbar">
    <input id="q" type="search" placeholder="Search row, symbol, object, S-101 rule">
    <select id="section"><option value="">all sections</option></select>
    <select id="gate"><option value="">all proof gates</option><option value="green">green</option><option value="yellow">yellow</option><option value="red">red</option></select>
    <button id="prev" class="secondary" type="button">Prev</button>
    <button id="next" class="secondary" type="button">Next</button>
    <span id="page" class="pill">page</span>
    <button id="refresh" class="secondary" type="button">Refresh</button>
    <a href="manifest.json">manifest</a>
    <a href="coverage.json">coverage</a>
    <a href="missing-hard-pile.json">hard pile</a>
    <a href="../registry/symbols.json">registry</a>
  </div>
</header>
<main>
  <div id="alert" class="alert hidden"></div>
  <section id="rows"></section>
</main>
<script>
const state={q:'',section:'',gate:'',offset:0,pageSize:150};
const alertBox=document.getElementById('alert');
let data=null;
function esc(v){return String(v ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function showAlert(message){alertBox.textContent=message;alertBox.classList.remove('hidden');}
function pill(label,value){return `<span class="pill">${esc(label)} ${esc(value)}</span>`;}
function gateClass(g){return `badge gate-${esc(g||'red')}`;}
function imageTile(label,item){if(!item||!item.url){return `<div class="tile"><div class="missing">missing</div><span>${esc(label)}</span></div>`;}return `<div class="tile"><img loading="lazy" src="${esc(item.url)}" alt="${esc(label)}"><span>${esc(label)}</span></div>`;}
function svgTile(label,path){if(!path){return `<div class="tile"><div class="missing">none</div><span>${esc(label)}</span></div>`;}return `<div class="tile"><img loading="lazy" src="${esc(path)}" alt="${esc(label)}"><span>${esc(label)}</span></div>`;}
function stripFromTriplet(triplet){return `<div class="strip">${['day','dusk','night'].map(p=>imageTile(p,triplet&&triplet[p])).join('')}</div>`;}
function stripFromSvg(map){return `<div class="strip">${['day','dusk','night'].map(p=>svgTile(p,map&&map[p])).join('')}</div>`;}
function renderSummary(){
  const c=data.coverage||{};
  document.getElementById('summary').innerHTML=[
    pill('rows',c.total_rows),pill('registry symbols',c.registry_symbols),pill('runtime export',c.runtime_export_rows),
    pill('blocked',c.runtime_blocked_rows),pill('svg palettes',c.rows_with_committed_svg_palette)
  ].join('');
  const section=document.getElementById('section');
  section.innerHTML='<option value="">all sections</option>'+Object.keys(c.section_counts||{}).map(k=>`<option value="${esc(k)}">${esc(k)}</option>`).join('');
}
function matches(row){
  if(state.section && row.section!==state.section)return false;
  const proof=(row.gates&&row.gates.proof&&row.gates.proof.gate)||'red';
  if(state.gate && proof!==state.gate)return false;
  if(state.q){
    const text=JSON.stringify({row_key:row.row_key,symbol_id:row.symbol_id,display:row.display,standards:row.standards,runtime:row.runtime}).toLowerCase();
    if(!text.includes(state.q.toLowerCase()))return false;
  }
  return true;
}
function updatePage(total,shown){
  document.getElementById('page').textContent=`${state.offset+1}-${state.offset+shown} of ${total}`;
  document.getElementById('prev').disabled=state.offset===0;
  document.getElementById('next').disabled=state.offset+state.pageSize>=total;
}
function renderRow(row){
  const proof=(row.gates&&row.gates.proof)||{};
  const visual=(row.gates&&row.gates.visual)||{};
  const semantic=(row.gates&&row.gates.semantic)||{};
  const s101=(row.standards&&row.standards.s101_trace)||{};
  const reasons=(row.runtime&&row.runtime.reason_codes||[]).slice(0,10).map(r=>`<span class="badge gate-red">${esc(r)}</span>`).join('');
  return `<article class="row">
    <div>
      <h2>${esc(row.symbol_id||row.row_key)}</h2>
      <p class="meta">${esc(row.row_key)}<br>${esc(row.row_taxonomy)} / ${esc(row.section)}</p>
      <span class="${gateClass(visual.gate)}">visual ${esc(visual.gate||'missing')}</span>
      <span class="${gateClass(semantic.gate)}">semantic ${esc(semantic.gate||'missing')}</span>
      <span class="${gateClass(proof.gate)}">proof ${esc(proof.gate||'missing')}</span>
      <p class="meta"><b>S-101:</b> ${esc(s101.classification)} / ${esc(s101.mapping_type)}<br><b>Rule:</b> ${esc(s101.rule_file||'none')}<br><b>Runtime:</b> blocked</p>
      <div class="reason">${reasons}</div>
    </div>
    <figure><figcaption>OpenCPN comparison</figcaption>${stripFromTriplet(row.assets&&row.assets.opencpn_reference)}<small class="meta">comparison target only</small></figure>
    <figure><figcaption>Helm SVG palette</figcaption>${stripFromSvg(row.assets&&row.assets.helm_svg_palettes)}<small class="meta">committed SVG where available</small></figure>
    <figure><figcaption>Helm S-57 render</figcaption>${stripFromTriplet(row.assets&&row.assets.helm_s57_render)}<small class="meta">generated-owned candidate</small></figure>
    <figure><figcaption>Helm S-101 trace render</figcaption>${stripFromTriplet(row.assets&&row.assets.helm_s101_render)}<small class="meta">S-101 evidence path, not bundled source art</small></figure>
  </article>`;
}
function renderRows(){
  const filtered=(data.rows||[]).filter(matches);
  if(state.offset>=filtered.length)state.offset=Math.max(0,Math.floor((filtered.length-1)/state.pageSize)*state.pageSize);
  const rows=filtered.slice(state.offset,state.offset+state.pageSize);
  updatePage(filtered.length,rows.length);
  document.getElementById('rows').innerHTML=rows.map(renderRow).join('')||'<div class="alert">No rows matched this filter.</div>';
}
async function init(){
  try{
    const res=await fetch('package-proof-data.json',{headers:{'Accept':'application/json'}});
    if(!res.ok)throw new Error(`${res.status} ${res.statusText}`);
    data=await res.json();
    renderSummary(); renderRows();
  }catch(err){showAlert(`Package proof data is required; no static fallback is allowed. ${err.message}`);}
}
document.getElementById('q').addEventListener('input',e=>{state.q=e.target.value;state.offset=0;renderRows();});
document.getElementById('section').addEventListener('change',e=>{state.section=e.target.value;state.offset=0;renderRows();});
document.getElementById('gate').addEventListener('change',e=>{state.gate=e.target.value;state.offset=0;renderRows();});
document.getElementById('prev').addEventListener('click',()=>{state.offset=Math.max(0,state.offset-state.pageSize);renderRows();});
document.getElementById('next').addEventListener('click',()=>{state.offset+=state.pageSize;renderRows();});
document.getElementById('refresh').addEventListener('click',renderRows);
init();
</script>
</body>
</html>
"""


def build_public_package(*, proof_bundle_dir: Path = DEFAULT_PROOF_BUNDLE_DIR) -> dict[str, Any]:
    registry = cleanroom_symbol_manifest.build_manifest()
    proof_bundle_manifest, _, _ = electronic_chart1_proof_bundle._load_bundle(proof_bundle_dir)  # noqa: SLF001
    runtime_gate = electronic_chart1_runtime_promotion_gate.build_promotion_gate(proof_dir=proof_bundle_dir)
    rows = _proof_rows(proof_bundle_dir, runtime_gate)
    coverage = _coverage(rows, registry, runtime_gate)
    manifest = _manifest(
        coverage=coverage,
        registry=registry,
        runtime_gate=runtime_gate,
        proof_bundle_manifest=proof_bundle_manifest,
    )
    data = {
        "schema": PROOF_DATA_SCHEMA,
        "status": "ok",
        "manifest": {
            "schema": manifest["schema"],
            "status": manifest["status"],
            "name": manifest["name"],
            "source_boundary": manifest["source_boundary"],
        },
        "coverage": coverage,
        "rows": rows,
    }
    return {
        "manifest": manifest,
        "coverage": coverage,
        "proof_data": data,
        "hard_pile": {
            "schema": "helm.forge.public_cleanroom_symbol_hard_pile.v1",
            "status": "runtime_release_blocked",
            "rows": [
                {
                    "row_key": row["row_key"],
                    "symbol_id": row.get("symbol_id"),
                    "section": row.get("section"),
                    "row_taxonomy": row.get("row_taxonomy"),
                    "reason_codes": row["runtime"]["reason_codes"],
                    "remediation_hints": row["runtime"]["remediation_hints"],
                }
                for row in rows
                if row["runtime"]["reason_codes"]
            ],
        },
        "chartplotter_rule_input": {
            "schema": "helm.forge.public_cleanroom_chartplotter_rule_input.v1",
            "status": "runtime_release_blocked",
            "runtime_export_rows": runtime_gate["runtime_export"]["rows"],
            "release_gate": runtime_gate["policy"],
            "source_hashes": runtime_gate["runtime_export"]["source_hashes"],
        },
    }


def write_public_package(
    *,
    proof_dir: Path = PROOF_DIR,
    proof_bundle_dir: Path = DEFAULT_PROOF_BUNDLE_DIR,
) -> dict[str, Any]:
    package = build_public_package(proof_bundle_dir=proof_bundle_dir)
    proof_dir.mkdir(parents=True, exist_ok=True)
    _write_json(proof_dir / "manifest.json", package["manifest"])
    _write_json(proof_dir / "coverage.json", package["coverage"])
    _write_json(proof_dir / "package-proof-data.json", package["proof_data"])
    _write_json(proof_dir / "missing-hard-pile.json", package["hard_pile"])
    _write_json(proof_dir / "chartplotter-rule-input.json", package["chartplotter_rule_input"])
    (proof_dir / "compare-opencpn.html").write_text(_comparison_html())
    (proof_dir / "index.html").write_text(_comparison_html())
    (proof_dir / "README.md").write_text(_readme_markdown())
    (proof_dir / "SOURCE-BOUNDARY.md").write_text(_source_boundary_markdown())
    inventory = {
        "manifest": _sha256(proof_dir / "manifest.json"),
        "coverage": _sha256(proof_dir / "coverage.json"),
        "package_proof_data": _sha256(proof_dir / "package-proof-data.json"),
        "missing_hard_pile": _sha256(proof_dir / "missing-hard-pile.json"),
        "chartplotter_rule_input": _sha256(proof_dir / "chartplotter-rule-input.json"),
        "compare_opencpn_html": _sha256(proof_dir / "compare-opencpn.html"),
    }
    _write_json(proof_dir / "provenance-inventory.json", {
        "schema": "helm.forge.public_cleanroom_symbol_inventory.v1",
        "status": "ok",
        "files": inventory,
    })
    return {
        "status": "public_cleanroom_symbol_package_written",
        "proof_dir": _display_path(proof_dir),
        "summary": package["coverage"],
        "inventory": inventory,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--proof-dir", type=Path, default=PROOF_DIR)
    parser.add_argument("--proof-bundle-dir", type=Path, default=DEFAULT_PROOF_BUNDLE_DIR)
    args = parser.parse_args(argv)
    print(json.dumps(
        write_public_package(proof_dir=args.proof_dir, proof_bundle_dir=args.proof_bundle_dir),
        indent=2,
        sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
