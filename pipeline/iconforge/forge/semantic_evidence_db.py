"""Build the Forge semantic evidence DB-view artifact.

This is a source-of-truth payload for proof pages, judge prompts, and future
runtime export gates. It intentionally does not execute S-101 Lua. It joins the
existing standards ledgers into one backend-sourced row contract and keeps all
runtime promotion fail-closed until later FORGE gates approve a row.

Run:
  python3 -m forge.semantic_evidence_db
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from . import helm_interpretation_contract
from . import s52_s101_rule_contract
from . import symbol_recipe_contract


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
PROOF = ROOT / "proof"

SOURCE_TABLE = CATALOG / "standard_source_table.json"
RESOLVER = CATALOG / "standards_s101_resolver.json"
THREE_WAY_PROOF = CATALOG / "standards_three_way_proof.json"
RULE_INPUT = PROOF / "chartplotter-rule-input.json"

DEFAULT_OUT = CATALOG / "semantic_evidence_db.json"
DEFAULT_MD = CATALOG / "semantic_evidence_db.md"

REQUIRED_API_FIELDS = [
    "open_cpn_description",
    "s57_object",
    "s57_attribute_tuple",
    "s57_description",
    "s52_instruction",
    "s52_instruction_ast",
    "s52_instruction_ast_status",
    "s101_rule_file",
    "s101_feature_type",
    "s101_attributes",
    "s101_mapping_type",
    "s101_rule_contract",
    "s101_rule_contract_status",
    "resolver_status",
    "helm_symbol_recipe",
    "helm_symbol_recipe_status",
    "helm_interpretation",
    "helm_interpretation_status",
    "source_refs",
    "unresolved_reasons",
    "runtime_gate_summary",
]


def _read(path: Path) -> Any:
    return json.loads(path.read_text())


def _write(path: Path, body: Any) -> None:
    path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")


def _source_catalog_id(row: dict[str, Any]) -> str:
    s57 = row.get("s57_structure") or {}
    return "_".join([
        str(s57.get("object_class") or "UNKNOWN"),
        str(row.get("asset") or "UNKNOWN"),
        str(s57.get("lookup_id") or "UNKNOWN"),
    ])


def _by_catalog_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row.get("helm_catalog_id")): row for row in rows}


def _source_by_catalog_id(source: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {_source_catalog_id(row): row for row in source["rows"]}


def _rule_by_symbol(rule_input: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row.get("symbol_id") or row.get("s52_symbol_id")): row for row in rule_input["rows"]}


def _first_ref(source_row: dict[str, Any] | None, provider: str) -> dict[str, Any]:
    refs = ((source_row or {}).get("reference_providers") or {}).get(provider) or []
    return refs[0] if refs else {}


def _opencpn_description(source_row: dict[str, Any] | None, tuple_: dict[str, Any]) -> str:
    ref = _first_ref(source_row, "opencpn_render")
    return str(
        ref.get("label")
        or (source_row or {}).get("name")
        or tuple_.get("semantic_brief")
        or tuple_.get("s52_symbol_id")
        or ""
    )


def _s57_object(source_row: dict[str, Any] | None, resolver_row: dict[str, Any]) -> dict[str, Any]:
    s57 = (source_row or {}).get("s57_structure") or {}
    return {
        "object_class": resolver_row.get("object_class") or s57.get("object_class"),
        "lookup_id": s57.get("lookup_id"),
        "lookup_rcid": s57.get("lookup_rcid"),
        "conditions": s57.get("conditions") or [],
    }


def _s57_attribute_tuple(tuple_: dict[str, Any]) -> dict[str, Any]:
    return {
        "object_class": tuple_.get("object_class"),
        "symbol_id": tuple_.get("s52_symbol_id"),
        "category": tuple_.get("category"),
        "geometry": tuple_.get("geometry"),
        "shape": tuple_.get("shape"),
        "colour_sequence": tuple_.get("colour_sequence") or [],
        "colour_pattern": tuple_.get("colour_pattern"),
        "topmark": tuple_.get("topmark"),
        "topmark_daymark_shape": tuple_.get("topmark_daymark_shape"),
        "status_condition": tuple_.get("status_condition") or {},
        "display_mode": tuple_.get("display_mode"),
    }


def _s57_description(symbol_id: str, source_row: dict[str, Any] | None, tuple_: dict[str, Any]) -> tuple[str, str]:
    # FORGE-26 only has derived prose. The gap reason stays visible until a
    # future catalogue-prose import can prove official S-57 object/attribute text.
    brief = str(tuple_.get("semantic_brief") or "").strip()
    if brief:
        return brief, "derived_from_semantic_tuple"

    name = str((source_row or {}).get("name") or symbol_id).strip()
    shape = tuple_.get("shape")
    colours = tuple_.get("colour_sequence") or []
    object_class = tuple_.get("object_class") or "unknown object"
    pieces = [f"{symbol_id} represents {name} for S-57 object {object_class}."]
    if shape:
        pieces.append(f"Required shape family: {shape}.")
    if colours:
        pieces.append(f"Required colour sequence: {', '.join(str(c) for c in colours)}.")
    return " ".join(pieces), "derived_from_row_name"


def _s101_evidence(resolver_row: dict[str, Any]) -> dict[str, Any]:
    evidence = resolver_row.get("portrayal_evidence") or {}
    direct = evidence.get("direct_symbol") or {}
    shape_witness = evidence.get("shape_witness")
    instruction_basis = evidence.get("instruction_basis") or []
    return {
        "feature_type": evidence.get("feature_type"),
        "rule_file": evidence.get("feature_rule_file"),
        "attributes": evidence.get("attributes") or {},
        "complex_attribute": evidence.get("complex_attribute"),
        "direct_symbol_id": direct.get("symbol_id"),
        "direct_symbol_file": direct.get("symbol_file"),
        "shape_witness": shape_witness,
        "instruction_basis": instruction_basis,
        "rule_instruction_refs": evidence.get("rule_instruction_refs") or [],
        "license_status": evidence.get("license_status"),
    }


def _runtime_gate_summary(
    three_way_row: dict[str, Any] | None,
    rule_row: dict[str, Any] | None,
    resolver_row: dict[str, Any],
) -> dict[str, Any]:
    reasons: list[str] = []
    reasons.extend((rule_row or {}).get("status_reasons") or [])
    reasons.extend((resolver_row.get("unresolved_reasons") or []))
    reasons.extend(((three_way_row or {}).get("gate") or {}).get("blockers") or [])

    candidate = (three_way_row or {}).get("helm_candidate") or {}
    qa = candidate.get("qa") or {}
    final_approved = bool(qa.get("final_approved"))
    rule_runtime = bool((rule_row or {}).get("runtime_eligible"))
    runtime_eligible = bool(rule_runtime and final_approved and not reasons)

    classification = resolver_row.get("s101_crosswalk_classification") or {}
    classification_class = classification.get("class")
    resolver_status = str(resolver_row.get("resolver_status") or "")
    if runtime_eligible:
        status = "runtime_ready"
    elif resolver_status == "unresolved" or classification.get("requires_manual_crosswalk"):
        status = "blocked"
    elif classification_class in {"non_s101_runtime_construct", "non_s101_or_inland_extension"}:
        status = "manual_review_required"
    else:
        status = "pending"

    if not rule_runtime and "rule_input_runtime_eligible:false" not in reasons:
        reasons.append("rule_input_runtime_eligible:false")
    if not final_approved and "final_approved:false" not in reasons:
        reasons.append("final_approved:false")

    return {
        "status": status,
        "runtime_eligible": runtime_eligible,
        "rule_input_status": (rule_row or {}).get("status"),
        "review_state": (three_way_row or {}).get("review_state"),
        "resolver_status": resolver_row.get("resolver_status"),
        "final_approved": final_approved,
        "reason_codes": sorted(set(str(reason) for reason in reasons if reason)),
        "promotion_rule": "FORGE-31 may export only rows with complete evidence, approved recipe, stored interpretation, final human approval, and passing visual gates.",
    }


def _source_refs(
    source_row: dict[str, Any] | None,
    resolver_row: dict[str, Any],
    three_way_row: dict[str, Any] | None,
    rule_row: dict[str, Any] | None,
) -> dict[str, Any]:
    refs = dict(resolver_row.get("source_refs") or {})
    refs.update({
        "standard_source_table": "catalog/standard_source_table.json",
        "standards_s101_resolver": "catalog/standards_s101_resolver.json",
        "standards_three_way_proof": "catalog/standards_three_way_proof.json",
        "chartplotter_rule_input": "proof/chartplotter-rule-input.json",
    })
    refs["opencpn_render"] = _first_ref(source_row, "opencpn_render") or None
    refs["s101_reference"] = _first_ref(source_row, "s101") or None
    refs["clean_room_boundary"] = (three_way_row or {}).get("clean_room_boundary") or {}
    refs["rule_input_symbol"] = (rule_row or {}).get("symbol_id")
    return refs


def _gap_reasons(row: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    class_ = row.get("s101_crosswalk_class")
    s101_not_applicable = class_ in {
        "non_s101_runtime_construct",
        "non_s101_or_inland_extension",
    }
    direct_symbol_evidence = (
        row.get("resolver_status") == "resolved_direct"
        or row.get("s101_rule_contract_status") == "direct_symbol_contract_ready"
    )
    if not row["source_refs"].get("opencpn_render"):
        reasons.append("no_opencpn_render_reference")
    if row.get("s57_description_source") != "official_catalogue_prose":
        reasons.append("s57_description_derived_pending_catalogue_prose")
    if not row.get("s52_instruction"):
        reasons.append("missing_s52_instruction")
    s52_status = row.get("s52_instruction_ast_status")
    if s52_status in {"malformed", "unsupported_command", "unsupported_conditional_procedure"}:
        reasons.append(f"s52_instruction_ast_{s52_status}")
    elif s52_status == "missing_instruction":
        reasons.append("s52_instruction_ast_missing_instruction")
    if not row.get("s101_feature_type") and not s101_not_applicable and not direct_symbol_evidence:
        reasons.append("missing_s101_feature_type")
    if not row.get("s101_rule_file") and not s101_not_applicable and not direct_symbol_evidence:
        reasons.append("missing_s101_rule_file")
    s101_contract_status = row.get("s101_rule_contract_status")
    if s101_contract_status in {
        "malformed_attribute_tuple",
        "missing_s101_feature_type",
        "missing_s101_rule_file",
        "direct_asset_reference_incomplete",
        "manual_rule_contract_required",
    }:
        reasons.append(f"s101_rule_contract_{s101_contract_status}")

    if class_ == "s101_component_context_required":
        reasons.append("s101_component_context_required")
    elif class_ == "non_s101_runtime_construct":
        reasons.append("non_s101_runtime_construct")
    elif class_ == "non_s101_or_inland_extension":
        reasons.append("non_s101_or_inland_extension")

    if row.get("unresolved_reasons"):
        reasons.append("resolver_has_visible_unresolved_reasons")
    if row.get("helm_symbol_recipe_status") != "recipe_ready":
        reasons.append("helm_symbol_recipe_not_ready")
    if row.get("helm_interpretation_status") != helm_interpretation_contract.READY:
        reasons.append("helm_interpretation_not_ready")
    if not row["runtime_gate_summary"]["runtime_eligible"]:
        reasons.append("runtime_not_eligible")
    return sorted(set(reasons))


def _row(
    resolver_row: dict[str, Any],
    source_row: dict[str, Any] | None,
    three_way_row: dict[str, Any] | None,
    rule_row: dict[str, Any] | None,
) -> dict[str, Any]:
    symbol_id = str(resolver_row.get("s52_symbol_id") or "")
    tuple_ = resolver_row.get("semantic_tuple") or {}
    s57 = (source_row or {}).get("s57_structure") or {}
    description, description_source = _s57_description(symbol_id, source_row, tuple_)
    s101 = _s101_evidence(resolver_row)
    crosswalk = resolver_row.get("s101_crosswalk_classification") or {}
    runtime_gate = _runtime_gate_summary(three_way_row, rule_row, resolver_row)

    row = {
        "canonical_row_key": resolver_row.get("helm_catalog_id"),
        "helm_catalog_id": resolver_row.get("helm_catalog_id"),
        "source_table_id": resolver_row.get("source_table_id"),
        "symbol_id": symbol_id,
        "asset": symbol_id,
        "name": (source_row or three_way_row or {}).get("name") or symbol_id,
        "kind": (source_row or three_way_row or {}).get("kind"),
        "family": (source_row or three_way_row or {}).get("family"),
        "open_cpn_description": _opencpn_description(source_row, tuple_),
        "s57_object": _s57_object(source_row, resolver_row),
        "s57_attribute_tuple": _s57_attribute_tuple(tuple_),
        "s57_description": description,
        "s57_description_source": description_source,
        "s52_instruction": s57.get("s52_instruction"),
        "s101_rule_file": s101["rule_file"],
        "s101_feature_type": s101["feature_type"],
        "s101_attributes": s101["attributes"],
        "s101_complex_attribute": s101["complex_attribute"],
        "s101_mapping_type": resolver_row.get("s101_mapping_type"),
        "s101_crosswalk_class": crosswalk.get("class"),
        "s101_crosswalk": crosswalk,
        "resolver_status": resolver_row.get("resolver_status"),
        "source_refs": _source_refs(source_row, resolver_row, three_way_row, rule_row),
        "unresolved_reasons": resolver_row.get("unresolved_reasons") or [],
        "runtime_gate_summary": runtime_gate,
        "proof_page_payload": {
            "open_cpn_description": _opencpn_description(source_row, tuple_),
            "open_cpn_reference": _first_ref(source_row, "opencpn_render") or None,
            "s57_description": description,
            "s57_attribute_tuple": _s57_attribute_tuple(tuple_),
            "s52_instruction": s57.get("s52_instruction"),
            "s101_rule_evidence": s101,
            "helm_candidate": (three_way_row or {}).get("helm_candidate") or {},
            "qa_state": runtime_gate,
        },
        "consumer_contract": {
            "browser_business_logic_allowed": False,
            "backend_db_source_of_truth": True,
            "runtime_export_allowed": runtime_gate["runtime_eligible"],
        },
    }
    rule_contract = s52_s101_rule_contract.contract_for_row(row)
    row.update(rule_contract)
    recipe = symbol_recipe_contract.recipe_for_row(row)
    row["helm_symbol_recipe"] = recipe
    row["helm_symbol_recipe_status"] = recipe["status"]
    row["runtime_gate_summary"]["s52_instruction_ast_status"] = row["s52_instruction_ast_status"]
    row["runtime_gate_summary"]["s101_rule_contract_status"] = row["s101_rule_contract_status"]
    row["runtime_gate_summary"]["s101_rule_contract_runtime_ready"] = row["s101_rule_contract"]["contract_runtime_ready"]
    row["runtime_gate_summary"]["helm_symbol_recipe_status"] = row["helm_symbol_recipe_status"]
    row["runtime_gate_summary"]["helm_symbol_recipe_ready"] = row["helm_symbol_recipe_status"] == "recipe_ready"
    row["consumer_contract"]["rule_contract_source"] = "FORGE-27:s52_s101_rule_contract"
    row["consumer_contract"]["symbol_recipe_source"] = "FORGE-28:helm_symbol_recipe_v1"
    row["consumer_contract"]["browser_symbol_recipe_logic_allowed"] = False
    row["proof_page_payload"]["helm_symbol_recipe"] = recipe
    interpretation = helm_interpretation_contract.interpretation_for_row(row)
    row["helm_interpretation"] = interpretation
    row["helm_interpretation_status"] = interpretation["status"]
    row["helm_interpretation_source"] = "FORGE-29:helm_interpretation_v1"
    row["runtime_gate_summary"]["helm_interpretation_status"] = row["helm_interpretation_status"]
    row["runtime_gate_summary"]["helm_interpretation_ready"] = (
        row["helm_interpretation_status"] == helm_interpretation_contract.READY
    )
    row["consumer_contract"]["helm_interpretation_source"] = "FORGE-29:helm_interpretation_v1"
    row["consumer_contract"]["browser_interpretation_generation_allowed"] = False
    row["proof_page_payload"]["helm_interpretation"] = interpretation
    row["evidence_gap_reasons"] = _gap_reasons(row)
    return row


def _coverage(rows: list[dict[str, Any]], sources: dict[str, Any]) -> dict[str, Any]:
    returned_counts = {field: sum(1 for row in rows if field in row) for field in REQUIRED_API_FIELDS}
    populated_counts = {
        field: sum(1 for row in rows if row.get(field) not in (None, "", [], {}))
        for field in REQUIRED_API_FIELDS
    }
    gap_counts: dict[str, int] = defaultdict(int)
    for row in rows:
        for reason in row["evidence_gap_reasons"]:
            gap_counts[reason] += 1

    runtime_counts = Counter(row["runtime_gate_summary"]["status"] for row in rows)
    runtime_eligible = sum(1 for row in rows if row["runtime_gate_summary"]["runtime_eligible"])
    resolver_counts = Counter(row["resolver_status"] for row in rows)
    mapping_counts = Counter(row["s101_mapping_type"] for row in rows)
    class_counts = Counter(row["s101_crosswalk_class"] or "unknown" for row in rows)
    s52_ast_counts = Counter(row["s52_instruction_ast_status"] for row in rows)
    s101_contract_counts = Counter(row["s101_rule_contract_status"] for row in rows)
    recipe_counts = Counter(row["helm_symbol_recipe_status"] for row in rows)
    interpretation_counts = Counter(row["helm_interpretation_status"] for row in rows)
    interpretation_validation_counts = Counter(
        row["helm_interpretation"]["validation"]["status"]
        for row in rows
    )

    return {
        "rows": len(rows),
        "source_rows": {
            "standard_source_table": len(sources["source"]["rows"]),
            "standards_s101_resolver": len(sources["resolver"]["rows"]),
            "standards_three_way_proof": len(sources["three_way"]["rows"]),
            "chartplotter_rule_input": len(sources["rule_input"]["rows"]),
        },
        "required_api_fields": REQUIRED_API_FIELDS,
        "required_api_fields_note": (
            "Returned means the key is present in the API payload. Consumers must "
            "also check required_api_fields_populated and gap_counts_by_reason; "
            "empty S-101 fields are deliberate fail-closed gaps, not approvals."
        ),
        "required_api_fields_returned": returned_counts,
        "required_api_fields_populated": populated_counts,
        "all_required_api_fields_returned": all(count == len(rows) for count in returned_counts.values()),
        "gap_counts_by_reason": dict(sorted(gap_counts.items())),
        "runtime_gate_counts": {
            "runtime_eligible": runtime_eligible,
            "runtime_blocked_or_pending": len(rows) - runtime_eligible,
            "status_counts": dict(sorted(runtime_counts.items())),
        },
        "resolver_status_counts": dict(sorted(resolver_counts.items())),
        "s101_mapping_type_counts": dict(sorted(mapping_counts.items())),
        "s101_crosswalk_class_counts": dict(sorted(class_counts.items())),
        "s52_instruction_ast_status_counts": dict(sorted(s52_ast_counts.items())),
        "s101_rule_contract_status_counts": dict(sorted(s101_contract_counts.items())),
        "helm_symbol_recipe_status_counts": dict(sorted(recipe_counts.items())),
        "helm_interpretation_status_counts": dict(sorted(interpretation_counts.items())),
        "helm_interpretation_validation_counts": dict(sorted(interpretation_validation_counts.items())),
    }


def build() -> dict[str, Any]:
    source = _read(SOURCE_TABLE)
    resolver = _read(RESOLVER)
    three_way = _read(THREE_WAY_PROOF)
    rule_input = _read(RULE_INPUT)

    source_rows = _source_by_catalog_id(source)
    three_way_rows = _by_catalog_id(three_way["rows"])
    rule_rows = _rule_by_symbol(rule_input)

    rows = []
    for resolver_row in resolver["rows"]:
        catalog_id = str(resolver_row.get("helm_catalog_id"))
        symbol_id = str(resolver_row.get("s52_symbol_id") or "")
        rows.append(_row(
            resolver_row=resolver_row,
            source_row=source_rows.get(catalog_id),
            three_way_row=three_way_rows.get(catalog_id),
            rule_row=rule_rows.get(symbol_id),
        ))

    sources = {
        "source": source,
        "resolver": resolver,
        "three_way": three_way,
        "rule_input": rule_input,
    }
    return {
        "schema": "helm.forge.semantic-evidence-db.v1",
        "status": "provisional_semantic_evidence_db_ready",
        "strict_runtime_position": (
            "Helm uses S-101 Lua/catalogue evidence to derive and audit symbol "
            "mappings, but does not yet claim full runtime-grade S-101 Lua rule "
            "execution. Runtime promotion remains fail-closed until S-52/S-101 "
            "instruction interpretation, recipes, stored Helm interpretation, "
            "visual proof, and human approval all pass."
        ),
        "source": {
            "standard_source_table": "catalog/standard_source_table.json",
            "standards_s101_resolver": "catalog/standards_s101_resolver.json",
            "standards_three_way_proof": "catalog/standards_three_way_proof.json",
            "chartplotter_rule_input": "proof/chartplotter-rule-input.json",
        },
        "consumer_contract": {
            "proof_review_server": "must read this backend DB/API payload; static HTML may only cache it with a source hash",
            "judge_prompts": "must read per-row evidence from this payload, not filenames",
            "future_runtime_renderer": "must wait for FORGE-31 export gates; this artifact is not runtime approval",
            "rule_contract": "FORGE-27 adds parsed S-52 AST and S-101 rule-contract status; Lua execution remains out of scope",
            "symbol_recipe_contract": "FORGE-28 adds backend-resolved shape/color/pattern/style/palette recipes; browser logic remains display-only",
            "helm_interpretation_contract": "FORGE-29 adds stored backend-generated human-readable interpretations; page-load LLM/browser generation is forbidden",
            "browser_business_logic_allowed": False,
            "hidden_fallbacks_allowed": False,
        },
        "known_external_review_gates": {
            "s101_mapping_audit": {
                "status": "accepted_in_FORGE_23_FORGE_24",
                "owner_tasks": ["FORGE-23", "FORGE-24"],
                "reason": (
                    "The S-101 resolver/proof alignment tasks are accepted as evidence-layer "
                    "work. The current audit accounts for all 824 rows, keeps raw S-101 SVGs "
                    "labelled as shape witnesses, and records runtime/extension rows as "
                    "explicit non-S-101 states. Runtime export still waits for later gates."
                ),
                "observed_rows": [],
            },
            "stacked_pr": {
                "status": "accepted_and_merged",
                "reason": (
                    "FORGE-23, FORGE-24, and FORGE-26 were accepted on the Vulkan board "
                    "with verifier-stamped evidence. Helm PR #243 merged into "
                    "codex/FORGE-12-chart1-parity at "
                    "d86fb3ae90e0900597b63bd431618efff19dbd55."
                ),
                "pr_url": "https://github.com/StevenRidder/Helm/pull/243",
                "merged_target_sha": "d86fb3ae90e0900597b63bd431618efff19dbd55",
            },
        },
        "coverage": _coverage(rows, sources),
        "rows": rows,
    }


def _md(result: dict[str, Any]) -> str:
    coverage = result["coverage"]
    return "\n".join([
        "# Semantic Evidence DB View",
        "",
        f"Status: `{result['status']}`",
        "",
        result["strict_runtime_position"],
        "",
        "This semantic evidence DB artifact is the backend row contract for proof pages,",
        "judge prompts, and later runtime export gates. It is not a Lua",
        "interpreter and it does not approve any symbol for runtime use. Later",
        "FORGE gates add parsed rule contracts, symbol recipes, and stored",
        "Helm interpretations into this same row payload.",
        "",
        f"- rows: `{coverage['rows']}`",
        f"- all_required_api_fields_returned: `{coverage['all_required_api_fields_returned']}`",
        f"- required_api_fields_note: `{coverage['required_api_fields_note']}`",
        f"- required_api_fields_populated: `{coverage['required_api_fields_populated']}`",
        f"- runtime_gate_counts: `{coverage['runtime_gate_counts']}`",
        f"- resolver_status_counts: `{coverage['resolver_status_counts']}`",
        f"- s101_crosswalk_class_counts: `{coverage['s101_crosswalk_class_counts']}`",
        f"- s52_instruction_ast_status_counts: `{coverage['s52_instruction_ast_status_counts']}`",
        f"- s101_rule_contract_status_counts: `{coverage['s101_rule_contract_status_counts']}`",
        f"- helm_symbol_recipe_status_counts: `{coverage['helm_symbol_recipe_status_counts']}`",
        f"- helm_interpretation_status_counts: `{coverage['helm_interpretation_status_counts']}`",
        f"- helm_interpretation_validation_counts: `{coverage['helm_interpretation_validation_counts']}`",
        "",
        "Gap counts:",
        "",
        *[
            f"- `{reason}`: `{count}`"
            for reason, count in coverage["gap_counts_by_reason"].items()
        ],
        "",
        "Consumer rule: browser and static proof pages display this payload only.",
        "They must not derive symbol meaning, colors, mappings, or runtime gates",
        "from filenames or hidden JavaScript fallbacks.",
        "",
        "Adjacent gates:",
        "",
        "- `s101_mapping_audit`: accepted in `FORGE-23`/`FORGE-24`; the current",
        "  audit accounts for all 824 rows and keeps raw S-101 SVGs labelled as",
        "  shape witnesses rather than color-resolved portrayal.",
        "- `stacked_pr`: accepted and merged via Helm PR #243 into",
        "  `codex/FORGE-12-chart1-parity` at",
        "  `d86fb3ae90e0900597b63bd431618efff19dbd55`.",
        "",
    ])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    result = build()
    _write(args.out, result)
    args.md.write_text(_md(result))
    print(f"wrote {args.out}")
    print(f"wrote {args.md}")


if __name__ == "__main__":
    main()
