"""Build the FORGE-27 S-52/S-101 rule-contract artifact.

This is a deterministic contract layer for proof/review tooling. It parses the
S-52 instruction string already present in the semantic evidence DB and
normalizes the S-101 evidence into explicit status fields. It intentionally does
not execute S-101 Lua and it does not approve runtime export.

Run:
  python3 -m forge.s52_s101_rule_contract
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"

DEFAULT_OUT = CATALOG / "s52_s101_rule_contract.json"
DEFAULT_MD = CATALOG / "s52_s101_rule_contract.md"

SUPPORTED_S52_COMMANDS = {
    "AC": "area_colour",
    "AP": "area_pattern",
    "CS": "conditional_procedure",
    "LC": "line_complex",
    "LS": "line_style",
    "SY": "symbol",
    "TE": "text_expression",
    "TX": "text_attribute",
}

# These are the conditional procedure references observed in the current
# 824-row evidence DB. The contract parses and names them, but it does not
# execute the procedures or their S-101 Lua equivalents.
KNOWN_CONDITIONAL_PROCEDURES = {
    "CLRLIN01",
    "DATCVR01",
    "DEPARE01",
    "DEPARE02",
    "DEPCNT02",
    "LEGLIN02",
    "LIGHTS05",
    "OBSTRN04",
    "OWNSHP02",
    "PASTRK01",
    "QUAPOS01",
    "RESARE01",
    "RESARE02",
    "RESTRN01",
    "SLCONS03",
    "SOUNDG02",
    "SYMINS01",
    "TOPMAR01",
    "TOPMARI1",
    "VESSEL01",
    "VRMEBL01",
    "WRECKS02",
}

RULE_REQUIRED_STATUSES = {
    "resolved_rule",
    "resolved_rule_catalogue",
    "resolved_with_deviation",
}


class S52ParseError(ValueError):
    """Raised when an S-52 instruction cannot be tokenized safely."""


def _write(path: Path, body: Any) -> None:
    path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")


def _split_top_level(text: str, delimiter: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    quote = False
    start = 0
    for idx, char in enumerate(text):
        if quote:
            if char == "'":
                quote = False
            continue
        if char == "'":
            quote = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth < 0:
                raise S52ParseError(f"unbalanced ')' near byte {idx}")
        elif char == delimiter and depth == 0:
            parts.append(text[start:idx].strip())
            start = idx + 1
    if quote:
        raise S52ParseError("unterminated quoted argument")
    if depth != 0:
        raise S52ParseError("unbalanced parentheses")
    tail = text[start:].strip()
    if tail:
        parts.append(tail)
    return [part for part in parts if part]


def _parse_args(args: str) -> list[str]:
    return _split_top_level(args, ",") if args.strip() else []


def _command_semantics(command: str, args: list[str]) -> dict[str, Any]:
    if command == "SY":
        return {
            "symbol_id": args[0] if args else None,
            "rotation_attribute": args[1] if len(args) > 1 else None,
        }
    if command == "LS":
        return {
            "pattern": args[0] if args else None,
            "width": args[1] if len(args) > 1 else None,
            "colour_token": args[2] if len(args) > 2 else None,
        }
    if command == "LC":
        return {"line_complex_id": args[0] if args else None}
    if command == "AP":
        return {"area_pattern_id": args[0] if args else None}
    if command == "AC":
        return {"area_colour_token": args[0] if args else None}
    if command == "TE":
        return {
            "text_source": args[1] if len(args) > 1 else None,
            "format": args[0] if args else None,
            "colour_token": args[8] if len(args) > 8 else None,
            "display_priority": args[9] if len(args) > 9 else None,
        }
    if command == "TX":
        return {
            "text_source": args[0] if args else None,
            "format": None,
            "colour_token": args[7] if len(args) > 7 else None,
            "display_priority": args[8] if len(args) > 8 else None,
        }
    return {}


def _parse_call(raw: str, index: int) -> dict[str, Any]:
    match = re.match(r"^([A-Z]{2})\((.*)\)$", raw)
    if not match:
        raise S52ParseError(f"malformed command token: {raw}")

    command = match.group(1)
    inner = match.group(2)
    args = _parse_args(inner)
    node = {
        "index": index,
        "command": command,
        "role": SUPPORTED_S52_COMMANDS.get(command, "unsupported"),
        "raw": raw,
        "args": args,
        "arg_count": len(args),
        "semantic": _command_semantics(command, args),
    }

    if command == "CS":
        pieces = _split_top_level(inner, ";")
        procedure = pieces[0].strip() if pieces else None
        nested = []
        for nested_index, nested_raw in enumerate(pieces[1:]):
            nested.append(_parse_call(nested_raw, nested_index))
        node["semantic"] = {
            "procedure": procedure,
            "known_reference": procedure in KNOWN_CONDITIONAL_PROCEDURES,
            "nested_commands": nested,
            "executes_condition": False,
        }

    return node


def parse_s52_instruction(instruction: str | None) -> dict[str, Any]:
    if not instruction:
        return {
            "status": "missing_instruction",
            "commands": [],
            "command_counts": {},
            "symbols": [],
            "line_styles": [],
            "line_complexes": [],
            "area_patterns": [],
            "area_colours": [],
            "text_commands": [],
            "conditional_procedures": [],
            "unsupported_commands": [],
            "parse_errors": ["missing_s52_instruction"],
        }

    try:
        raw_commands = _split_top_level(instruction, ";")
        commands = [_parse_call(raw, idx) for idx, raw in enumerate(raw_commands)]
    except S52ParseError as exc:
        return {
            "status": "malformed",
            "commands": [],
            "command_counts": {},
            "symbols": [],
            "line_styles": [],
            "line_complexes": [],
            "area_patterns": [],
            "area_colours": [],
            "text_commands": [],
            "conditional_procedures": [],
            "unsupported_commands": [],
            "parse_errors": [str(exc)],
        }

    unsupported = sorted({node["command"] for node in commands if node["command"] not in SUPPORTED_S52_COMMANDS})
    conditional_nodes = [node for node in commands if node["command"] == "CS"]
    conditional_procedures = [
        str(node["semantic"].get("procedure"))
        for node in conditional_nodes
        if node["semantic"].get("procedure")
    ]
    unknown_conditionals = sorted({
        procedure for procedure in conditional_procedures
        if procedure not in KNOWN_CONDITIONAL_PROCEDURES
    })
    command_counts = Counter(node["command"] for node in commands)

    if unsupported:
        status = "unsupported_command"
    elif unknown_conditionals:
        status = "unsupported_conditional_procedure"
    elif conditional_procedures:
        status = "parsed_with_conditional_references"
    else:
        status = "parsed"

    return {
        "status": status,
        "commands": commands,
        "command_counts": dict(sorted(command_counts.items())),
        "symbols": [
            node["semantic"]["symbol_id"]
            for node in commands
            if node["command"] == "SY" and node["semantic"].get("symbol_id")
        ],
        "line_styles": [
            node["semantic"]
            for node in commands
            if node["command"] == "LS"
        ],
        "line_complexes": [
            node["semantic"]["line_complex_id"]
            for node in commands
            if node["command"] == "LC" and node["semantic"].get("line_complex_id")
        ],
        "area_patterns": [
            node["semantic"]["area_pattern_id"]
            for node in commands
            if node["command"] == "AP" and node["semantic"].get("area_pattern_id")
        ],
        "area_colours": [
            node["semantic"]["area_colour_token"]
            for node in commands
            if node["command"] == "AC" and node["semantic"].get("area_colour_token")
        ],
        "text_commands": [
            node["semantic"]
            for node in commands
            if node["command"] in {"TE", "TX"}
        ],
        "conditional_procedures": conditional_procedures,
        "unsupported_commands": unsupported,
        "unsupported_conditional_procedures": unknown_conditionals,
        "parse_errors": [],
    }


def _attribute_validation(row: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    s57_tuple = row.get("s57_attribute_tuple") or {}
    s101_attrs = row.get("s101_attributes") or {}

    if not isinstance(s57_tuple, dict):
        errors.append("s57_attribute_tuple_not_object")
        s57_tuple = {}
    if not isinstance(s101_attrs, dict):
        errors.append("s101_attributes_not_object")
        s101_attrs = {}

    for field in ("colour_sequence",):
        value = s57_tuple.get(field)
        if value is not None and not isinstance(value, list):
            errors.append(f"s57_{field}_not_list")

    value = s101_attrs.get("colour")
    if value is not None and not isinstance(value, list):
        errors.append("s101_colour_not_list")
    elif isinstance(value, list) and not all(isinstance(item, str) and item for item in value):
        errors.append("s101_colour_list_contains_non_string")

    for field in ("colourPattern", "buoyShape", "beaconShape", "topmarkDaymarkShape"):
        value = s101_attrs.get(field)
        if value is not None and not isinstance(value, str):
            errors.append(f"s101_{field}_not_string")

    semantic_colours = s57_tuple.get("colour_sequence") or []
    s101_colours = s101_attrs.get("colour") or []
    if semantic_colours and s101_colours and semantic_colours != s101_colours:
        warnings.append("s101_colour_differs_from_s57_tuple")

    return {
        "status": "malformed" if errors else "valid",
        "errors": sorted(errors),
        "warnings": sorted(warnings),
    }


def _filename_gap_interpretation(row: dict[str, Any]) -> dict[str, Any]:
    mapping_type = row.get("s101_mapping_type")
    direct_symbol = ((row.get("proof_page_payload") or {}).get("s101_rule_evidence") or {}).get("direct_symbol_id")
    direct_missing = not bool(direct_symbol)
    if mapping_type in {"rule_derived_equivalent", "acceptable_deviation"} and direct_missing:
        interpretation = "expected_rule_derived_gap"
        is_error = False
    elif row.get("resolver_status") == "resolved_rule_catalogue" and direct_missing:
        interpretation = "catalogue_rule_reference_gap"
        is_error = False
    elif mapping_type == "direct_asset_match" and direct_missing:
        interpretation = "direct_asset_reference_missing_symbol_id"
        is_error = True
    elif direct_missing:
        interpretation = "no_direct_symbol_reference"
        is_error = False
    else:
        interpretation = "direct_symbol_reference_present"
        is_error = False
    return {
        "direct_symbol_missing": direct_missing,
        "interpretation": interpretation,
        "is_error": is_error,
    }


def s101_rule_contract_for_row(row: dict[str, Any]) -> dict[str, Any]:
    attr_validation = _attribute_validation(row)
    resolver_status = str(row.get("resolver_status") or "")
    mapping_type = str(row.get("s101_mapping_type") or "")
    crosswalk_class = str(row.get("s101_crosswalk_class") or "")
    feature_type = row.get("s101_feature_type")
    rule_file = row.get("s101_rule_file")
    filename_gap = _filename_gap_interpretation(row)
    reason_codes: list[str] = []

    if attr_validation["status"] != "valid":
        status = "malformed_attribute_tuple"
        reason_codes.extend(attr_validation["errors"])
    elif crosswalk_class == "non_s101_runtime_construct":
        status = "non_s101_runtime_construct"
        reason_codes.append("not_an_s101_enc_feature")
    elif crosswalk_class == "non_s101_or_inland_extension":
        status = "non_s101_or_extension_profile_required"
        reason_codes.append("requires_profile_or_manual_mapping")
    elif resolver_status in RULE_REQUIRED_STATUSES:
        if not feature_type:
            status = "missing_s101_feature_type"
            reason_codes.append("missing_s101_feature_type")
        elif not rule_file:
            status = "missing_s101_rule_file"
            reason_codes.append("missing_s101_rule_file")
        elif resolver_status == "resolved_with_deviation":
            status = "documented_deviation_review"
            reason_codes.append("acceptable_s52_s101_portrayal_difference")
        elif resolver_status == "resolved_rule_catalogue":
            status = "catalogue_rule_reference_ready"
        else:
            status = "rule_contract_ready"
    elif mapping_type == "direct_asset_match":
        if filename_gap["is_error"]:
            status = "direct_asset_reference_incomplete"
            reason_codes.append("direct_s101_symbol_missing")
        else:
            status = "direct_symbol_contract_ready"
    elif crosswalk_class == "s101_feature_equivalent":
        if feature_type and rule_file:
            status = "catalogue_rule_reference_ready"
        else:
            status = "manual_rule_contract_required"
            reason_codes.append("feature_equivalent_without_rule_contract")
    else:
        status = "manual_rule_contract_required"
        reason_codes.append("manual_rule_contract_required")

    return {
        "status": status,
        "feature_type": feature_type,
        "rule_file": rule_file,
        "mapping_type": mapping_type,
        "resolver_status": resolver_status,
        "crosswalk_class": crosswalk_class,
        "attributes": row.get("s101_attributes") or {},
        "attribute_validation": attr_validation,
        "filename_gap": filename_gap,
        "reason_codes": sorted(set(reason_codes)),
        "lua_execution": {
            "implemented": False,
            "position": (
                "S-101 Lua/rule files are recorded as evidence. Helm does not "
                "claim runtime-grade Lua execution in FORGE-27."
            ),
        },
        "contract_runtime_ready": False,
        "runtime_gate": "fail_closed_until_FORGE_31_export_gate",
    }


def contract_for_row(row: dict[str, Any]) -> dict[str, Any]:
    ast = parse_s52_instruction(row.get("s52_instruction"))
    s101 = s101_rule_contract_for_row(row)
    return {
        "s52_instruction_ast": ast,
        "s52_instruction_ast_status": ast["status"],
        "s101_rule_contract": s101,
        "s101_rule_contract_status": s101["status"],
    }


def build() -> dict[str, Any]:
    from . import semantic_evidence_db

    semantic = semantic_evidence_db.build()
    rows = []
    for row in semantic["rows"]:
        rows.append({
            "helm_catalog_id": row["helm_catalog_id"],
            "symbol_id": row["symbol_id"],
            "name": row["name"],
            "s52_instruction": row.get("s52_instruction"),
            "s52_instruction_ast_status": row["s52_instruction_ast_status"],
            "s52_instruction_ast": row["s52_instruction_ast"],
            "s101_rule_contract_status": row["s101_rule_contract_status"],
            "s101_rule_contract": row["s101_rule_contract"],
            "runtime_gate_summary": row["runtime_gate_summary"],
        })

    s52_counts = Counter(row["s52_instruction_ast_status"] for row in rows)
    s101_counts = Counter(row["s101_rule_contract_status"] for row in rows)
    command_counts: Counter[str] = Counter()
    conditional_counts: Counter[str] = Counter()
    for row in rows:
        command_counts.update(row["s52_instruction_ast"].get("command_counts") or {})
        conditional_counts.update(row["s52_instruction_ast"].get("conditional_procedures") or [])

    runtime_ready = sum(
        1 for row in rows
        if row["s101_rule_contract"]["contract_runtime_ready"]
    )
    return {
        "schema": "helm.forge.s52-s101-rule-contract.v1",
        "status": "provisional_rule_contract_ready",
        "source": {
            "semantic_evidence_db": "catalog/semantic_evidence_db.json",
        },
        "strict_runtime_position": semantic["strict_runtime_position"],
        "coverage": {
            "rows": len(rows),
            "s52_instruction_ast_status_counts": dict(sorted(s52_counts.items())),
            "s101_rule_contract_status_counts": dict(sorted(s101_counts.items())),
            "s52_command_counts": dict(sorted(command_counts.items())),
            "conditional_procedure_counts": dict(sorted(conditional_counts.items())),
            "runtime_contract_ready": runtime_ready,
            "runtime_contract_blocked_or_pending": len(rows) - runtime_ready,
        },
        "consumer_contract": {
            "browser_business_logic_allowed": False,
            "hidden_fallbacks_allowed": False,
            "runtime_export_allowed": False,
            "runtime_export_gate_owner": "FORGE-31",
        },
        "rows": rows,
    }


def _md(result: dict[str, Any]) -> str:
    coverage = result["coverage"]
    return "\n".join([
        "# S-52 / S-101 Rule Contract",
        "",
        f"Status: `{result['status']}`",
        "",
        result["strict_runtime_position"],
        "",
        "This FORGE-27 artifact parses S-52 instructions into a normalized AST",
        "and records an S-101 rule-contract status for every semantic evidence",
        "row. It does not execute S-101 Lua and it does not approve runtime",
        "export.",
        "",
        f"- rows: `{coverage['rows']}`",
        f"- s52_instruction_ast_status_counts: `{coverage['s52_instruction_ast_status_counts']}`",
        f"- s101_rule_contract_status_counts: `{coverage['s101_rule_contract_status_counts']}`",
        f"- s52_command_counts: `{coverage['s52_command_counts']}`",
        f"- conditional_procedure_counts: `{coverage['conditional_procedure_counts']}`",
        f"- runtime_contract_ready: `{coverage['runtime_contract_ready']}`",
        f"- runtime_contract_blocked_or_pending: `{coverage['runtime_contract_blocked_or_pending']}`",
        "",
        "What Helm follows now:",
        "",
        "- S-52 `SY`, `LS`, `LC`, `AP`, `AC`, `TE`, `TX`, and `CS` tokens are parsed",
        "  into a backend-owned AST.",
        "- S-101 evidence is normalized as direct symbol, rule-derived, catalogue-rule,",
        "  documented-deviation, runtime-construct, or extension/profile contract state.",
        "- Missing S-101 filenames are not treated as missing mapping when the resolver",
        "  has rule-derived or catalogue-rule evidence.",
        "",
        "What remains provisional:",
        "",
        "- S-101 Lua is not executed as runtime portrayal logic in this artifact.",
        "- Conditional procedures are named and gated, not rendered by hidden fallback.",
        "- Runtime export stays blocked until FORGE-31 sees complete rule, recipe,",
        "  visual, provenance, and human-approval gates.",
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
    print(f"S-52/S-101 rule contract -> {args.out}")
    print(f"S-52/S-101 rule contract summary -> {args.md}")
    print(f"coverage: {result['coverage']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
