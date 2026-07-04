"""Build the public clean-room proof bundle for Icon Forge.

The bundle is intentionally honest: it publishes generated-owned SVG exports,
S-52/OpenCPN comparison references, S-101 resolver evidence, and human review
state without promoting provisional rows to approved chartplotter symbols.

Run:
  python3 -m forge.proof_bundle
"""
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

from .s52_normalization import canonicalize_legacy_text
from .style_contract import OPENBRIDGE_NAV_PALETTES


ROOT = Path(__file__).resolve().parent.parent
THREE_WAY = ROOT / "catalog" / "standards_three_way_proof.json"
TOPMARK_GATE = ROOT / "catalog" / "topmark_contradiction_gate.json"
ALIGNMENT_GATE = ROOT / "catalog" / "standards_alignment_gate.json"
DEFAULT_OUT = ROOT / "proof"
PALETTES = ("day", "dusk", "night")
SPEC_LABEL = "SPEC 0001: Clean-room Maritime Symbol Package"
SPEC_SOURCE = (
    "/Users/steveridder/Documents/Codex/2026-07-01/"
    "is-this-useful-rfc-draft-0001/SPEC-0001-clean-room-symbol-package.md"
)

_VAR = re.compile(r"var\(--([A-Za-z0-9_-]+)\)")


def _read(path: Path) -> Any:
    return json.loads(path.read_text())


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _palette_svg(svg: str, palette: str) -> str:
    colors = OPENBRIDGE_NAV_PALETTES[palette]

    def replace(match: re.Match[str]) -> str:
        token = match.group(1)
        normalized = "gray" if token == "grey" else token
        return colors.get(normalized, match.group(0))

    return _VAR.sub(replace, svg)


def _topmark_rows() -> dict[str, dict[str, Any]]:
    if not TOPMARK_GATE.exists():
        return {}
    data = _read(TOPMARK_GATE)
    return {str(row.get("asset")): row for row in data.get("rows") or []}


def _row_status(row: dict[str, Any], topmark: dict[str, Any] | None) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if row.get("review_state") != "accepted":
        reasons.append(f"review_state:{row.get('review_state')}")
    if row.get("gate", {}).get("status") != "pass":
        reasons.append(f"gate:{row.get('gate', {}).get('status')}")
    if not row.get("helm_candidate", {}).get("final_approved"):
        reasons.append("final_approved:false")
    if row.get("s101_evidence", {}).get("resolver_status") == "unresolved":
        reasons.append("s101_resolver:unresolved")
    if topmark and topmark.get("gate_status") == "manual_review_required":
        reasons.extend(f"topmark:{finding}" for finding in topmark.get("findings") or [])
    if not row.get("helm_candidate", {}).get("canonical_svg"):
        reasons.append("generated_svg:missing")

    if not reasons:
        return "accepted", []
    if "generated_svg:missing" in reasons:
        return "missing", reasons
    return "needs_review", reasons


