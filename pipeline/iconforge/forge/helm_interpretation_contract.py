"""Build the FORGE-29 Helm interpretation contract.

The interpretation contract stores the human-readable explanation that proof
pages, judge prompts, repair agents, and maintainers read. It is generated from
backend DB evidence and recipe fields. Browser code may display it, but must not
generate or alter it.

Run:
  python3 -m forge.helm_interpretation_contract
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"

DEFAULT_OUT = CATALOG / "helm_interpretation_contract.json"
DEFAULT_MD = CATALOG / "helm_interpretation_contract.md"

INTERPRETATION_VERSION = "helm_interpretation_v1"
PROMPT_VERSION = "helm_interpretation_prompt_v1"
OUTPUT_SCHEMA_VERSION = "helm_interpretation_output_schema_v1"

READY = "helm_interpretation_ready"
PENDING = "helm_interpretation_pending_evidence"
MANUAL = "helm_interpretation_manual_required"
VALID_STATUSES = {READY, PENDING, MANUAL}

MANUAL_CROSSWALK_CLASSES = {
    "non_s101_runtime_construct",
    "non_s101_or_inland_extension",
}
MANUAL_RULE_STATUSES = {
    "non_s101_runtime_construct",
    "non_s101_or_extension_profile_required",
}
PENDING_RULE_STATUSES = {
    "malformed_attribute_tuple",
    "missing_s101_feature_type",
    "missing_s101_rule_file",
    "direct_asset_reference_incomplete",
    "manual_rule_contract_required",
}

PROMPT_CONTRACT = {
    "prompt_version": PROMPT_VERSION,
    "output_schema_version": OUTPUT_SCHEMA_VERSION,
    "generation_mode": "deterministic_backend_batch",
    "llm_batch_allowed": True,
    "llm_batch_required": False,
    "llm_page_load_generation_allowed": False,
    "browser_business_logic_allowed": False,
    "source_of_truth": "catalog/semantic_evidence_db.json",
    "required_inputs": [
        "open_cpn_description",
        "s57_object",
        "s57_attribute_tuple",
        "s52_instruction_ast",
        "s101_rule_contract",
        "helm_symbol_recipe",
        "source_refs",
        "unresolved_reasons",
    ],
}

OUTPUT_SCHEMA = {
    "schema": OUTPUT_SCHEMA_VERSION,
    "required_fields": [
        "version",
        "status",
        "text",
        "sections",
        "required_values",
        "validation",
        "prompt_contract",
    ],
    "valid_statuses": sorted(VALID_STATUSES),
    "contradiction_policy": (
        "Validators reject stored interpretation payloads whose required values "
        "conflict with the DB row or whose prose omits safety-relevant DB facts."
    ),
}


def _write(path: Path, body: Any) -> None:
    path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")


def _clean(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _sentence(value: Any, fallback: str = "No stored evidence.") -> str:
    text = _clean(value)
    return text if text else fallback


def _token_list(values: Any, fallback: str = "none") -> str:
    if not values:
        return fallback
    return ", ".join(str(value) for value in values)


def _attrs(attrs: dict[str, Any]) -> str:
    if not attrs:
        return "none recorded"
    parts = []
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


def _topmark_value(row: dict[str, Any]) -> str | None:
    tuple_ = row.get("s57_attribute_tuple") or {}
    attrs = row.get("s101_attributes") or {}
    for key in ("topmark", "topmark_daymark_shape"):
        if tuple_.get(key) not in (None, "", [], {}):
            return str(tuple_[key])
    for key in ("topmarkDaymarkShape", "topmarkShape"):
        if attrs.get(key) not in (None, "", [], {}):
            return str(attrs[key])
    return None


def _expected_values(row: dict[str, Any]) -> dict[str, Any]:
    recipe = row.get("helm_symbol_recipe") or {}
    s57_object = row.get("s57_object") or {}
    tuple_ = row.get("s57_attribute_tuple") or {}
    return {
        "symbol_id": row.get("symbol_id"),
        "s57_object_class": s57_object.get("object_class"),
        "s52_instruction": row.get("s52_instruction"),
        "s101_feature_type": row.get("s101_feature_type"),
        "s101_rule_file": row.get("s101_rule_file"),
        "s101_crosswalk_class": row.get("s101_crosswalk_class"),
        "shape_family": recipe.get("shape_family"),
        "color_tokens": recipe.get("color_tokens") or [],
        "pattern_token": recipe.get("pattern_token"),
        "recipe_status": recipe.get("status"),
        "topmark": _topmark_value(row),
        "s57_shape": tuple_.get("shape"),
        "s57_category": tuple_.get("category"),
    }


def _base_status(row: dict[str, Any]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    recipe_status = row.get("helm_symbol_recipe_status")
    crosswalk_class = row.get("s101_crosswalk_class")
    rule_status = row.get("s101_rule_contract_status")

    if crosswalk_class in MANUAL_CROSSWALK_CLASSES:
        reasons.append(f"s101_crosswalk:{crosswalk_class}")
    if rule_status in MANUAL_RULE_STATUSES:
        reasons.append(f"s101_rule_contract:{rule_status}")
    if recipe_status == "manual_exception_required":
        reasons.append("helm_symbol_recipe:manual_exception_required")

    if reasons:
        return MANUAL, sorted(set(reasons))

    pending: list[str] = []
    if recipe_status != "recipe_ready":
        pending.append(f"helm_symbol_recipe:{recipe_status}")
    if rule_status in PENDING_RULE_STATUSES:
        pending.append(f"s101_rule_contract:{rule_status}")

    if pending:
        return PENDING, sorted(set(pending))
    return READY, []


def _s101_basis(row: dict[str, Any]) -> str:
    crosswalk_class = row.get("s101_crosswalk_class") or "unknown"
    feature = row.get("s101_feature_type")
    rule_file = row.get("s101_rule_file")
    attrs = row.get("s101_attributes") or {}
    mapping_type = row.get("s101_mapping_type") or "unknown"
    status = row.get("s101_rule_contract_status") or "unknown"

    if crosswalk_class == "non_s101_runtime_construct":
        return (
            "S-101 basis: this row is a runtime/display construct, not an S-101 "
            f"feature mapping. Candidate feature is {feature or 'none'}; "
            f"mapping type is {mapping_type}; contract status is {status}."
        )
    if crosswalk_class == "non_s101_or_inland_extension":
        return (
            "S-101 basis: this row is a non-S-101 or inland-extension profile. "
            f"Candidate feature is {feature or 'none'}; mapping type is {mapping_type}; "
            f"contract status is {status}."
        )

    pieces = [
        f"S-101 basis: feature {feature or 'not resolved'}",
        f"mapping type {mapping_type}",
        f"contract status {status}",
    ]
    if rule_file:
        pieces.append(f"rule file {rule_file}")
    pieces.append(f"attributes {_attrs(attrs)}")
    return "; ".join(pieces) + "."


def _invariants(row: dict[str, Any]) -> list[str]:
    expected = _expected_values(row)
    invariants = [
        f"symbol_id={expected['symbol_id']}",
        f"s57_object_class={expected['s57_object_class']}",
        f"shape_family={expected['shape_family']}",
        f"color_tokens={_token_list(expected['color_tokens'])}",
        f"pattern_token={expected['pattern_token']}",
        f"recipe_status={expected['recipe_status']}",
        f"s101_crosswalk_class={expected['s101_crosswalk_class']}",
    ]
    if expected.get("s101_feature_type"):
        invariants.append(f"s101_feature_type={expected['s101_feature_type']}")
    if expected.get("topmark"):
        invariants.append(f"topmark={expected['topmark']}")
    return invariants


def _sections(row: dict[str, Any], status: str, reason_codes: list[str]) -> dict[str, Any]:
    expected = _expected_values(row)
    recipe = row.get("helm_symbol_recipe") or {}
    s57_tuple = row.get("s57_attribute_tuple") or {}
    s52_ast = row.get("s52_instruction_ast") or {}
    unresolved = row.get("unresolved_reasons") or []

    what = (
        f"{expected['symbol_id']} is {_sentence(row.get('open_cpn_description'), expected['symbol_id'])}. "
        f"Helm stores this as {expected['shape_family'] or 'an unresolved shape family'} "
        f"with interpretation status {status}."
    )
    usage = _sentence(row.get("s57_description"))
    s57_basis = (
        f"S-57 basis: object class {expected['s57_object_class'] or 'unknown'}; "
        f"category {s57_tuple.get('category') or 'unknown'}; "
        f"shape {s57_tuple.get('shape') or 'unknown'}; "
        f"colour sequence {_token_list(s57_tuple.get('colour_sequence') or [])}; "
        f"colour pattern {s57_tuple.get('colour_pattern') or 'none'}."
    )
    s52_basis = (
        f"S-52 basis: instruction {_sentence(row.get('s52_instruction'))}; "
        f"AST status {row.get('s52_instruction_ast_status')}; "
        f"symbols {_token_list(s52_ast.get('symbols') or [])}; "
        f"conditional procedures {_token_list(s52_ast.get('conditional_procedures') or [])}."
    )
    recipe_basis = (
        f"Helm recipe: shape_family={recipe.get('shape_family')}; "
        f"color_tokens={_token_list(recipe.get('color_tokens') or [])}; "
        f"pattern_token={recipe.get('pattern_token')}; "
        f"palette_version={recipe.get('palette_version')}; "
        f"style_version={recipe.get('style_version')}; "
        f"recipe_status={recipe.get('status')}."
    )
    clean_room = (
        "Clean-room/render note: this interpretation is generated from backend DB "
        "evidence, standards vocabulary, and Helm-owned recipe tokens. OpenCPN and "
        "S-101 material remain comparison/evidence references; browser JavaScript "
        "must not derive symbol meaning, colors, patterns, or runtime gates."
    )
    caveats = sorted(set(str(reason) for reason in reason_codes + unresolved if reason))
    if row.get("evidence_gap_reasons"):
        caveats.extend(str(reason) for reason in row["evidence_gap_reasons"])
    caveats = sorted(set(caveats))

    return {
        "what_it_is": what,
        "use_and_safety_context": usage,
        "s57_basis": s57_basis,
        "s52_basis": s52_basis,
        "s101_basis": _s101_basis(row),
        "helm_recipe": recipe_basis,
        "clean_room_render_notes": clean_room,
        "repair_judge_invariants": _invariants(row),
        "known_caveats": caveats,
    }


def _flatten_text(sections: dict[str, Any]) -> str:
    pieces: list[str] = []
    for key in [
        "what_it_is",
        "use_and_safety_context",
        "s57_basis",
        "s52_basis",
        "s101_basis",
        "helm_recipe",
        "clean_room_render_notes",
    ]:
        pieces.append(_sentence(sections.get(key)))
    invariants = sections.get("repair_judge_invariants") or []
    if invariants:
        pieces.append("Repair/judge invariants: " + "; ".join(str(item) for item in invariants) + ".")
    caveats = sections.get("known_caveats") or []
    if caveats:
        pieces.append("Known caveats: " + "; ".join(str(item) for item in caveats) + ".")
    return " ".join(pieces)


def _contains(text: str, value: Any) -> bool:
    if value in (None, "", [], {}):
        return True
    return str(value).lower() in text.lower()


def validate_interpretation(row: dict[str, Any], interpretation: dict[str, Any]) -> dict[str, Any]:
    expected = _expected_values(row)
    required = interpretation.get("required_values") or {}
    text = str(interpretation.get("text") or "")
    reasons: list[str] = []

    if interpretation.get("status") not in VALID_STATUSES:
        reasons.append(f"invalid_status:{interpretation.get('status')}")

    for key, expected_value in expected.items():
        if expected_value in (None, "", [], {}):
            continue
        actual_value = required.get(key)
        if actual_value != expected_value:
            reasons.append(f"conflicting_required_value:{key}")

    text_checks = [
        "symbol_id",
        "s57_object_class",
        "shape_family",
        "pattern_token",
        "recipe_status",
        "s101_crosswalk_class",
        "s101_feature_type",
        "topmark",
    ]
    for key in text_checks:
        value = expected.get(key)
        if value in (None, "", [], {}):
            continue
        if not _contains(text, value):
            reasons.append(f"text_missing:{key}:{value}")

    for token in expected.get("color_tokens") or []:
        if not _contains(text, token):
            reasons.append(f"text_missing:color_token:{token}")

    base_status, _ = _base_status(row)
    if interpretation.get("status") == READY and base_status != READY:
        reasons.append(f"ready_status_conflicts_with_base_status:{base_status}")

    return {
        "status": "passed" if not reasons else "failed",
        "reason_codes": sorted(set(reasons)),
        "validator": "helm_interpretation_validator_v1",
    }


def interpretation_for_row(row: dict[str, Any]) -> dict[str, Any]:
    status, reason_codes = _base_status(row)
    sections = _sections(row, status, reason_codes)
    interpretation = {
        "version": INTERPRETATION_VERSION,
        "status": status,
        "reason_codes": list(reason_codes),
        "text": _flatten_text(sections),
        "sections": sections,
        "required_values": _expected_values(row),
        "prompt_contract": deepcopy(PROMPT_CONTRACT),
        "output_schema_version": OUTPUT_SCHEMA_VERSION,
        "source_fields": {
            "semantic_evidence_db": "catalog/semantic_evidence_db.json",
            "s52_instruction_ast": "s52_instruction_ast",
            "s101_rule_contract": "s101_rule_contract",
            "helm_symbol_recipe": "helm_symbol_recipe",
        },
        "browser_generation_allowed": False,
        "backend_resolved": True,
        "runtime_export_allowed": False,
    }
    validation = validate_interpretation(row, interpretation)
    if validation["status"] != "passed" and status == READY:
        status = PENDING
        interpretation["status"] = status
        interpretation["reason_codes"] = sorted(set(reason_codes + ["interpretation_validation_failed"]))
    interpretation["validation"] = validation
    return interpretation


def build() -> dict[str, Any]:
    from . import semantic_evidence_db

    semantic = semantic_evidence_db.build()
    rows = []
    for row in semantic["rows"]:
        interpretation = row["helm_interpretation"]
        text = interpretation["text"]
        rows.append({
            "helm_catalog_id": row["helm_catalog_id"],
            "symbol_id": row["symbol_id"],
            "name": row["name"],
            "s57_object": row["s57_object"],
            "s101_crosswalk_class": row["s101_crosswalk_class"],
            "helm_symbol_recipe_status": row["helm_symbol_recipe_status"],
            "helm_interpretation_status": row["helm_interpretation_status"],
            "helm_interpretation_version": interpretation["version"],
            "validation": interpretation["validation"],
            "reason_codes": interpretation.get("reason_codes") or [],
            "text_length": len(text),
            "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "stored_text_source": "catalog/semantic_evidence_db.json#/rows/helm_interpretation",
            "runtime_gate_summary": row["runtime_gate_summary"],
        })

    status_counts = Counter(row["helm_interpretation_status"] for row in rows)
    validation_counts = Counter(
        row["validation"]["status"]
        for row in rows
    )
    reason_counts: Counter[str] = Counter()
    for row in rows:
        reason_counts.update(row.get("reason_codes") or [])

    return {
        "schema": "helm.forge.helm-interpretation-contract.v1",
        "status": "provisional_helm_interpretation_contract_ready",
        "source": {
            "semantic_evidence_db": "catalog/semantic_evidence_db.json",
            "symbol_recipe_contract": "catalog/helm_symbol_recipe_contract.json",
            "s52_s101_rule_contract": "catalog/s52_s101_rule_contract.json",
        },
        "versions": {
            "interpretation": INTERPRETATION_VERSION,
            "prompt": PROMPT_VERSION,
            "output_schema": OUTPUT_SCHEMA_VERSION,
        },
        "prompt_contract": deepcopy(PROMPT_CONTRACT),
        "output_schema": deepcopy(OUTPUT_SCHEMA),
        "consumer_contract": {
            "backend_db_source_of_truth": True,
            "browser_business_logic_allowed": False,
            "browser_generation_allowed": False,
            "llm_page_load_generation_allowed": False,
            "hidden_fallbacks_allowed": False,
            "runtime_export_allowed": False,
            "runtime_export_gate_owner": "FORGE-31",
        },
        "coverage": {
            "rows": len(rows),
            "status_counts": dict(sorted(status_counts.items())),
            "validation_counts": dict(sorted(validation_counts.items())),
            "reason_counts": dict(sorted(reason_counts.items())),
        },
        "rows": rows,
    }


def _md(result: dict[str, Any]) -> str:
    coverage = result["coverage"]
    return "\n".join([
        "# Helm Interpretation Contract",
        "",
        f"Status: `{result['status']}`",
        "",
        "This FORGE-29 artifact stores the human-readable Helm interpretation",
        "for each semantic evidence row. It is generated from backend evidence",
        "and validated against DB fields; it is not generated in browser code.",
        "",
        f"- rows: `{coverage['rows']}`",
        f"- versions: `{result['versions']}`",
        f"- status_counts: `{coverage['status_counts']}`",
        f"- validation_counts: `{coverage['validation_counts']}`",
        f"- reason_counts: `{coverage['reason_counts']}`",
        "",
        "Consumer rule: proof pages, judge prompts, and repair agents display",
        "`helm_interpretation_v1` from the backend payload. They must not infer",
        "meaning, colors, shape family, S-101 equivalence, or runtime eligibility",
        "from filenames or hidden JavaScript fallbacks.",
        "",
        "Runtime rule: this artifact explains rows only. FORGE-31 remains the",
        "runtime export gate and must require interpretation status, recipe status,",
        "visual proof, provenance, and human approval before export.",
        "",
    ])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args(argv)
    result = build()
    _write(args.out, result)
    args.md.write_text(_md(result))
    print(f"Helm interpretation contract -> {args.out}")
    print(f"Helm interpretation contract summary -> {args.md}")
    print(f"coverage: {result['coverage']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
