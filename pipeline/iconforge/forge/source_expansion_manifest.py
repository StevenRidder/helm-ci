"""Build the source-expansion manifest for reference-gap Forge rows.

FORGE-20 is not an artwork task. It prepares a later source/inspiration lane by
making missing reference coverage, license posture, and generation plans
explicit. It must not mark symbols ready or final-approved.

Run:
  python3 -m forge.source_expansion_manifest
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
STANDARD_SOURCE_TABLE = CATALOG / "standard_source_table.json"
TRIAD_REFERENCE_PACK = CATALOG / "triad_reference_candidate_pack.json"
REGISTRY = ROOT / "registry" / "symbols.json"
OUT_JSON = CATALOG / "source_expansion_manifest.json"
OUT_MD = CATALOG / "source_expansion_manifest.md"

SCHEMA = "helm.iconforge.source_expansion_manifest.v1"
EXPECTED_STALE_NO_CANDIDATE_COUNT = 77
LICENSE_TAGS = [
    "public-domain-import",
    "cc0-reference",
    "apache-design-inspiration",
    "license_pending_reference",
    "manual_exception",
]


def _read(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"required source-expansion input missing: {path}")
    return json.loads(path.read_text())


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _stable(value: Any) -> str:
    return str(value or "").strip()


def _status(row: dict[str, Any]) -> str:
    return _stable(((row.get("helm_candidate") or {}).get("candidate_status")))


def _load_indexes() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    standard = _read(STANDARD_SOURCE_TABLE)
    triad = _read(TRIAD_REFERENCE_PACK)
    registry = _read(REGISTRY)
    standard_by_asset = {str(row.get("asset")): row for row in standard.get("rows") or [] if row.get("asset")}
    triad_by_asset = {str(row.get("id")): row for row in triad.get("rows") or [] if row.get("id")}
    registry_by_symbol: dict[str, list[dict[str, Any]]] = {}
    for row in registry.get("symbols") or []:
        symbol_id = row.get("symbol_id")
        if symbol_id:
            registry_by_symbol.setdefault(str(symbol_id), []).append(row)
    return standard_by_asset, triad_by_asset, registry_by_symbol


def _selection_reasons(asset: str, standard: dict[str, Any] | None, triad: dict[str, Any] | None) -> list[str]:
    reasons: list[str] = []
    if standard:
        status = _status(standard)
        if status == "no_helm_candidate":
            reasons.append("candidate_status:no_helm_candidate")
        elif status and status != "judge_pass_pending_final_approval":
            reasons.append(f"candidate_status:{status}")
    coverage = (triad or {}).get("triad_coverage") or {}
    if coverage and not coverage.get("any"):
        reasons.append("triad_reference_gap:any_false")
    if coverage and not coverage.get("opencpn"):
        reasons.append("triad_reference_gap:opencpn_false")
    if not triad:
        reasons.append("triad_row_missing")
    if not standard:
        reasons.append("standard_source_row_missing")
    return reasons


def _license_tag(provider: str, status: str | None = None) -> str:
    provider = provider.lower()
    status = (status or "").lower()
    if "chart" in provider and "no.1" in provider:
        return "public-domain-import"
    if provider == "openbridge":
        return "apache-design-inspiration"
    if "cc0" in status:
        return "cc0-reference"
    if "manual" in status:
        return "manual_exception"
    return "license_pending_reference"


def _existing_refs(triad: dict[str, Any] | None) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for provider, provider_refs in ((triad or {}).get("triad_refs") or {}).items():
        for ref in provider_refs or []:
            refs.append({
                "provider": provider,
                "label": ref.get("label"),
                "path": ref.get("path") or ref.get("day"),
                "status": ref.get("status"),
                "license_boundary": ref.get("license_boundary"),
                "license_tag": _license_tag(provider, ref.get("status")),
                "use": "reference_only_not_source_artwork",
            })
    return refs


def _proposed_sources(row: dict[str, Any] | None, triad: dict[str, Any] | None) -> list[dict[str, Any]]:
    family = _stable((row or {}).get("family") or (triad or {}).get("family"))
    status = _status(row or {})
    sources: list[dict[str, Any]] = [
        {
            "provider": "NOAA Chart No.1",
            "license_tag": "public-domain-import",
            "use": "reference_crop_or_symbol_semantics_where_exact_crop_can_be_recorded",
            "needed_for": "public_domain_shape_witness",
        }
    ]
    if family in {"areas_patterns_lines", "ugly_attribute_edges"} or status in {"style_primitive_registry", "portrayal_rule_registry"}:
        sources.append({
            "provider": "OpenBridge",
            "license_tag": "apache-design-inspiration",
            "use": "style_or_interface_inspiration_only_when local Apache-2.0 evidence applies",
            "needed_for": "primitive_style_reference_not_chart_portrayal_authority",
        })
    sources.append({
        "provider": "S-57/S-52/S-101 metadata",
        "license_tag": "license_pending_reference",
        "use": "standards_vocabulary_and_rule_evidence_only_not_artwork_import",
        "needed_for": "semantic_brief_and_mapping_cross_check",
    })
    if not (triad or {}).get("triad_coverage", {}).get("opencpn"):
        sources.append({
            "provider": "OpenCPN generated comparison render",
            "license_tag": "license_pending_reference",
            "use": "comparison_target_only_do_not_copy_pixels",
            "needed_for": "human_parity_review_gap",
        })
    return sources


def _semantic_gaps(row: dict[str, Any] | None, triad: dict[str, Any] | None) -> list[str]:
    gaps: list[str] = []
    brief = (row or {}).get("semantic_brief") or {}
    if not brief:
        gaps.append("semantic_brief_missing")
    if not brief.get("required_colours"):
        gaps.append("required_colours_reference_defined_or_missing")
    if not brief.get("required_shape") or "strongest S-101/OpenCPN/Aqua Map reference" in str(brief.get("required_shape")):
        gaps.append("required_shape_needs_specific_witness")
    coverage = (triad or {}).get("triad_coverage") or {}
    for provider in ("opencpn", "s101", "aquamap"):
        if coverage and not coverage.get(provider):
            gaps.append(f"{provider}_reference_missing")
    return sorted(set(gaps))


def _generation_plan(row: dict[str, Any] | None, triad: dict[str, Any] | None, reasons: list[str]) -> dict[str, Any]:
    candidate = (row or {}).get("helm_candidate") or {}
    has_candidate = bool(candidate.get("canonical_svg") or ((triad or {}).get("asset") or {}).get("canonical"))
    return {
        "current_helm_candidate": candidate.get("canonical_svg") or ((triad or {}).get("asset") or {}).get("canonical"),
        "has_candidate": has_candidate,
        "next_action": "collect_or_verify_reference_sources_then_rerun_judge_or_manual_exception",
        "must_not_do": [
            "do_not_copy_or_trace_OpenCPN_IHO_AquaMap_pixels",
            "do_not_mark_ready_without_clear_source_provenance",
            "do_not_final_approve_from_source_expansion_manifest",
        ],
        "handoff": "visual_repair_or_manual_exception_lane",
        "selection_reasons": reasons,
    }


def _row(asset: str, standard: dict[str, Any] | None, triad: dict[str, Any] | None, registry_rows: list[dict[str, Any]]) -> dict[str, Any]:
    reasons = _selection_reasons(asset, standard, triad)
    return {
        "asset": asset,
        "name": (standard or triad or {}).get("name") or asset,
        "family": (standard or triad or {}).get("family"),
        "kind": (triad or {}).get("kind") or "symbol",
        "candidate_status": _status(standard or {}),
        "triad_coverage": (triad or {}).get("triad_coverage") or {},
        "selection_reasons": reasons,
        "semantic_brief": (standard or {}).get("semantic_brief") or {},
        "semantic_brief_gaps": _semantic_gaps(standard, triad),
        "existing_reference_ideas": _existing_refs(triad),
        "proposed_source_refs": _proposed_sources(standard, triad),
        "generation_plan": _generation_plan(standard, triad, reasons),
        "registry_rows": [
            {
                "id": item.get("id"),
                "qa_status": (item.get("qa") or {}).get("status"),
                "visual_parity": (item.get("qa") or {}).get("visual_parity"),
                "runtime_eligible": (item.get("qa") or {}).get("runtime_eligible"),
            }
            for item in registry_rows[:10]
        ],
        "readiness": {
            "status": "not_ready",
            "reason": "source_expansion_manifest_is_planning_only",
            "may_generate_final_art": False,
        },
    }


def build_manifest() -> dict[str, Any]:
    standard, triad, registry = _load_indexes()
    all_assets = sorted(set(standard) | set(triad))
    no_candidate_assets = {asset for asset, row in standard.items() if _status(row) == "no_helm_candidate"}
    selected = [
        asset for asset in all_assets
        if _selection_reasons(asset, standard.get(asset), triad.get(asset))
    ]
    rows = [_row(asset, standard.get(asset), triad.get(asset), registry.get(asset, [])) for asset in selected]
    reason_counts: Counter[str] = Counter()
    license_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter(row["candidate_status"] or "missing" for row in rows)
    for row in rows:
        reason_counts.update(row["selection_reasons"])
        for source in row["existing_reference_ideas"] + row["proposed_source_refs"]:
            license_counts.update([source["license_tag"]])
    return {
        "schema": SCHEMA,
        "status": "planning_only_not_artwork",
        "source": {
            "standard_source_table": "pipeline/iconforge/catalog/standard_source_table.json",
            "triad_reference_candidate_pack": "pipeline/iconforge/catalog/triad_reference_candidate_pack.json",
            "registry": "pipeline/iconforge/registry/symbols.json",
        },
        "input_correction": {
            "task_expected_no_helm_candidate_rows": EXPECTED_STALE_NO_CANDIDATE_COUNT,
            "current_no_helm_candidate_rows": len(no_candidate_assets),
            "position": "Current inputs no longer contain no_helm_candidate rows; this manifest uses current reference-gap and non-final source-status signals instead.",
        },
        "license_tags": LICENSE_TAGS,
        "summary": {
            "rows": len(rows),
            "ready_rows": 0,
            "no_helm_candidate_rows": len(no_candidate_assets),
            "selection_reason_counts": dict(sorted(reason_counts.items())),
            "candidate_status_counts": dict(sorted(status_counts.items())),
            "license_tag_counts": dict(sorted(license_counts.items())),
        },
        "policy": {
            "artifact_type": "source_expansion_manifest_not_final_art",
            "source_boundary": "reference ideas and semantic evidence only; Helm output remains generated-owned",
            "promotion_rule": "no row is ready until provenance is clear and downstream visual/human gates pass",
        },
        "rows": rows,
    }


def _markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# FORGE-20 Source Expansion Manifest",
        "",
        "This artifact is planning only. It does not approve or generate final artwork.",
        "",
        "## Summary",
        "",
        f"- Rows selected: {summary['rows']}",
        f"- Ready rows: {summary['ready_rows']}",
        f"- Current no_helm_candidate rows: {summary['no_helm_candidate_rows']}",
        f"- Stale task expected no_helm_candidate rows: {payload['input_correction']['task_expected_no_helm_candidate_rows']}",
        "",
        "## Selection Reasons",
        "",
    ]
    for reason, count in summary["selection_reason_counts"].items():
        lines.append(f"- `{reason}`: {count}")
    lines.extend(["", "## License Tags", ""])
    for tag, count in summary["license_tag_counts"].items():
        lines.append(f"- `{tag}`: {count}")
    lines.extend(["", "## First Rows", ""])
    for row in payload["rows"][:20]:
        lines.append(
            f"- `{row['asset']}`: {', '.join(row['selection_reasons'])}; "
            f"readiness={row['readiness']['status']}"
        )
    lines.append("")
    return "\n".join(lines)


def write_manifest(json_path: Path = OUT_JSON, md_path: Path = OUT_MD) -> dict[str, Any]:
    payload = build_manifest()
    _write_json(json_path, payload)
    md_path.write_text(_markdown(payload))
    return {
        "status": "source_expansion_manifest_written",
        "json": _display_path(json_path),
        "markdown": _display_path(md_path),
        "summary": payload["summary"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path, default=OUT_JSON)
    parser.add_argument("--markdown", type=Path, default=OUT_MD)
    args = parser.parse_args(argv)
    print(json.dumps(write_manifest(args.json, args.markdown), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
