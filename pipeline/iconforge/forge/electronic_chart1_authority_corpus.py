"""Build FORGE-44 authority text for electronic Chart 1 rows.

This artifact stores row-level human-readable authority text from backend data.
It is not generated in browser code and it does not promote runtime output.

Run:
  python3 -m forge.electronic_chart1_authority_corpus
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
CONTRACT_JSON = CATALOG / "electronic_chart1_contract.json"
FIXTURES_JSON = CATALOG / "electronic_chart1_fixtures.json"
OPENCPN_JSON = CATALOG / "electronic_chart1_opencpn_reference.json"
HELM_S57_JSON = CATALOG / "electronic_chart1_helm_s57_render.json"
HELM_S101_JSON = CATALOG / "electronic_chart1_helm_s101_render.json"
AUTHORITY_JSON = CATALOG / "electronic_chart1_authority_corpus.json"
AUTHORITY_MD = CATALOG / "electronic_chart1_authority_corpus.md"
SCHEMA = "helm.forge.electronic_chart1_authority_corpus.v1"


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


def _clean(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _sentence(value: Any, fallback: str) -> str:
    text = _clean(value)
    return text if text else fallback


def _list(values: Any, fallback: str = "none") -> str:
    if not values:
        return fallback
    if isinstance(values, dict):
        return json.dumps(values, sort_keys=True)
    if not isinstance(values, list):
        values = [values]
    return ", ".join(str(value) for value in values)


def _attrs(attrs: dict[str, Any]) -> str:
    if not attrs:
        return "none recorded"
    parts: list[str] = []
    for key in sorted(attrs):
        value = attrs[key]
        if isinstance(value, list):
            value_text = "[" + ", ".join(str(item) for item in value) + "]"
        elif isinstance(value, dict):
            value_text = json.dumps(value, sort_keys=True)
        else:
            value_text = str(value)
        parts.append(f"{key}={value_text}")
    return "; ".join(parts)


def _index_rows(payload: dict[str, Any], key: str = "rows") -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in payload.get(key, []) or []:
        out[row["row_key"]] = row
    return out


def _index_all_rows(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for bucket in ("rows", "hard_pile"):
        for row in payload.get(bucket, []) or []:
            out[row["row_key"]] = row
    return out


def _global_language() -> dict[str, Any]:
    return {
        "version": "helm_authority_language_v1",
        "colour_language": {
            "solid": "A single named color token fills the feature or symbol.",
            "ordered_sequence": "Colors must preserve the source order because the order is part of the navigational identity.",
            "horizontal_bands": "Bands are stacked vertically in the listed color order.",
            "vertical_stripes": "Stripes run vertically in the listed color order.",
            "border_stripe": "A border or edge stripe is part of the color identity and must not be collapsed into a solid fill.",
            "not_colour_bearing_or_pending": "The current row has no resolved feature color authority; render color must come from explicit S-52/Helm renderer evidence or remain a gap.",
        },
        "shape_language": {
            "buoy": "Preserve body silhouette, color order, topmark where present, and chart anchor.",
            "beacon": "Preserve fixed-aid silhouette, dayboard or topmark context, color order, and label/text placement.",
            "topmark": "Topmark geometry is semantic, especially cone, sphere, cross, X, T, rhombus, and multiple-cone orientation.",
            "line_style": "Line samples prove stroke, dash/dot pattern, color token, and geometry role separately from point symbols.",
            "area_fill": "Area samples prove fill/pattern behavior; point-symbol assumptions are not allowed.",
            "conditional_rule": "Conditional rows must retain the named procedure and derived attributes; filename-only matching is insufficient.",
            "simplified_symbol": "Simplified symbols may remove decorative detail but must keep semantic silhouette and source color identity.",
        },
        "consumer_rule": {
            "browser_business_logic_allowed": False,
            "frontend_written_prose_allowed": False,
            "static_json_fallback_allowed": False,
            "runtime_promotion_allowed": False,
        },
    }


def _s52_text(row: dict[str, Any]) -> dict[str, Any]:
    s52 = row.get("s52") or {}
    evidence = s52.get("instruction_evidence") or {}
    parse_status = evidence.get("parse_status")
    refs = {
        "symbols": evidence.get("symbol_refs") or [],
        "conditional_rules": evidence.get("conditional_refs") or [],
        "line_styles": evidence.get("line_style_refs") or [],
        "area_patterns": evidence.get("pattern_refs") or [],
        "text": [ref.get("attribute") for ref in evidence.get("text_refs") or [] if ref.get("attribute")],
        "colours": evidence.get("color_refs") or [],
    }
    text = (
        f"S-52/OpenCPN evidence uses instruction {_sentence(s52.get('instruction'), 'none recorded')} "
        f"with parse status {parse_status or 'missing'} and command sequence {_list(evidence.get('command_sequence') or [])}. "
        f"Referenced symbols: {_list(refs['symbols'])}; conditional rules: {_list(refs['conditional_rules'])}; "
        f"line styles: {_list(refs['line_styles'])}; area patterns: {_list(refs['area_patterns'])}; "
        f"text attributes: {_list(refs['text'])}; color refs: {_list(refs['colours'])}."
    )
    gaps: list[str] = []
    if not s52.get("instruction"):
        gaps.append("s52_instruction:missing")
    if parse_status != "complete":
        gaps.append(f"s52_parse_status:{parse_status or 'missing'}")
    return {"text": text, "refs": refs, "gaps": gaps}


def _s57_text(row: dict[str, Any]) -> dict[str, Any]:
    s57 = row.get("s57") or {}
    tuple_ = s57.get("attribute_tuple") or {}
    semantic_brief = tuple_.get("semantic_brief")
    text = (
        f"S-57 evidence identifies object class {s57.get('object_class') or tuple_.get('object_class') or 'unknown'} "
        f"with geometry {tuple_.get('geometry') or 'unknown'}, category {tuple_.get('category') or 'unknown'}, "
        f"shape {tuple_.get('shape') or 'unknown'}, display mode {tuple_.get('display_mode') or 'unknown'}, "
        f"color sequence {_list(tuple_.get('colour_sequence') or [])}, color pattern {tuple_.get('colour_pattern') or 'none'}, "
        f"and topmark {tuple_.get('topmark') or 'none'}. "
        f"Semantic brief: {_sentence(semantic_brief, 'missing')}."
    )
    gaps: list[str] = []
    if not semantic_brief:
        gaps.append("s57_semantic_brief:missing")
    if not tuple_.get("object_class") and not s57.get("object_class"):
        gaps.append("s57_object_class:missing")
    if not tuple_.get("geometry"):
        gaps.append("s57_geometry:missing")
    return {"text": text, "attribute_tuple": tuple_, "gaps": gaps}


def _s101_text(row: dict[str, Any], s101_trace_row: dict[str, Any] | None) -> dict[str, Any]:
    if s101_trace_row:
        trace = s101_trace_row["s101_trace"]
        status = s101_trace_row["status"]
        reason_codes = s101_trace_row.get("reason_codes") or []
    else:
        raw = row.get("s101") or {}
        trace = {
            "classification": raw.get("resolver_status") or raw.get("mapping_type") or "missing",
            "mapping_type": raw.get("mapping_type"),
            "resolver_status": raw.get("resolver_status"),
            "crosswalk_class": raw.get("crosswalk_class"),
            "feature_type": raw.get("feature_type"),
            "rule_file": raw.get("rule_file"),
            "attributes": raw.get("attributes") or {},
            "unresolved_reasons": raw.get("unresolved_reasons") or [],
            "db_backed": bool(raw.get("resolver_status") or raw.get("rule_file") or raw.get("direct_symbol_id")),
            "filename_only_match": False,
        }
        status = "contract_only_no_forge43_trace"
        reason_codes = ["forge43_trace:missing_for_row"]
    text = (
        f"S-101 evidence classification {trace.get('classification') or 'missing'} with mapping type "
        f"{trace.get('mapping_type') or 'missing'}, resolver status {trace.get('resolver_status') or 'missing'}, "
        f"crosswalk class {trace.get('crosswalk_class') or 'missing'}, feature {trace.get('feature_type') or 'not resolved'}, "
        f"rule file {trace.get('rule_file') or 'none'}, attributes {_attrs(trace.get('attributes') or {})}, "
        f"and unresolved reasons {_list(trace.get('unresolved_reasons') or [])}."
    )
    gaps: list[str] = []
    if not trace.get("feature_type"):
        gaps.append("s101_feature_type:missing")
    if trace.get("classification") in {None, "missing", "unresolved"}:
        gaps.append("s101_classification:unresolved")
    if not trace.get("db_backed"):
        gaps.append("s101_db_backing:missing")
    if "forge43_trace:missing_for_row" in reason_codes:
        gaps.append("s101_forge43_trace:missing")
    return {
        "text": text,
        "trace": trace,
        "status": status,
        "reason_codes": reason_codes,
        "gaps": gaps,
    }


def _helm_authority_text(
    row: dict[str, Any],
    opencpn_row: dict[str, Any] | None,
    helm_s57_row: dict[str, Any] | None,
    s101_trace_row: dict[str, Any] | None,
) -> dict[str, Any]:
    helm = row.get("helm") or {}
    colour = helm.get("colour_authority") or {}
    family = helm.get("shape_family_authority") or {}
    recipe = None
    render_sources: list[str] = []
    if helm_s57_row:
        recipe = (helm_s57_row.get("helm_trace") or {}).get("recipe") or {}
        render_sources.extend((helm_s57_row.get("helm_trace") or {}).get("render_sources") or [])
    if s101_trace_row and s101_trace_row.get("helm_candidate_render", {}).get("recipe"):
        recipe = s101_trace_row["helm_candidate_render"]["recipe"]
        render_sources.extend(s101_trace_row["helm_candidate_render"].get("render_sources") or [])
    text = (
        f"Helm authority uses art path {helm.get('art_path') or 'none'} with art status {helm.get('art_status') or 'missing'}, "
        f"shape family {family.get('family') or 'unknown'} / shape {family.get('shape') or 'unknown'} "
        f"from {family.get('source') or 'missing source'}, color authority status {colour.get('status') or 'missing'} "
        f"with colors {_list(colour.get('colour_sequence') or [])} and pattern {colour.get('colour_pattern') or 'none'}. "
        f"Recipe shape family {(recipe or {}).get('shape_family') or 'missing'}, color tokens "
        f"{_list((recipe or {}).get('color_tokens') or [])}, pattern token {(recipe or {}).get('pattern_token') or 'none'}, "
        f"and render sources {_list(sorted(set(render_sources)))}."
    )
    gaps: list[str] = []
    if opencpn_row is None:
        gaps.append("opencpn_reference_render:missing")
    if helm_s57_row is None:
        gaps.append("helm_s57_render:missing")
    if s101_trace_row is None:
        gaps.append("helm_s101_trace:missing")
    if not recipe:
        gaps.append("helm_recipe:missing")
    if not family.get("shape"):
        gaps.append("helm_shape_family:missing")
    return {
        "text": text,
        "art_path": helm.get("art_path"),
        "colour_authority": colour,
        "shape_family_authority": family,
        "recipe": recipe or {},
        "render_sources": sorted(set(render_sources)),
        "gaps": gaps,
    }


def _interpretation_status(gaps: list[str], row: dict[str, Any]) -> str:
    if row.get("row_taxonomy") in {"placeholder_manual", "non_reviewable_construct"}:
        return "authority_text_manual_required"
    if gaps:
        return "authority_text_pending_source"
    return "authority_text_ready"


def _helm_interpretation(
    row: dict[str, Any],
    s52: dict[str, Any],
    s57: dict[str, Any],
    s101: dict[str, Any],
    helm: dict[str, Any],
    gaps: list[str],
) -> dict[str, Any]:
    tuple_ = row.get("s57", {}).get("attribute_tuple") or {}
    status = _interpretation_status(gaps, row)
    confidence = "high" if status == "authority_text_ready" else "medium" if status == "authority_text_pending_source" else "manual_required"
    sections = {
        "what_it_is": (
            f"{row['row_key']} is an Electronic Chart 1 {row.get('row_taxonomy') or 'chart'} row representing "
            f"{_sentence(tuple_.get('semantic_brief'), row.get('row_taxonomy', 'a chart row'))}."
        ),
        "opencpn_s52_evidence": s52["text"],
        "s57_description": s57["text"],
        "s101_summary": s101["text"],
        "helm_render_interpretation": helm["text"],
        "clean_room_boundary": (
            "This prose is generated from backend/export evidence. OpenCPN and S-101 references are comparison and "
            "standards-vocabulary evidence; Helm-owned render outputs remain separate from third-party artwork."
        ),
        "runtime_status": (
            f"Runtime export remains {row.get('render_eligibility')}; final approved is "
            f"{bool((row.get('human_qa_status') or {}).get('final_approved'))}."
        ),
    }
    caveats = sorted(set(gaps + (row.get("reason_codes") or []) + (s101.get("reason_codes") or [])))
    text = " ".join(sections[key] for key in [
        "what_it_is",
        "opencpn_s52_evidence",
        "s57_description",
        "s101_summary",
        "helm_render_interpretation",
        "clean_room_boundary",
        "runtime_status",
    ])
    if caveats:
        text += " Known gaps: " + "; ".join(caveats) + "."
    return {
        "version": "helm_electronic_chart1_authority_text_v1",
        "status": status,
        "confidence": confidence,
        "review_status": "needs_human_review",
        "text": text,
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "sections": sections,
        "known_gaps": caveats,
        "source_refs": {
            "contract_row": "catalog/electronic_chart1_contract.json",
            "opencpn_reference": "catalog/electronic_chart1_opencpn_reference.json",
            "helm_s57_render": "catalog/electronic_chart1_helm_s57_render.json",
            "helm_s101_trace": "catalog/electronic_chart1_helm_s101_render.json",
        },
        "browser_generation_allowed": False,
        "frontend_written_prose_allowed": False,
        "runtime_export_allowed": False,
    }


def _validate(row: dict[str, Any]) -> dict[str, Any]:
    text = row["helm_interpretation"]["text"]
    expected = [
        row["row_key"],
        row.get("row_taxonomy"),
        row["s57_authority"]["attribute_tuple"].get("object_class") or row.get("s57_object_class"),
    ]
    reasons: list[str] = []
    for value in expected:
        if value and str(value).lower() not in text.lower():
            reasons.append(f"text_missing:{value}")
    if row["runtime_gate"]["runtime_eligible"]:
        reasons.append("runtime_eligible_must_remain_false")
    if row["consumer_contract"]["browser_business_logic_allowed"]:
        reasons.append("browser_business_logic_enabled")
    return {
        "status": "passed" if not reasons else "failed",
        "reason_codes": sorted(set(reasons)),
        "validator": "electronic_chart1_authority_corpus_validator_v1",
    }


def _build_row(
    row: dict[str, Any],
    opencpn_rows: dict[str, dict[str, Any]],
    helm_s57_rows: dict[str, dict[str, Any]],
    helm_s101_rows: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    opencpn_row = opencpn_rows.get(row["row_key"])
    helm_s57_row = helm_s57_rows.get(row["row_key"])
    helm_s101_row = helm_s101_rows.get(row["row_key"])
    s52 = _s52_text(row)
    s57 = _s57_text(row)
    s101 = _s101_text(row, helm_s101_row)
    helm = _helm_authority_text(row, opencpn_row, helm_s57_row, helm_s101_row)
    gaps = sorted(set(s52["gaps"] + s57["gaps"] + s101["gaps"] + helm["gaps"]))
    interpretation = _helm_interpretation(row, s52, s57, s101, helm, gaps)
    out = {
        "chart1_row_id": row["chart1_row_id"],
        "s52_lookup_id": row["s52_lookup_id"],
        "row_key": row["row_key"],
        "row_taxonomy": row["row_taxonomy"],
        "evidence_status": row["evidence_status"],
        "s57_object_class": (row.get("s57") or {}).get("object_class"),
        "s52_authority": s52,
        "s57_authority": s57,
        "s101_authority": s101,
        "helm_authority": helm,
        "helm_interpretation": interpretation,
        "source_language_gaps": gaps,
        "runtime_gate": {
            "runtime_eligible": False,
            "render_eligibility": row.get("render_eligibility"),
            "fail_closed": True,
            "reason_codes": sorted(set(row.get("reason_codes") or [])),
        },
        "consumer_contract": {
            "backend_generated": True,
            "browser_business_logic_allowed": False,
            "frontend_written_prose_allowed": False,
            "static_json_fallback_allowed": False,
            "runtime_promotion_allowed": False,
        },
    }
    out["validation"] = _validate(out)
    return out


def build_corpus(
    *,
    contract_path: Path = CONTRACT_JSON,
    fixtures_path: Path = FIXTURES_JSON,
    opencpn_path: Path = OPENCPN_JSON,
    helm_s57_path: Path = HELM_S57_JSON,
    helm_s101_path: Path = HELM_S101_JSON,
    limit: int | None = None,
) -> dict[str, Any]:
    contract = _load_json(contract_path)
    if contract["schema"] != "helm.forge.electronic_chart1_contract.v1":
        raise ValueError(f"unexpected contract schema: {contract['schema']}")
    fixtures = _load_json(fixtures_path)
    opencpn = _load_json(opencpn_path)
    helm_s57 = _load_json(helm_s57_path)
    helm_s101 = _load_json(helm_s101_path)
    opencpn_rows = _index_rows(opencpn)
    helm_s57_rows = _index_rows(helm_s57)
    helm_s101_rows = _index_all_rows(helm_s101)
    rows = [
        _build_row(row, opencpn_rows, helm_s57_rows, helm_s101_rows)
        for row in contract["rows"][:limit]
    ]
    summary = _summary(contract, fixtures, opencpn, helm_s57, helm_s101, rows, limit)
    return {
        "schema": SCHEMA,
        "status": "electronic_chart1_authority_corpus_ready" if summary["validation_counts"] == {"passed": len(rows)} else "electronic_chart1_authority_corpus_failed",
        "policy": {
            "backend_generated": True,
            "browser_business_logic_allowed": False,
            "frontend_written_prose_allowed": False,
            "static_json_fallback_allowed": False,
            "llm_batch_allowed": True,
            "llm_page_load_generation_allowed": False,
            "runtime_promotion_allowed": False,
            "missing_source_language_must_be_explicit_gap": True,
            "clean_room_boundary": "Authority text is generated from backend metadata/proof artifacts; comparison references are not bundled Helm source artwork.",
        },
        "source": {
            "contract": {"path": str(contract_path), "schema": contract["schema"], "sha256": _sha256(contract_path)},
            "fixtures": {"path": str(fixtures_path), "schema": fixtures["schema"], "sha256": _sha256(fixtures_path)},
            "opencpn_reference": {"path": str(opencpn_path), "schema": opencpn["schema"], "sha256": _sha256(opencpn_path)},
            "helm_s57_render": {"path": str(helm_s57_path), "schema": helm_s57["schema"], "sha256": _sha256(helm_s57_path)},
            "helm_s101_trace": {"path": str(helm_s101_path), "schema": helm_s101["schema"], "sha256": _sha256(helm_s101_path)},
        },
        "global_language": _global_language(),
        "summary": summary,
        "rows": rows,
    }


def _summary(
    contract: dict[str, Any],
    fixtures: dict[str, Any],
    opencpn: dict[str, Any],
    helm_s57: dict[str, Any],
    helm_s101: dict[str, Any],
    rows: list[dict[str, Any]],
    limit: int | None,
) -> dict[str, Any]:
    validation_counts = Counter(row["validation"]["status"] for row in rows)
    status_counts = Counter(row["helm_interpretation"]["status"] for row in rows)
    taxonomy_counts = Counter(row["row_taxonomy"] for row in rows)
    gap_counts: Counter[str] = Counter()
    for row in rows:
        gap_counts.update(row["source_language_gaps"])
    return {
        "contract_rows": len(contract["rows"][:limit]),
        "authority_rows": len(rows),
        "fixture_rows": len(fixtures.get("fixtures") or []),
        "opencpn_reference_rows": len(opencpn.get("rows") or []),
        "helm_s57_render_rows": len(helm_s57.get("rows") or []),
        "helm_s101_trace_rows": len(helm_s101.get("rows") or []),
        "helm_s101_fail_closed_rows": len(helm_s101.get("hard_pile") or []),
        "runtime_eligible_rows": 0,
        "status_counts": dict(sorted(status_counts.items())),
        "validation_counts": dict(sorted(validation_counts.items())),
        "row_taxonomy_counts": dict(sorted(taxonomy_counts.items())),
        "source_language_gap_counts": dict(gap_counts.most_common(30)),
    }


def _markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Electronic Chart 1 Authority Corpus",
        "",
        "FORGE-44 backend-generated authority text for Electronic Chart 1 rows.",
        "",
        f"- schema: `{payload['schema']}`",
        f"- status: `{payload['status']}`",
        f"- authority_rows: `{summary['authority_rows']}`",
        f"- fixture_rows: `{summary['fixture_rows']}`",
        f"- runtime_eligible_rows: `{summary['runtime_eligible_rows']}`",
        "",
        "## Policy",
        "",
        "- Authority prose is generated from backend/export evidence, not browser code.",
        "- Missing source language is recorded as row-level gaps.",
        "- Global language covers colors, bands/stripes, topmarks, simplified symbols, line styles, area fills, and conditional rules.",
        "- Runtime export remains fail-closed.",
        "",
        "## Interpretation Status Counts",
        "",
        "| Status | Count |",
        "| --- | ---: |",
    ]
    for status, count in summary["status_counts"].items():
        lines.append(f"| `{status}` | {count} |")
    lines.extend([
        "",
        "## Validation Counts",
        "",
        "| Status | Count |",
        "| --- | ---: |",
    ])
    for status, count in summary["validation_counts"].items():
        lines.append(f"| `{status}` | {count} |")
    lines.extend([
        "",
        "## Source Language Gaps",
        "",
        "| Gap | Count |",
        "| --- | ---: |",
    ])
    for gap, count in summary["source_language_gap_counts"].items():
        lines.append(f"| `{gap}` | {count} |")
    return "\n".join(lines) + "\n"


def write_corpus(
    *,
    contract_path: Path = CONTRACT_JSON,
    fixtures_path: Path = FIXTURES_JSON,
    opencpn_path: Path = OPENCPN_JSON,
    helm_s57_path: Path = HELM_S57_JSON,
    helm_s101_path: Path = HELM_S101_JSON,
    json_path: Path = AUTHORITY_JSON,
    markdown_path: Path = AUTHORITY_MD,
    limit: int | None = None,
) -> dict[str, Any]:
    payload = build_corpus(
        contract_path=contract_path,
        fixtures_path=fixtures_path,
        opencpn_path=opencpn_path,
        helm_s57_path=helm_s57_path,
        helm_s101_path=helm_s101_path,
        limit=limit,
    )
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
    parser.add_argument("--contract", type=Path, default=CONTRACT_JSON)
    parser.add_argument("--fixtures", type=Path, default=FIXTURES_JSON)
    parser.add_argument("--opencpn-reference", type=Path, default=OPENCPN_JSON)
    parser.add_argument("--helm-s57-render", type=Path, default=HELM_S57_JSON)
    parser.add_argument("--helm-s101-trace", type=Path, default=HELM_S101_JSON)
    parser.add_argument("--json", type=Path, default=AUTHORITY_JSON)
    parser.add_argument("--markdown", type=Path, default=AUTHORITY_MD)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args(argv)
    print(json.dumps(
        write_corpus(
            contract_path=args.contract,
            fixtures_path=args.fixtures,
            opencpn_path=args.opencpn_reference,
            helm_s57_path=args.helm_s57_render,
            helm_s101_path=args.helm_s101_trace,
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