def _safe_asset(asset: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", asset)


def _copy_palette_svgs(row: dict[str, Any], out_dir: Path) -> dict[str, str]:
    candidate = row.get("helm_candidate") or {}
    source = candidate.get("canonical_svg") or candidate.get("source_svg")
    if not source:
        return {}
    source_path = ROOT / source
    if not source_path.exists():
        return {}
    svg = source_path.read_text()
    asset = _safe_asset(str(row["asset"]))
    paths = {}
    for palette in PALETTES:
        target = out_dir / f"svg-{palette}" / f"{asset}.svg"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(canonicalize_legacy_text(_palette_svg(svg, palette)))
        paths[palette] = str(target.relative_to(out_dir))
    return paths


def _proof_row(row: dict[str, Any], out_dir: Path, topmarks: dict[str, dict[str, Any]]) -> dict[str, Any]:
    topmark = topmarks.get(str(row["asset"]))
    status, reasons = _row_status(row, topmark)
    palette_svgs = _copy_palette_svgs(row, out_dir)
    opencpn = row.get("s52_opencpn_expected", {}).get("comparison_reference") or {}
    s101 = row.get("s101_evidence") or {}
    candidate = row.get("helm_candidate") or {}
    return {
        "symbol_id": row["asset"],
        "name": row.get("name"),
        "kind": row.get("kind"),
        "family": row.get("family"),
        "status": status,
        "status_reasons": reasons,
        "generated_assets": {
            "canonical_svg": candidate.get("canonical_svg"),
            "palette_resolved_svg": palette_svgs,
            "origin": candidate.get("origin"),
            "style_contract": candidate.get("style_contract"),
        },
        "comparison_references": {
            "opencpn": {
                "role": "comparison_target_only",
                "paths": opencpn.get("paths") or {},
                "license_boundary": row.get("s52_opencpn_expected", {}).get("license_boundary"),
                "status": opencpn.get("status"),
            }
        },
        "standards_mappings": {
            "s52_symbol_id": row["asset"],
            "object_class": row.get("s52_opencpn_expected", {}).get("object_class"),
            "s101_mapping_type": s101.get("s101_mapping_type"),
            "s101_resolver_status": s101.get("resolver_status"),
            "s101_crosswalk_classification": s101.get("s101_crosswalk_classification"),
            "exact_s101_filename_match": s101.get("exact_filename_match"),
            "false_filename_gap": s101.get("false_filename_gap"),
            "portrayal_evidence": s101.get("portrayal_evidence"),
            "unresolved_reasons": s101.get("unresolved_reasons"),
        },
        "qa": {
            "candidate_status": candidate.get("candidate_status"),
            "candidate_qa": candidate.get("qa") or {},
            "topmark_contradiction_gate": topmark,
            "final_approved": bool(candidate.get("final_approved")) and status == "accepted",
        },
        "chartplotter_runtime": {
            "eligible": status == "accepted",
            "reason": "use only after status is accepted and final_approved is true",
        },
        "clean_room_boundary": {
            "generated_owned_candidate": candidate.get("origin") == "generated-owned-artwork",
            "comparison_refs_only": True,
            "third_party_artwork_not_source": True,
        },
    }


def _coverage(rows: list[dict[str, Any]], alignment_gate: dict[str, Any], topmark_gate: dict[str, Any]) -> dict[str, Any]:
    statuses = Counter(row["status"] for row in rows)
    s101 = Counter(row["standards_mappings"]["s101_resolver_status"] for row in rows)
    crosswalk = Counter(
        (row["standards_mappings"].get("s101_crosswalk_classification") or {}).get("class", "unknown")
        for row in rows
    )
    return {
        "total": len(rows),
        "generated": sum(1 for row in rows if row["generated_assets"]["palette_resolved_svg"]),
        "accepted": statuses.get("accepted", 0),
        "needs_review": statuses.get("needs_review", 0),
        "failed": statuses.get("failed", 0),
        "blocked": 0,
        "missing": statuses.get("missing", 0),
        "not_comparable": 0,
        "manual_exception": (alignment_gate.get("chart1_parity") or {}).get("evidence_counts", {}).get("manual_exception", 0),
        "manual_review_required": (topmark_gate.get("summary") or {}).get("manual_review_required", 0),
        "status_counts": dict(sorted(statuses.items())),
        "s101_resolver_status_counts": dict(sorted(s101.items())),
        "s101_crosswalk_class_counts": dict(sorted(crosswalk.items())),
        "gate_status": alignment_gate.get("status"),
        "gate_blockers": (alignment_gate.get("review_state") or {}).get("blockers", []),
    }


def _manifest(rows: list[dict[str, Any]], coverage: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "helm.symbol.cleanroom-package.v1",
        "status": "provisional_review_package",
        "specification": {
            "label": SPEC_LABEL,
            "source": SPEC_SOURCE,
            "role": "package/profile contract",
        },
        "standards_profile": {
            "s52": "comparison and symbol vocabulary",
            "s57": "object-class and attribute vocabulary",
            "s101": "direct asset and rule-derived portrayal evidence",
            "opencpn": "comparison target only",
        },
        "render_targets": [
            "OpenCPN/Vulkan",
            "Helm C++",
            "iOS/native",
            "WebGPU",
            "SVG",
            "atlas PNG",
        ],
        "source_boundary": {
            "generated_outputs": "Forge generated-owned SVG candidates and palette-resolved exports",
            "comparison_references": "OpenCPN/IHO/Chart No.1 are comparison or standards evidence only",
            "publish_gate": "only accepted/final_approved rows may become runtime defaults",
        },
        "approval_workflow": {
            "server_module": "forge.human_review_server",
            "run_command": "python3 -m forge.human_review_server --port 9017",
            "review_url": "http://127.0.0.1:9017/out/human_review/icon_review.html",
            "signoff_url": "http://127.0.0.1:9017/out/human_review/pass_review.html",
            "endpoints": {
                "save_review": "/api/save-review",
                "save_signoff": "/api/save-signoff",
            },
            "outputs": {
                "feedback_json": "out/human_review/icon_review_feedback.json",
                "feedback_csv": "out/human_review/icon_review_feedback.csv",
                "signoff_json": "out/human_review/icon_review_signoff.json",
                "signoff_csv": "out/human_review/icon_review_signoff.csv",
            },
            "approved_runtime_rule": "only signoff rows with final_decision=approve and package status=accepted are chartplotter-eligible",
        },
        "coverage": coverage,
        "source": source,
        "symbols": rows,
    }


def _chartplotter_rules(rows: list[dict[str, Any]], coverage: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "helm.symbol.chartplotter-rule-input.v1",
        "status": "provisional_not_runtime_default",
        "runtime_policy": {
            "consume_when": "row.status == accepted and row.qa.final_approved == true",
            "current_default": "do_not_use_as_final_chartplotter_symbols",
            "reason": "visual approval and hard-pile closure remain upstream gates",
        },
        "coverage": coverage,
        "rows": [
            {
                "symbol_id": row["symbol_id"],
                "status": row["status"],
                "runtime_eligible": row["chartplotter_runtime"]["eligible"],
                "palette_resolved_svg": row["generated_assets"]["palette_resolved_svg"],
                "s52_symbol_id": row["standards_mappings"]["s52_symbol_id"],
                "s57_object_class": row["standards_mappings"]["object_class"],
                "s101_mapping_type": row["standards_mappings"]["s101_mapping_type"],
                "s101_resolver_status": row["standards_mappings"]["s101_resolver_status"],
                "s101_crosswalk_classification": row["standards_mappings"]["s101_crosswalk_classification"],
                "portrayal_evidence": row["standards_mappings"]["portrayal_evidence"],
                "status_reasons": row["status_reasons"],
            }
            for row in rows
        ],
    }


def _hard_pile(rows: list[dict[str, Any]]) -> dict[str, Any]:
    hard_rows = [
        {
            "symbol_id": row["symbol_id"],
            "status": row["status"],
            "status_reasons": row["status_reasons"],
            "s101_resolver_status": row["standards_mappings"]["s101_resolver_status"],
            "topmark_findings": (
                (row["qa"].get("topmark_contradiction_gate") or {}).get("findings") or []
            ),
        }
        for row in rows
        if row["status"] != "accepted"
    ]
    return {
        "schema": "helm.symbol.cleanroom-hard-pile.v1",
        "rows": hard_rows,
        "count": len(hard_rows),
    }


def _img(src: str | None, alt: str) -> str:
    if not src:
        return "<div class='missing'>missing</div>"
    return f'<img loading="lazy" src="{html.escape(src)}" alt="{html.escape(alt)}">'


def _summary_pills(coverage: dict[str, Any]) -> str:
    labels = [
        ("total", coverage["total"]),
        ("generated", coverage["generated"]),
        ("accepted", coverage["accepted"]),
        ("needs review", coverage["needs_review"]),
        ("manual review", coverage["manual_review_required"]),
        ("S-101 unknown", coverage["s101_resolver_status_counts"].get("unresolved", 0)),
    ]
    return "".join(f"<span class='pill'>{html.escape(k)} {v}</span>" for k, v in labels)


def _base_css() -> str:
    return """
body{font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:0;background:#f6f7f8;color:#20252b}
header{position:sticky;top:0;background:#fff;border-bottom:1px solid #d8dde3;padding:16px 22px;z-index:2}
h1{margin:0 0 8px;font-size:22px}.summary{display:flex;gap:8px;flex-wrap:wrap}
.pill{border:1px solid #cfd6de;border-radius:999px;padding:4px 10px;background:#f9fafb;font-size:13px}
.toolbar{display:flex;gap:10px;margin-top:12px}input,select{font:inherit;padding:8px;border:1px solid #c7cfd8;border-radius:6px}
main{padding:16px 22px}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px}
.card,.row{background:#fff;border:1px solid #d8dde3;border-radius:8px}.card{padding:12px}.card h2{font-size:16px;margin:0 0 8px}
.preview{display:flex;gap:8px;align-items:center}.preview img{width:56px;height:56px;object-fit:contain;border:1px solid #edf0f3;border-radius:5px}
.meta{font-size:12px;color:#52606d;line-height:1.4}.badge{display:inline-block;margin:2px 4px 2px 0;padding:2px 6px;border-radius:999px;background:#eef2f6;font-size:11px}
.needs_review{background:#fff7e8}.accepted{background:#edf8ef}.missing{font-weight:700;color:#8a2f2f;padding:14px;text-align:center}
.row{display:grid;grid-template-columns:260px repeat(4,1fr);gap:12px;margin:0 0 12px;padding:12px}
figure{margin:0;border:1px solid #e0e5ea;border-radius:6px;min-height:170px;padding:10px;display:flex;flex-direction:column;align-items:center;justify-content:center;background:#fff}
figcaption{font-size:13px;font-weight:700;margin-bottom:8px}figure img{width:112px;height:112px;object-fit:contain}
small{display:block;color:#5d6874;font-size:11px;line-height:1.3;margin-top:8px}.hidden{display:none}
@media(max-width:1000px){.row{grid-template-columns:1fr}}
"""


def _index_html(rows: list[dict[str, Any]], coverage: dict[str, Any]) -> str:
    cards = []
    for row in rows:
        asset = html.escape(str(row["symbol_id"]))
        haystack = html.escape(" ".join(str(row.get(key) or "") for key in ["symbol_id", "name", "kind", "family"]))
        svgs = row["generated_assets"]["palette_resolved_svg"]
        cards.append(
            f"<article class='card {html.escape(row['status'])}' data-status='{html.escape(row['status'])}' "
            f"data-haystack='{haystack.lower()}'>"
            f"<h2>{asset}</h2><div class='preview'>"
            f"{_img(svgs.get('day'), asset + ' day')}"
            f"{_img(svgs.get('dusk'), asset + ' dusk')}"
            f"{_img(svgs.get('night'), asset + ' night')}</div>"
            f"<p class='meta'>{html.escape(str(row.get('name') or ''))}</p>"
            f"<span class='badge'>{html.escape(row['status'])}</span>"
            f"<span class='badge'>{html.escape(str(row['standards_mappings']['s101_mapping_type']))}</span>"
            f"<span class='badge'>runtime {str(row['chartplotter_runtime']['eligible']).lower()}</span>"
            "</article>"
        )
    return "".join([
        "<!doctype html><html><head><meta charset='utf-8'><title>Helm Clean-room Symbol Catalog</title>",
        f"<style>{_base_css()}</style></head><body><header>",
        "<h1>Helm Clean-room Symbol Catalog</h1>",
        f"<div class='summary'>{_summary_pills(coverage)}</div>",
        "<div class='toolbar'><input id='q' type='search' placeholder='Search symbols'><select id='status'><option value=''>all statuses</option><option value='needs_review'>needs_review</option><option value='accepted'>accepted</option><option value='missing'>missing</option></select><a href='compare-opencpn.html'>OpenCPN comparison</a></div>",
        "</header><main><section class='grid' id='grid'>",
        *cards,
        "</section></main><script>",
        "const q=document.getElementById('q'),s=document.getElementById('status');function f(){const v=q.value.toLowerCase(),st=s.value;document.querySelectorAll('.card').forEach(c=>{c.classList.toggle('hidden',(v&&!c.dataset.haystack.includes(v))||(st&&c.dataset.status!==st));});}q.addEventListener('input',f);s.addEventListener('change',f);",
        "</script></body></html>",
    ])


def _compare_html(rows: list[dict[str, Any]], coverage: dict[str, Any]) -> str:
    blocks = []
    for row in rows:
        asset = html.escape(str(row["symbol_id"]))
        refs = ((row.get("comparison_references") or {}).get("opencpn") or {}).get("paths") or {}
        svgs = row["generated_assets"]["palette_resolved_svg"]
        s101 = row["standards_mappings"]
        classification = s101.get("s101_crosswalk_classification") or {}
        blocks.append(
            f"<section class='row {html.escape(row['status'])}' data-status='{html.escape(row['status'])}'>"
            f"<div><h2>{asset}</h2><p class='meta'>{html.escape(str(row.get('name') or ''))}</p>"
            f"<p class='meta'><b>Status:</b> {html.escape(row['status'])}</p>"
            f"<p class='meta'><b>S-101:</b> {html.escape(str(s101['s101_resolver_status']))} / {html.escape(str(s101['s101_mapping_type']))}</p>"
            f"<p class='meta'><b>Crosswalk:</b> {html.escape(str(classification.get('class') or 'unknown'))}</p>"
            f"<p class='meta'><b>Runtime eligible:</b> {str(row['chartplotter_runtime']['eligible']).lower()}</p></div>"
            f"<figure><figcaption>OpenCPN day</figcaption>{_img('../' + refs.get('day') if refs.get('day') else None, asset + ' OpenCPN day')}<small>comparison target only</small></figure>"
            f"<figure><figcaption>Helm day</figcaption>{_img(svgs.get('day'), asset + ' Helm day')}</figure>"
            f"<figure><figcaption>Helm dusk</figcaption>{_img(svgs.get('dusk'), asset + ' Helm dusk')}</figure>"
            f"<figure><figcaption>Helm night</figcaption>{_img(svgs.get('night'), asset + ' Helm night')}</figure>"
            "</section>"
        )
    return "".join([
        "<!doctype html><html><head><meta charset='utf-8'><title>Helm/OpenCPN Symbol Proof</title>",
        f"<style>{_base_css()}</style></head><body><header>",
        "<h1>Helm/OpenCPN Symbol Proof</h1>",
        f"<div class='summary'>{_summary_pills(coverage)}</div>",
        "<p class='meta'>OpenCPN renders are comparison targets only. Helm SVGs are generated-owned candidates. Rows remain out of runtime defaults until accepted and final-approved.</p>",
        "<div class='toolbar'><a href='index.html'>Catalog</a><a href='manifest.json'>Manifest</a><a href='chartplotter-rule-input.json'>Chartplotter rule input</a></div>",
        "</header><main>",
        *blocks,
        "</main></body></html>",
    ])


def build(out_dir: Path = DEFAULT_OUT) -> dict[str, Any]:
    source = _read(THREE_WAY)
    topmark_gate = _read(TOPMARK_GATE) if TOPMARK_GATE.exists() else {"summary": {}}
    alignment_gate = _read(ALIGNMENT_GATE) if ALIGNMENT_GATE.exists() else {}
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    topmarks = _topmark_rows()
    rows = [_proof_row(row, out_dir, topmarks) for row in source["rows"]]
    coverage = _coverage(rows, alignment_gate, topmark_gate)
    manifest = _manifest(rows, coverage, source.get("source") or {})
    hard_pile = _hard_pile(rows)
    rule_input = _chartplotter_rules(rows, coverage)

    _write_json(out_dir / "manifest.json", manifest)
    _write_json(out_dir / "coverage.json", coverage)
    _write_json(out_dir / "missing-hard-pile.json", hard_pile)
    _write_json(out_dir / "chartplotter-rule-input.json", rule_input)
    (out_dir / "index.html").write_text(_index_html(rows, coverage))
    (out_dir / "compare-opencpn.html").write_text(_compare_html(rows, coverage))

    return {
        "status": "proof_bundle_written",
        "out_dir": _display_path(out_dir),
        "coverage": coverage,
        "outputs": {
            "manifest": _display_path(out_dir / "manifest.json"),
            "coverage": _display_path(out_dir / "coverage.json"),
            "missing_hard_pile": _display_path(out_dir / "missing-hard-pile.json"),
            "chartplotter_rule_input": _display_path(out_dir / "chartplotter-rule-input.json"),
            "index": _display_path(out_dir / "index.html"),
            "compare_opencpn": _display_path(out_dir / "compare-opencpn.html"),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    print(json.dumps(build(args.out), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
