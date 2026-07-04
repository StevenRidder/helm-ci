"""Generate FORGE-40 electronic Chart 1 synthetic fixtures.

The fixture set is generated from the FORGE-39 DB-backed contract only. It does
not read browser JSON, frontend state, SVG artwork, or hand-authored fixture
fallbacks. Every contract row becomes either a deterministic synthetic fixture
or an explicit hard-pile record with reason codes.

Run:
  python3 -m forge.electronic_chart1_fixtures
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from . import electronic_chart1_contract


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
FIXTURES_JSON = CATALOG / "electronic_chart1_fixtures.json"
FIXTURES_MD = CATALOG / "electronic_chart1_fixtures.md"
SCHEMA = "helm.forge.electronic_chart1_fixtures.v1"

FIXTURE_TAXONOMIES = {
    "area_fill",
    "conditional_rule",
    "line_style",
    "point_symbol",
    "text_rule",
}

HARD_PILE_TAXONOMY_REASONS = {
    "non_reviewable_construct": "presentation_library_construct_not_direct_chart1_symbol",
    "placeholder_manual": "manual_mapping_required",
    "runtime_overlay": "runtime_overlay_profile_required",
}


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_canonical_json(payload))


def _row_number(row: dict[str, Any]) -> int:
    raw = str(row.get("chart1_row_id") or "")
    try:
        return int(raw.rsplit("-", 1)[-1])
    except ValueError:
        return 0


def _base_xy(row: dict[str, Any]) -> tuple[float, float]:
    number = max(_row_number(row) - 1, 0)
    column = number % 48
    band = number // 48
    return round(-179.75 + column * 0.25, 6), round(-79.75 + band * 0.25, 6)


def _point_geometry(row: dict[str, Any]) -> dict[str, Any]:
    x, y = _base_xy(row)
    return {"type": "Point", "coordinates": [x, y]}


def _line_geometry(row: dict[str, Any]) -> dict[str, Any]:
    x, y = _base_xy(row)
    return {
        "type": "LineString",
        "coordinates": [
            [x, y],
            [round(x + 0.08, 6), round(y + 0.045, 6)],
            [round(x + 0.16, 6), round(y, 6)],
        ],
    }


def _polygon_geometry(row: dict[str, Any]) -> dict[str, Any]:
    x, y = _base_xy(row)
    ring = [
        [round(x - 0.06, 6), round(y - 0.045, 6)],
        [round(x + 0.06, 6), round(y - 0.045, 6)],
        [round(x + 0.06, 6), round(y + 0.045, 6)],
        [round(x - 0.06, 6), round(y + 0.045, 6)],
        [round(x - 0.06, 6), round(y - 0.045, 6)],
    ]
    return {"type": "Polygon", "coordinates": [ring]}


def _fixture_geometry(row: dict[str, Any]) -> dict[str, Any]:
    taxonomy = row["row_taxonomy"]
    if taxonomy in {"area_fill", "conditional_rule"}:
        return _polygon_geometry(row)
    if taxonomy == "line_style":
        return _line_geometry(row)
    if taxonomy in {"point_symbol", "text_rule"}:
        return _point_geometry(row)
    raise ValueError(f"unsupported fixture taxonomy: {taxonomy}")


def _geometry_role(row: dict[str, Any]) -> str:
    taxonomy = row["row_taxonomy"]
    if taxonomy == "area_fill":
        return "representative_area_fill_polygon"
    if taxonomy == "conditional_rule":
        return "minimum_conditional_rule_polygon"
    if taxonomy == "line_style":
        return "representative_line_style_polyline"
    if taxonomy == "text_rule":
        return "label_anchor_point"
    if taxonomy == "point_symbol":
        return "stable_symbol_anchor_point"
    return "unsupported"


def _minimum_attributes(row: dict[str, Any]) -> dict[str, Any]:
    s57_tuple = dict(row["s57"].get("attribute_tuple") or {})
    status_condition = s57_tuple.get("status_condition") or {}
    s101 = row.get("s101") or {}
    portrayal = s101.get("portrayal_evidence") or {}
    merged: dict[str, Any] = {}
    if isinstance(status_condition, dict):
        merged.update(status_condition)
    if isinstance(portrayal.get("attributes"), dict):
        merged.update(portrayal["attributes"])
    if isinstance(s101.get("attributes"), dict):
        merged.update(s101["attributes"])
    return dict(sorted(merged.items()))


def _text_payload(row: dict[str, Any]) -> dict[str, Any] | None:
    text_refs = row["s52"].get("instruction_evidence", {}).get("text_refs") or []
    if not text_refs:
        return None
    values = {}
    for ref in text_refs:
        attribute = ref.get("attribute") or ref.get("template") or "TEXT"
        values[attribute] = f"fixture-{attribute}"
    return {
        "label_values": dict(sorted(values.items())),
        "text_refs": text_refs,
    }


def _expected_authority(row: dict[str, Any]) -> dict[str, Any]:
    instruction = row["s52"].get("instruction_evidence") or {}
    helm = row.get("helm") or {}
    return {
        "colour": {
            "s52_color_refs": instruction.get("color_refs") or [],
            "helm_colour_authority": helm.get("colour_authority") or {},
        },
        "pattern": {
            "s52_pattern_refs": instruction.get("pattern_refs") or [],
            "s52_line_style_refs": instruction.get("line_style_refs") or [],
        },
        "family": helm.get("shape_family_authority") or {},
    }


def _scale_context(row: dict[str, Any]) -> dict[str, Any]:
    tuple_ = row["s57"].get("attribute_tuple") or {}
    return {
        "fixture_context": "electronic_chart1_synthetic",
        "display_mode": tuple_.get("display_mode"),
        "feature_geometry": tuple_.get("geometry"),
        "scale_denominator": 12000,
        "palette_modes": ["day", "dusk", "night"],
        "declutter": "disabled_for_fixture",
    }


def _hard_reasons(row: dict[str, Any]) -> list[str]:
    reasons = set(row.get("reason_codes") or [])
    taxonomy = row["row_taxonomy"]
    if taxonomy in HARD_PILE_TAXONOMY_REASONS:
        reasons.add(HARD_PILE_TAXONOMY_REASONS[taxonomy])
    instruction = row["s52"].get("instruction_evidence") or {}
    if instruction.get("parse_status") != "complete":
        reasons.add("s52_instruction_ast:not_complete")
        for error in instruction.get("parse_errors") or []:
            reasons.add(f"s52_parse_error:{error}")
    if not reasons:
        reasons.add("fixture_generation:unsupported_or_underspecified")
    return sorted(reasons)


def _can_generate_fixture(row: dict[str, Any]) -> bool:
    if row["row_taxonomy"] not in FIXTURE_TAXONOMIES:
        return False
    instruction = row["s52"].get("instruction_evidence") or {}
    if instruction.get("parse_status") != "complete":
        return False
    return True


def _fixture_row(row: dict[str, Any], *, source: dict[str, Any]) -> dict[str, Any]:
    text = _text_payload(row)
    fixture = {
        "fixture_id": f"ec1-fixture-{row['chart1_row_id']}",
        "s52_lookup_id": row["s52_lookup_id"],
        "row_key": row["row_key"],
        "chart1_row_id": row["chart1_row_id"],
        "row_taxonomy": row["row_taxonomy"],
        "geometry_role": _geometry_role(row),
        "synthetic_geometry": _fixture_geometry(row),
        "s57": {
            "object_class": row["s57"].get("object_class"),
            "attribute_tuple": row["s57"].get("attribute_tuple") or {},
            "minimum_attributes": _minimum_attributes(row),
        },
        "s52": {
            "instruction": row["s52"].get("instruction"),
            "instruction_evidence": row["s52"].get("instruction_evidence") or {},
        },
        "s101": {
            "feature_type": row.get("s101", {}).get("feature_type"),
            "attributes": row.get("s101", {}).get("attributes") or {},
            "rule_file": row.get("s101", {}).get("rule_file"),
            "mapping_type": row.get("s101", {}).get("mapping_type"),
            "resolver_status": row.get("s101", {}).get("resolver_status"),
            "crosswalk_class": row.get("s101", {}).get("crosswalk_class"),
            "portrayal_evidence": row.get("s101", {}).get("portrayal_evidence") or {},
            "unresolved_reasons": row.get("s101", {}).get("unresolved_reasons") or [],
        },
        "helm": {
            "art_path": row.get("helm", {}).get("art_path"),
            "art_status": row.get("helm", {}).get("art_status"),
            "expected_authority": _expected_authority(row),
        },
        "context": _scale_context(row),
        "runtime_gate": {
            "render_eligibility": row["render_eligibility"],
            "runtime_eligible": bool(row.get("human_qa_status", {}).get("runtime_eligible")),
            "reason_codes": row.get("reason_codes") or [],
            "fail_closed": row["render_eligibility"] != "runtime_eligible",
        },
        "provenance": {
            "source_contract_schema": electronic_chart1_contract.SCHEMA,
            "source_db_sha256": source.get("db_sha256"),
            "source_db_view": source.get("view"),
            "clean_room_boundary": row.get("provenance", {}).get("clean_room_boundary"),
            "browser_business_logic_allowed": False,
            "static_json_fallback_allowed": False,
        },
    }
    if text:
        fixture["text"] = text
    return fixture


def _hard_pile_row(row: dict[str, Any], *, source: dict[str, Any]) -> dict[str, Any]:
    return {
        "s52_lookup_id": row["s52_lookup_id"],
        "row_key": row["row_key"],
        "chart1_row_id": row["chart1_row_id"],
        "row_taxonomy": row["row_taxonomy"],
        "evidence_status": row["evidence_status"],
        "reason_codes": _hard_reasons(row),
        "s57": {
            "object_class": row["s57"].get("object_class"),
            "attribute_tuple": row["s57"].get("attribute_tuple") or {},
        },
        "s52": {
            "instruction": row["s52"].get("instruction"),
            "instruction_evidence": row["s52"].get("instruction_evidence") or {},
        },
        "s101": {
            "feature_type": row.get("s101", {}).get("feature_type"),
            "rule_file": row.get("s101", {}).get("rule_file"),
            "mapping_type": row.get("s101", {}).get("mapping_type"),
            "resolver_status": row.get("s101", {}).get("resolver_status"),
            "unresolved_reasons": row.get("s101", {}).get("unresolved_reasons") or [],
        },
        "runtime_gate": {
            "render_eligibility": row["render_eligibility"],
            "runtime_eligible": bool(row.get("human_qa_status", {}).get("runtime_eligible")),
            "fail_closed": True,
        },
        "provenance": {
            "source_contract_schema": electronic_chart1_contract.SCHEMA,
            "source_db_sha256": source.get("db_sha256"),
            "source_db_view": source.get("view"),
            "clean_room_boundary": row.get("provenance", {}).get("clean_room_boundary"),
            "browser_business_logic_allowed": False,
            "static_json_fallback_allowed": False,
        },
    }


def build_fixtures(*, contract_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = contract_payload or electronic_chart1_contract.build_contract()
    if contract["schema"] != electronic_chart1_contract.SCHEMA:
        raise ValueError(f"unexpected source contract schema: {contract['schema']}")

    fixtures: list[dict[str, Any]] = []
    hard_pile: list[dict[str, Any]] = []
    source = contract.get("source") or {}
    for row in contract["rows"]:
        if _can_generate_fixture(row):
            fixtures.append(_fixture_row(row, source=source))
        else:
            hard_pile.append(_hard_pile_row(row, source=source))

    fixture_taxonomies = Counter(row["row_taxonomy"] for row in fixtures)
    hard_taxonomies = Counter(row["row_taxonomy"] for row in hard_pile)
    hard_reasons: Counter[str] = Counter()
    for row in hard_pile:
        hard_reasons.update(row["reason_codes"])

    accounted = len(fixtures) + len(hard_pile)
    total = len(contract["rows"])
    status = "fixtures_ready" if accounted == total and not _duplicates(fixtures, hard_pile) else "fixtures_blocked"
    return {
        "schema": SCHEMA,
        "status": status,
        "policy": {
            "source": "FORGE-39 electronic_chart1_contract",
            "generated_from_db_rows_only": True,
            "browser_business_logic_allowed": False,
            "static_json_fallback_allowed": False,
            "frontend_inference_allowed": False,
            "runtime_promotion_allowed": False,
            "clean_room_boundary": "Generated metadata and synthetic geometries only; no bundled IHO/OpenCPN artwork.",
            "accounting_rule": "fixtures + hard_pile must equal source contract rows",
        },
        "source": {
            "contract_schema": contract["schema"],
            "contract_status": contract["status"],
            "contract_db_sha256": contract["source"].get("db_sha256"),
            "contract_view": contract["source"].get("view"),
        },
        "summary": {
            "source_rows": total,
            "fixture_rows": len(fixtures),
            "hard_pile_rows": len(hard_pile),
            "accounted_rows": accounted,
            "unaccounted_rows": total - accounted,
            "duplicate_row_keys": _duplicates(fixtures, hard_pile),
            "fixture_taxonomy_counts": dict(sorted(fixture_taxonomies.items())),
            "hard_pile_taxonomy_counts": dict(sorted(hard_taxonomies.items())),
            "hard_pile_reason_counts": dict(hard_reasons.most_common(30)),
        },
        "fixtures": fixtures,
        "hard_pile": hard_pile,
    }


def _duplicates(fixtures: list[dict[str, Any]], hard_pile: list[dict[str, Any]]) -> list[str]:
    keys = [row["row_key"] for row in fixtures] + [row["row_key"] for row in hard_pile]
    counts = Counter(keys)
    return sorted(key for key, count in counts.items() if count > 1)


def _markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Electronic Chart 1 Synthetic Fixtures",
        "",
        "FORGE-40 deterministic synthetic fixture set generated from the FORGE-39 DB-backed contract.",
        "",
        f"- schema: `{payload['schema']}`",
        f"- status: `{payload['status']}`",
        f"- source_rows: `{summary['source_rows']}`",
        f"- fixture_rows: `{summary['fixture_rows']}`",
        f"- hard_pile_rows: `{summary['hard_pile_rows']}`",
        f"- unaccounted_rows: `{summary['unaccounted_rows']}`",
        "",
        "## Policy",
        "",
        "- Fixtures are generated from backend DB contract rows only.",
        "- Browser/UI consumers may display the generated facts but must not infer missing symbol meaning.",
        "- Static JSON fallbacks are forbidden; missing or under-specified rows stay in the hard pile.",
        "- Synthetic geometries are test inputs only and do not promote any symbol to runtime eligibility.",
        "",
        "## Fixture Taxonomy",
        "",
        "| Taxonomy | Count |",
        "| --- | ---: |",
    ]
    for name, count in summary["fixture_taxonomy_counts"].items():
        lines.append(f"| `{name}` | {count} |")
    lines.extend([
        "",
        "## Hard Pile Taxonomy",
        "",
        "| Taxonomy | Count |",
        "| --- | ---: |",
    ])
    for name, count in summary["hard_pile_taxonomy_counts"].items():
        lines.append(f"| `{name}` | {count} |")
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


def write_fixtures(
    *,
    json_path: Path = FIXTURES_JSON,
    markdown_path: Path = FIXTURES_MD,
) -> dict[str, Any]:
    payload = build_fixtures()
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
    parser.add_argument("--json", type=Path, default=FIXTURES_JSON)
    parser.add_argument("--markdown", type=Path, default=FIXTURES_MD)
    args = parser.parse_args(argv)
    print(json.dumps(write_fixtures(json_path=args.json, markdown_path=args.markdown), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
