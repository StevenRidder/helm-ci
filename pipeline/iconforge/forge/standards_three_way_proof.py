"""Build a full-catalog three-way portrayal proof artifact.

Rows show:

1. S-52/OpenCPN expected comparison target.
2. S-101 direct/rule-derived resolver evidence.
3. Helm generated clean-room candidate.

The output is intentionally review-oriented. It displays the current gate state
and does not promote unapproved artwork as final.

Run:  python -m forge.standards_three_way_proof
"""
from __future__ import annotations

import argparse
import html
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
SOURCE_TABLE = ROOT / "catalog" / "standard_source_table.json"
RESOLVER = ROOT / "catalog" / "standards_s101_resolver.json"
GATE = ROOT / "catalog" / "standards_alignment_gate.json"
DEFAULT_OUT = ROOT / "catalog" / "standards_three_way_proof.json"
DEFAULT_MD = ROOT / "catalog" / "standards_three_way_proof.md"
DEFAULT_HTML = ROOT / "catalog" / "standards_three_way_proof.html"


def _read(path: Path) -> Any:
    return json.loads(path.read_text())


def _write(path: Path, body: Any) -> None:
    path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")


def _source_by_catalog_id(source: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = {}
    for row in source["rows"]:
        s57 = row.get("s57_structure") or {}
        catalog_id = "_".join([
            str(s57.get("object_class") or "UNKNOWN"),
            str(row.get("asset") or "UNKNOWN"),
            str(s57.get("lookup_id") or "UNKNOWN"),
        ])
        rows[catalog_id] = row
    return rows


def _opencpn_ref(row: dict[str, Any] | None) -> dict[str, Any]:
    if not row:
        return {}
    refs = ((row.get("reference_providers") or {}).get("opencpn_render") or [])
    if not refs:
        return {}
    ref = refs[0]
    return {
        "label": ref.get("label"),
        "paths": ref.get("paths") or {},
        "license_boundary": ref.get("license_boundary"),
        "status": ref.get("status"),
    }


def _helm_candidate(row: dict[str, Any] | None) -> dict[str, Any]:
    candidate = (row or {}).get("helm_candidate") or {}
    qa = candidate.get("qa") or {}
    return {
        "canonical_svg": candidate.get("canonical_svg"),
        "source_svg": candidate.get("source_svg"),
        "candidate_status": candidate.get("candidate_status"),
        "origin": candidate.get("origin"),
        "style_contract": candidate.get("style_contract"),
        "qa": qa,
        "final_approved": bool(qa.get("final_approved")),
    }


def _review_state(resolver_row: dict[str, Any], source_row: dict[str, Any] | None, gate: dict[str, Any]) -> str:
    candidate = _helm_candidate(source_row)
    if gate.get("status") != "pass" or not candidate.get("final_approved"):
        return "review_required"
    if resolver_row["resolver_status"] == "unresolved":
        return "resolver_unresolved"
    return "accepted"


def build() -> dict[str, Any]:
    source = _read(SOURCE_TABLE)
    resolver = _read(RESOLVER)
    gate = _read(GATE)
    source_rows = _source_by_catalog_id(source)
    rows = []
    for resolver_row in resolver["rows"]:
        source_row = source_rows.get(resolver_row["helm_catalog_id"])
        rows.append({
            "helm_catalog_id": resolver_row["helm_catalog_id"],
            "source_table_id": resolver_row.get("source_table_id"),
            "asset": resolver_row["s52_symbol_id"],
            "name": (source_row or {}).get("name"),
            "kind": (source_row or {}).get("kind"),
            "family": (source_row or {}).get("family"),
            "review_state": _review_state(resolver_row, source_row, gate),
            "s52_opencpn_expected": {
                "asset": resolver_row["s52_symbol_id"],
                "object_class": resolver_row.get("object_class"),
                "comparison_reference": _opencpn_ref(source_row),
                "license_boundary": "OpenCPN render is comparison target only; do not copy pixels.",
            },
            "s101_evidence": {
                "resolver_status": resolver_row["resolver_status"],
                "s101_mapping_type": resolver_row["s101_mapping_type"],
                "s101_crosswalk_classification": resolver_row.get("s101_crosswalk_classification"),
                "exact_filename_match": resolver_row["exact_filename_match"],
                "false_filename_gap": resolver_row["false_filename_gap"],
                "display_profile": resolver_row["display_profile"],
                "portrayal_evidence": resolver_row["portrayal_evidence"],
                "unresolved_reasons": resolver_row["unresolved_reasons"],
            },
            "helm_candidate": _helm_candidate(source_row),
            "gate": {
                "status": gate.get("status"),
                "blockers": (gate.get("review_state") or {}).get("blockers", []),
                "final_approved": False,
            },
            "clean_room_boundary": {
                "helm_candidate_is_generated_owned": _helm_candidate(source_row).get("origin") == "generated-owned-artwork",
                "comparison_refs_only": True,
            },
        })

    review_counts = Counter(row["review_state"] for row in rows)
    resolver_counts = Counter(row["s101_evidence"]["resolver_status"] for row in rows)
    class_counts = Counter(
        (row["s101_evidence"].get("s101_crosswalk_classification") or {}).get("class", "unknown")
        for row in rows
    )
    return {
        "schema": "helm.forge.three-way-proof.v1",
        "status": "provisional_three_way_proof_ready",
        "source": {
            "standards_s101_resolver": "catalog/standards_s101_resolver.json",
            "standard_source_table": "catalog/standard_source_table.json",
            "standards_alignment_gate": "catalog/standards_alignment_gate.json",
            "source_head": "773a6a18e3a8dbe86f5f653e1340af1e9796002e",
            "source_pr": "https://github.com/StevenRidder/Helm/pull/243",
        },
        "coverage": {
            "rows": len(rows),
            "review_state_counts": dict(sorted(review_counts.items())),
            "resolver_status_counts": dict(sorted(resolver_counts.items())),
            "s101_crosswalk_class_counts": dict(sorted(class_counts.items())),
            "false_filename_gap_count": sum(1 for row in rows if row["s101_evidence"]["false_filename_gap"]),
            "gate_status": gate.get("status"),
        },
        "rows": rows,
    }


def _md(result: dict[str, Any]) -> str:
    coverage = result["coverage"]
    return "\n".join([
        "# Standards Three-Way Proof",
        "",
        f"Status: `{result['status']}`",
        "",
        "Full-catalog proof ledger joining S-52/OpenCPN comparison targets,",
        "S-101 resolver evidence, and Helm generated candidates.",
        "",
        f"- rows: `{coverage['rows']}`",
        f"- review_state_counts: `{coverage['review_state_counts']}`",
        f"- resolver_status_counts: `{coverage['resolver_status_counts']}`",
        f"- s101_crosswalk_class_counts: `{coverage['s101_crosswalk_class_counts']}`",
        f"- false_filename_gap_count: `{coverage['false_filename_gap_count']}`",
        f"- gate_status: `{coverage['gate_status']}`",
        "",
        "This artifact is proof/review infrastructure. It does not final-approve",
        "symbols while the gate status is `review_required`.",
        "",
    ])


def _img(path: str | None, alt: str) -> str:
    if not path:
        return "<div class='missing'>missing</div>"
    src = path
    if not src.startswith(("/", "http://", "https://", "data:")):
        src = f"/{src}"
    return f'<img loading="lazy" src="{html.escape(src)}" alt="{html.escape(alt)}">'


def _html(result: dict[str, Any]) -> str:
    rows = []
    for row in result["rows"]:
        ref_paths = row["s52_opencpn_expected"]["comparison_reference"].get("paths") or {}
        candidate = row["helm_candidate"]
        s101 = row["s101_evidence"]
        evidence = s101["portrayal_evidence"]
        classification = s101.get("s101_crosswalk_classification") or {}
        attrs = ", ".join(f"{k}={v}" for k, v in sorted((evidence.get("attributes") or {}).items())) or "none"
        instructions = evidence.get("instruction_basis") or []
        instruction = instructions[0] if instructions else {}
        rows.append(
            f"<section class='row' data-review='{html.escape(row['review_state'])}' "
            f"data-resolver='{html.escape(s101['resolver_status'])}'>"
            "<div class='meta'>"
            f"<h2>{html.escape(row['asset'] or '')}</h2>"
            f"<p>{html.escape(row.get('name') or '')}</p>"
            f"<p><b>Review:</b> {html.escape(row['review_state'])}</p>"
            f"<p><b>Resolver:</b> {html.escape(s101['resolver_status'])} "
            f"({html.escape(s101['s101_mapping_type'])})</p>"
            f"<p><b>Crosswalk:</b> {html.escape(str(classification.get('class') or 'unknown'))}</p>"
            f"<p><b>False filename gap:</b> {s101['false_filename_gap']}</p>"
            f"<p><b>Gate:</b> {html.escape(row['gate']['status'] or '')}</p>"
            "</div>"
            "<figure>"
            "<figcaption>S-52 / OpenCPN Comparison</figcaption>"
            f"{_img(ref_paths.get('day'), (row['asset'] or '') + ' OpenCPN day')}"
            f"<small>{html.escape(row['s52_opencpn_expected']['license_boundary'])}</small>"
            "</figure>"
            "<figure>"
            "<figcaption>S-101 Resolver Evidence</figcaption>"
            f"<div class='evidence'><b>{html.escape(str(evidence.get('feature_type') or 'unresolved'))}</b>"
            f"<span>{html.escape(str(evidence.get('feature_rule_file') or 'no rule file'))}</span>"
            f"<span>{html.escape(str(instruction.get('basis') or 'no instruction basis'))}</span>"
            f"<span>{html.escape(str(classification.get('basis') or 'no classification basis'))}</span>"
            f"<small>{html.escape(attrs)}</small></div>"
            "</figure>"
            "<figure>"
            "<figcaption>Helm Generated Candidate</figcaption>"
            f"{_img(candidate.get('canonical_svg') or candidate.get('source_svg'), (row['asset'] or '') + ' Helm candidate')}"
            f"<small>{html.escape(candidate.get('candidate_status') or 'no candidate')}</small>"
            "</figure>"
            "</section>"
        )
    coverage = result["coverage"]
    return "".join([
        "<!doctype html><html><head><meta charset='utf-8'>",
        "<title>FORGE Three-Way Proof</title>",
        "<style>",
        "body{font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:0;background:#f6f7f8;color:#20252b}",
        "header{position:sticky;top:0;background:#fff;border-bottom:1px solid #d8dde3;padding:16px 22px;z-index:2}",
        "h1{margin:0 0 8px;font-size:22px}.summary{display:flex;gap:10px;flex-wrap:wrap}",
        ".pill{border:1px solid #cfd6de;border-radius:999px;padding:4px 10px;background:#f9fafb;font-size:13px}",
        "main{padding:16px 22px}.row{display:grid;grid-template-columns:280px 1fr 1fr 1fr;gap:12px;margin:0 0 12px;padding:12px;background:#fff;border:1px solid #d8dde3;border-radius:8px}",
        ".meta h2{margin:0 0 6px;font-size:18px}.meta p{margin:5px 0;font-size:13px;line-height:1.35}",
        "figure{margin:0;border:1px solid #e0e5ea;border-radius:6px;min-height:190px;padding:10px;display:flex;flex-direction:column;align-items:center;justify-content:center;background:#fff}",
        "figcaption{font-size:13px;font-weight:700;margin-bottom:8px}img{width:132px;height:132px;object-fit:contain}.missing{font-weight:700;color:#8a2f2f;padding:24px}",
        "small{display:block;color:#5d6874;font-size:11px;line-height:1.3;margin-top:8px}.evidence{display:grid;gap:7px;text-align:center;font-size:13px}.evidence span{color:#44505c}",
        "@media(max-width:1000px){.row{grid-template-columns:1fr}.meta{border-bottom:1px solid #eef1f4;padding-bottom:8px}}",
        "</style></head><body>",
        "<header><h1>FORGE Three-Way Proof</h1><div class='summary'>",
        f"<span class='pill'>rows {coverage['rows']}</span>",
        f"<span class='pill'>gate {html.escape(str(coverage['gate_status']))}</span>",
        f"<span class='pill'>false filename gaps {coverage['false_filename_gap_count']}</span>",
        f"<span class='pill'>review {html.escape(str(coverage['review_state_counts']))}</span>",
        f"<span class='pill'>resolver {html.escape(str(coverage['resolver_status_counts']))}</span>",
        f"<span class='pill'>crosswalk {html.escape(str(coverage['s101_crosswalk_class_counts']))}</span>",
        "</div></header><main>",
        *rows,
        "</main></body></html>",
    ])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    parser.add_argument("--html", type=Path, default=DEFAULT_HTML)
    args = parser.parse_args(argv)
    result = build()
    _write(args.out, result)
    args.md.write_text(_md(result))
    args.html.write_text(_html(result))
    print(f"three-way proof -> {args.out}")
    print(f"three-way summary -> {args.md}")
    print(f"three-way html -> {args.html}")
    print(f"coverage: {result['coverage']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
