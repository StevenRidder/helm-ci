"""Build FORGE-43 Helm S-101 resolver traces for electronic Chart 1 fixtures.

This harness consumes the FORGE-40 electronic Chart 1 fixtures and the
FORGE-42 Helm S-57 candidate render evidence. It does not duplicate artwork
generation. It proves which fixture rows have enough DB-backed S-101 evidence
to point at a Helm candidate render, and which rows must stay fail-closed.

Run:
  python3 -m forge.electronic_chart1_helm_s101_render
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
FIXTURES_JSON = CATALOG / "electronic_chart1_fixtures.json"
HELM_S57_JSON = CATALOG / "electronic_chart1_helm_s57_render.json"
HELM_S101_JSON = CATALOG / "electronic_chart1_helm_s101_render.json"
HELM_S101_MD = CATALOG / "electronic_chart1_helm_s101_render.md"
SCHEMA = "helm.forge.electronic_chart1_helm_s101_render.v1"

TRACE_READY_CLASSES = {
    "direct",
    "catalogue_rule",
    "rule_derived",
    "documented_deviation",
}


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_canonical_json(payload))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _compact_palette_outputs(row: dict[str, Any]) -> dict[str, dict[str, Any]]:
    outputs: dict[str, dict[str, Any]] = {}
    for palette, metadata in sorted((row.get("palette_outputs") or {}).items()):
        outputs[palette] = {
            "path": metadata["path"],
            "sha256": metadata["sha256"],
            "nonblank": metadata["nonblank"],
            "primary_color_token": metadata.get("primary_color_token"),
            "color_source": metadata.get("color_source"),
        }
    return outputs


def _s101_attributes(s101: dict[str, Any]) -> dict[str, Any]:
    return dict(s101.get("attributes") or (s101.get("portrayal_evidence") or {}).get("attributes") or {})


def _rule_instruction_refs(s101: dict[str, Any]) -> list[dict[str, Any]]:
    return list((s101.get("portrayal_evidence") or {}).get("rule_instruction_refs") or [])


def _direct_symbol(s101: dict[str, Any]) -> dict[str, Any]:
    return dict((s101.get("portrayal_evidence") or {}).get("direct_symbol") or {})


def _feature_rule_file(s101: dict[str, Any]) -> str | None:
    return s101.get("rule_file") or (s101.get("portrayal_evidence") or {}).get("feature_rule_file")


def _trace_class(s101: dict[str, Any]) -> str:
    mapping_type = s101.get("mapping_type")
    resolver_status = s101.get("resolver_status")
    crosswalk_class = s101.get("crosswalk_class")
    if mapping_type == "direct_asset_match" and resolver_status == "resolved_direct":
        return "direct"
    if mapping_type == "rule_derived_equivalent" and resolver_status == "resolved_rule_catalogue":
        return "catalogue_rule"
    if mapping_type == "rule_derived_equivalent" and resolver_status == "resolved_rule":
        return "rule_derived"
    if mapping_type == "acceptable_deviation" and resolver_status == "resolved_with_deviation":
        return "documented_deviation"
    if crosswalk_class == "non_s101_runtime_construct" or resolver_status == "classified_non_s101_runtime":
        return "non_s101_runtime_construct"
    if crosswalk_class == "non_s101_or_inland_extension" or resolver_status == "classified_extension_requires_profile":
        return "non_s101_or_extension_profile"
    if mapping_type == "semantic_only":
        return "semantic_only_manual"
    return "unresolved"


def _source_refs(fixture: dict[str, Any]) -> dict[str, Any]:
    s57_tuple = fixture["s57"]["attribute_tuple"]
    s101 = fixture["s101"]
    return {
        "s52_lookup_id": fixture["s52_lookup_id"],
        "s52_symbol_id": s57_tuple.get("s52_symbol_id"),
        "object_class": s57_tuple.get("object_class"),
        "s101_feature_type": s101.get("feature_type"),
        "s101_rule_file": _feature_rule_file(s101),
    }


def _has_db_backing(fixture: dict[str, Any], trace_class: str) -> tuple[bool, list[str]]:
    s101 = fixture["s101"]
    reasons: list[str] = []
    if trace_class == "direct":
        direct = _direct_symbol(s101)
        if not direct.get("matched") or not direct.get("symbol_id"):
            reasons.append("s101_direct_symbol_missing")
    elif trace_class in {"rule_derived", "catalogue_rule"}:
        if not _feature_rule_file(s101):
            reasons.append("s101_rule_file_missing")
    elif trace_class == "documented_deviation":
        if not _feature_rule_file(s101) and not _direct_symbol(s101).get("symbol_id"):
            reasons.append("s101_deviation_authority_missing")
    else:
        reasons.append(f"s101_trace_class_not_runtime_candidate:{trace_class}")
    return not reasons, reasons


def _colour_transform_authority(fixture: dict[str, Any], render_row: dict[str, Any] | None) -> dict[str, Any]:
    helm_colour = fixture.get("helm", {}).get("expected_authority", {}).get("colour", {})
    s101 = fixture["s101"]
    attrs = _s101_attributes(s101)
    palette_outputs = render_row.get("palette_outputs") if render_row else {}
    color_sources = sorted({meta.get("color_source") for meta in palette_outputs.values() if meta.get("color_source")})
    return {
        "authority_source": "fixture.helm.expected_authority.colour + S-101 resolver attributes + FORGE-42 palette metadata",
        "helm_colour_authority": helm_colour.get("helm_colour_authority") or {},
        "s52_color_refs": helm_colour.get("s52_color_refs") or fixture["s52"]["instruction_evidence"].get("color_refs") or [],
        "s101_colour": attrs.get("colour"),
        "s101_colour_pattern": attrs.get("colourPattern"),
        "render_color_sources": color_sources,
        "raw_s101_svg_colour_is_not_authority": True,
    }


def _topmark_daymark_context(fixture: dict[str, Any]) -> dict[str, Any]:
    attrs = _s101_attributes(fixture["s101"])
    s57_tuple = fixture["s57"]["attribute_tuple"]
    return {
        "object_class": s57_tuple.get("object_class"),
        "s52_symbol_id": s57_tuple.get("s52_symbol_id"),
        "topmark_context": attrs.get("topmarkContext"),
        "topmark_shape_code": attrs.get("topmarkShapeCode"),
        "topmark_shape_label": attrs.get("topmarkShapeLabel"),
        "topmark_shape_source_attribute": attrs.get("topmarkShapeSourceAttribute"),
        "s57_topmark_shape": attrs.get("s57_topmark_shape") or s57_tuple.get("TOPSHP"),
    }


def _s101_trace(fixture: dict[str, Any]) -> dict[str, Any]:
    s101 = fixture["s101"]
    trace_class = _trace_class(s101)
    db_backed, missing = _has_db_backing(fixture, trace_class)
    rule_file = _feature_rule_file(s101)
    attrs = _s101_attributes(s101)
    direct = _direct_symbol(s101)
    filename_only_match = False
    if trace_class in {"rule_derived", "catalogue_rule", "documented_deviation"}:
        filename_only_match = not db_backed
    return {
        "classification": trace_class,
        "mapping_type": s101.get("mapping_type"),
        "resolver_status": s101.get("resolver_status"),
        "crosswalk_class": s101.get("crosswalk_class"),
        "feature_type": s101.get("feature_type") or (s101.get("portrayal_evidence") or {}).get("feature_type"),
        "rule_file": rule_file,
        "attributes": attrs,
        "direct_symbol": direct,
        "rule_instruction_refs": _rule_instruction_refs(s101),
        "unresolved_reasons": list(s101.get("unresolved_reasons") or []),
        "db_backed": db_backed,
        "missing_db_backing_reasons": missing,
        "filename_only_match": filename_only_match,
        "source_refs": _source_refs(fixture),
    }


def _hard_pile_row(
    fixture: dict[str, Any],
    render_row: dict[str, Any] | None,
    trace: dict[str, Any],
    reasons: list[str],
) -> dict[str, Any]:
    return {
        "fixture_id": fixture["fixture_id"],
        "s52_lookup_id": fixture["s52_lookup_id"],
        "row_key": fixture["row_key"],
        "chart1_row_id": fixture["chart1_row_id"],
        "row_taxonomy": fixture["row_taxonomy"],
        "status": "helm_s101_fail_closed",
        "reason_codes": sorted(set(reasons or ["helm_s101_trace:fail_closed"])),
        "s57": fixture["s57"],
        "s52": fixture["s52"],
        "s101_trace": trace,
        "helm_candidate_render": {
            "present": render_row is not None,
            "status": render_row.get("status") if render_row else None,
            "palette_outputs": _compact_palette_outputs(render_row) if render_row else {},
        },
        "colour_transform_authority": _colour_transform_authority(fixture, render_row),
        "topmark_daymark_context": _topmark_daymark_context(fixture),
        "runtime_gate": {
            **fixture["runtime_gate"],
            "runtime_eligible": False,
            "fail_closed": True,
            "blocked_by": sorted(set((fixture["runtime_gate"].get("blocked_by") or []) + reasons)),
        },
    }


def _row(fixture: dict[str, Any], render_row: dict[str, Any], trace: dict[str, Any]) -> dict[str, Any]:
    return {
        "fixture_id": fixture["fixture_id"],
        "s52_lookup_id": fixture["s52_lookup_id"],
        "row_key": fixture["row_key"],
        "chart1_row_id": fixture["chart1_row_id"],
        "row_taxonomy": fixture["row_taxonomy"],
        "status": "s101_trace_ready",
        "reason_codes": [],
        "s57": fixture["s57"],
        "s52": {
            "instruction": fixture["s52"]["instruction"],
            "instruction_evidence": fixture["s52"]["instruction_evidence"],
        },
        "s101_trace": trace,
        "helm_candidate_render": {
            "present": True,
            "status": render_row["status"],
            "nonblank_validation": render_row["nonblank_validation"],
            "render_sources": render_row["helm_trace"]["render_sources"],
            "recipe": render_row["helm_trace"]["recipe"],
            "palette_outputs": _compact_palette_outputs(render_row),
            "source_boundary": render_row["helm_trace"]["source_boundary"],
        },
        "colour_transform_authority": _colour_transform_authority(fixture, render_row),
        "topmark_daymark_context": _topmark_daymark_context(fixture),
        "runtime_gate": {
            **fixture["runtime_gate"],
            "runtime_eligible": False,
            "fail_closed": True,
        },
    }


def build_render_trace(
    *,
    fixtures_path: Path = FIXTURES_JSON,
    helm_s57_path: Path = HELM_S57_JSON,
    limit: int | None = None,
) -> dict[str, Any]:
    fixture_payload = _load_json(fixtures_path)
    if fixture_payload["schema"] != "helm.forge.electronic_chart1_fixtures.v1":
        raise ValueError(f"unexpected fixture schema: {fixture_payload['schema']}")
    s57_payload = _load_json(helm_s57_path)
    if s57_payload["schema"] != "helm.forge.electronic_chart1_helm_s57_render.v1":
        raise ValueError(f"unexpected Helm S-57 render schema: {s57_payload['schema']}")

    fixtures = fixture_payload["fixtures"][:limit]
    render_by_row_key = {row["row_key"]: row for row in s57_payload["rows"]}
    rows: list[dict[str, Any]] = []
    hard_pile: list[dict[str, Any]] = []
    for fixture in fixtures:
        trace = _s101_trace(fixture)
        render_row = render_by_row_key.get(fixture["row_key"])
        reasons: list[str] = []
        if trace["classification"] not in TRACE_READY_CLASSES:
            reasons.append(f"s101_trace:{trace['classification']}")
        if trace["classification"] in TRACE_READY_CLASSES and not trace["db_backed"]:
            reasons.extend(f"s101_trace:{reason}" for reason in trace["missing_db_backing_reasons"])
        if render_row is None:
            reasons.append("helm_s101_render:no_forge42_candidate_render")
        if trace["filename_only_match"]:
            reasons.append("s101_trace:filename_only_match_forbidden")

        if reasons:
            hard_pile.append(_hard_pile_row(fixture, render_row, trace, reasons))
        else:
            rows.append(_row(fixture, render_row, trace))

    summary = _summary(fixture_payload, s57_payload, rows, hard_pile, limit)
    return {
        "schema": SCHEMA,
        "status": "helm_s101_render_trace_ready" if summary["accounted_fixture_rows"] == summary["fixture_rows"] else "helm_s101_render_trace_blocked",
        "policy": {
            "source": "FORGE-40 electronic_chart1_fixtures + FORGE-42 Helm S-57 candidate renders + fixture S-101 resolver evidence",
            "backend_generated": True,
            "db_resolver_trace_required": True,
            "uses_forge42_render_evidence": True,
            "duplicates_artwork_generation": False,
            "browser_business_logic_allowed": False,
            "static_json_fallback_allowed": False,
            "runtime_promotion_allowed": False,
            "raw_s101_svg_colour_is_not_authority": True,
            "clean_room_boundary": "S-101 catalogue and OpenCPN evidence are reference/comparison signals; Helm candidate renders remain generated-owned artifacts.",
        },
        "source": {
            "fixture_schema": fixture_payload["schema"],
            "fixture_status": fixture_payload["status"],
            "fixture_rows": len(fixtures),
            "fixture_source_rows": fixture_payload["summary"]["source_rows"],
            "fixture_source_hard_pile_rows": len(fixture_payload["hard_pile"]) if limit is None else 0,
            "fixtures_sha256": _sha256(fixtures_path),
            "helm_s57_schema": s57_payload["schema"],
            "helm_s57_status": s57_payload["status"],
            "helm_s57_rendered_rows": len(s57_payload["rows"]),
            "helm_s57_hard_pile_rows": len(s57_payload["hard_pile"]),
            "helm_s57_sha256": _sha256(helm_s57_path),
        },
        "summary": summary,
        "rows": rows,
        "hard_pile": hard_pile,
        "source_hard_pile": fixture_payload["hard_pile"] if limit is None else [],
    }


def _summary(
    fixture_payload: dict[str, Any],
    s57_payload: dict[str, Any],
    rows: list[dict[str, Any]],
    hard_pile: list[dict[str, Any]],
    limit: int | None,
) -> dict[str, Any]:
    fixtures = fixture_payload["fixtures"][:limit]
    trace_counts = Counter(row["s101_trace"]["classification"] for row in rows)
    trace_counts.update(row["s101_trace"]["classification"] for row in hard_pile)
    ready_trace_counts = Counter(row["s101_trace"]["classification"] for row in rows)
    hard_trace_counts = Counter(row["s101_trace"]["classification"] for row in hard_pile)
    hard_reasons: Counter[str] = Counter()
    for row in hard_pile:
        hard_reasons.update(row["reason_codes"])
    return {
        "fixture_rows": len(fixtures),
        "trace_ready_rows": len(rows),
        "trace_fail_closed_rows": len(hard_pile),
        "accounted_fixture_rows": len(rows) + len(hard_pile),
        "source_hard_pile_rows": len(fixture_payload["hard_pile"]) if limit is None else 0,
        "forge42_rendered_rows": len(s57_payload["rows"]),
        "forge42_render_hard_pile_rows": len(s57_payload["hard_pile"]),
        "s101_trace_class_counts": dict(sorted(trace_counts.items())),
        "ready_trace_class_counts": dict(sorted(ready_trace_counts.items())),
        "fail_closed_trace_class_counts": dict(sorted(hard_trace_counts.items())),
        "hard_pile_reason_counts": dict(hard_reasons.most_common(40)),
        "row_taxonomy_counts": dict(sorted(Counter(row["row_taxonomy"] for row in rows).items())),
        "runtime_eligible_rows": 0,
    }


def _markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Electronic Chart 1 Helm S-101 Render Trace",
        "",
        "FORGE-43 joins Electronic Chart 1 fixtures, S-101 resolver evidence, and FORGE-42 Helm candidate render evidence.",
        "",
        f"- schema: `{payload['schema']}`",
        f"- status: `{payload['status']}`",
        f"- fixture_rows: `{summary['fixture_rows']}`",
        f"- trace_ready_rows: `{summary['trace_ready_rows']}`",
        f"- trace_fail_closed_rows: `{summary['trace_fail_closed_rows']}`",
        f"- source_hard_pile_rows: `{summary['source_hard_pile_rows']}`",
        "",
        "## Policy",
        "",
        "- S-101 traces are generated by the backend from fixture DB evidence.",
        "- Helm S-101 candidate rows reuse FORGE-42 Helm-owned render evidence; this task does not generate duplicate artwork.",
        "- Rule-derived BOY/BCN/TOP rows must carry rule files and attributes; filename-only matches fail closed.",
        "- Raw S-101 SVG colour is not colour authority. Colour authority comes from fixture semantics, S-101 attributes, and Helm palette metadata.",
        "- Browser/UI consumers may display this report but must not implement resolver logic.",
        "- Rows remain fail-closed and are not runtime-promoted by this task.",
        "",
        "## S-101 Trace Classes",
        "",
        "| Class | Count |",
        "| --- | ---: |",
    ]
    for klass, count in summary["s101_trace_class_counts"].items():
        lines.append(f"| `{klass}` | {count} |")
    lines.extend([
        "",
        "## Ready Trace Classes",
        "",
        "| Class | Count |",
        "| --- | ---: |",
    ])
    for klass, count in summary["ready_trace_class_counts"].items():
        lines.append(f"| `{klass}` | {count} |")
    lines.extend([
        "",
        "## Fail-Closed Trace Classes",
        "",
        "| Class | Count |",
        "| --- | ---: |",
    ])
    for klass, count in summary["fail_closed_trace_class_counts"].items():
        lines.append(f"| `{klass}` | {count} |")
    lines.extend([
        "",
        "## Top Hard Pile Reasons",
        "",
        "| Reason | Count |",
        "| --- | ---: |",
    ])
    for reason, count in summary["hard_pile_reason_counts"].items():
        lines.append(f"| `{reason}` | {count} |")
    return "\n".join(lines) + "\n"


def write_render_trace(
    *,
    fixtures_path: Path = FIXTURES_JSON,
    helm_s57_path: Path = HELM_S57_JSON,
    json_path: Path = HELM_S101_JSON,
    markdown_path: Path = HELM_S101_MD,
    limit: int | None = None,
) -> dict[str, Any]:
    payload = build_render_trace(fixtures_path=fixtures_path, helm_s57_path=helm_s57_path, limit=limit)
    _write_json(json_path, payload)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(_markdown(payload))
    return {
        "status": payload["status"],
        "summary": payload["summary"],
        "json": str(json_path),
        "markdown": str(markdown_path),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, default=FIXTURES_JSON)
    parser.add_argument("--helm-s57-render", type=Path, default=HELM_S57_JSON)
    parser.add_argument("--json", type=Path, default=HELM_S101_JSON)
    parser.add_argument("--markdown", type=Path, default=HELM_S101_MD)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args(argv)
    print(json.dumps(
        write_render_trace(
            fixtures_path=args.fixtures,
            helm_s57_path=args.helm_s57_render,
            json_path=args.json,
            markdown_path=args.markdown,
            limit=args.limit,
        ),
        indent=2,
        sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
