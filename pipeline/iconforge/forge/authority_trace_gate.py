"""Build the FORGE-34 authority trace gate.

The authority trace joins the S-57/S-52 lookup row, decoded attribute
dictionaries, S-52 instruction AST, S-101 rule evidence, Helm recipe/
interpretation, colour authority, and runtime gate into one backend-owned
contract. It does not approve symbols for runtime export.

Run:
  python3 -m forge.authority_trace_gate
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from . import standard_source_table


ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = ROOT.parent.parent
CATALOG = ROOT / "catalog"
DB_PATH = REPO_ROOT / "artifacts" / "opencpn_s52_portrayal.sqlite"

STANDARD_SOURCE_TABLE = CATALOG / "standard_source_table.json"
STANDARD_SOURCE_BUILDER = ROOT / "forge" / "standard_source_table.py"
SEMANTIC_DB = CATALOG / "semantic_evidence_db.json"
RULE_CONTRACT = CATALOG / "s52_s101_rule_contract.json"
RECIPE_CONTRACT = CATALOG / "helm_symbol_recipe_contract.json"
COLOUR_AUTHORITY = CATALOG / "colour_authority_contract.json"

REPORT_JSON = CATALOG / "authority_trace_gate.json"
REPORT_MD = CATALOG / "authority_trace_gate.md"

SCHEMA = "helm.iconforge.authority_trace_gate.v1"

S101_LOCAL_ROOTS = [
    Path("/private/tmp/s101-portrayal-catalogue-audit"),
    Path("/private/tmp/s101-audit"),
    ROOT / "reference_sources" / "s101-portrayal-catalogue",
    ROOT / "reference_sources" / "S-101_Portrayal-Catalogue",
]

CHARTSYMBOLS_CANDIDATES = [
    Path("/private/tmp/helm-forge14/pipeline/iconforge/reference_sources/opencpn-open-source/data/s57data/chartsymbols.xml"),
    Path("/Users/steveridder/.helm/runtime/s57data/chartsymbols.xml"),
    ROOT / "reference_sources" / "opencpn-open-source" / "data" / "s57data" / "chartsymbols.xml",
]

S101_REQUIRED_CLASSES = {
    "s101_feature_equivalent",
    "s101_component_context_required",
}

NON_S101_CLASSES = {
    "non_s101_runtime_construct",
    "non_s101_or_inland_extension",
}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def _json_value(value: str | None, default: Any) -> Any:
    if value is None or value == "":
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _sha256(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n")


def _connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _indexes() -> dict[str, Any]:
    semantic_payload = _read_json(SEMANTIC_DB)
    semantic_rows = semantic_payload.get("rows") or []
    semantic_by_key = {
        str(row.get("canonical_row_key")): row
        for row in semantic_rows
        if row.get("canonical_row_key")
    }
    semantic_by_catalog = {
        str(row.get("helm_catalog_id")): row
        for row in semantic_rows
        if row.get("helm_catalog_id")
    }
    semantic_by_symbol: dict[str, dict[str, Any]] = {}
    for row in semantic_rows:
        symbol_id = row.get("symbol_id")
        if symbol_id and str(symbol_id) not in semantic_by_symbol:
            semantic_by_symbol[str(symbol_id)] = row

    recipe_payload = _read_json(RECIPE_CONTRACT)
    recipe_by_symbol = {
        str(row.get("symbol_id")): row
        for row in recipe_payload.get("rows") or []
        if row.get("symbol_id")
    }
    colour_payload = _read_json(COLOUR_AUTHORITY)
    colour_by_asset = {
        str(row.get("asset")): row
        for row in colour_payload.get("rows") or []
        if row.get("asset")
    }
    return {
        "semantic_by_key": semantic_by_key,
        "semantic_by_catalog": semantic_by_catalog,
        "semantic_by_symbol": semantic_by_symbol,
        "recipe_by_symbol": recipe_by_symbol,
        "colour_by_asset": colour_by_asset,
        "semantic_payload": semantic_payload,
        "recipe_payload": recipe_payload,
        "colour_payload": colour_payload,
        "rule_payload": _read_json(RULE_CONTRACT),
        "source_payload": _read_json(STANDARD_SOURCE_TABLE),
    }


def _pick_semantic(db_row: sqlite3.Row, indexes: dict[str, Any]) -> dict[str, Any]:
    row_key = str(db_row["row_key"] or "")
    catalog_id = str(db_row["helm_catalog_id"] or "")
    symbol_id = str(db_row["s52_symbol_id"] or "")
    return (
        indexes["semantic_by_key"].get(row_key)
        or indexes["semantic_by_catalog"].get(catalog_id)
        or indexes["semantic_by_symbol"].get(symbol_id)
        or {}
    )


def _lookup_rows(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT
          c.*,
          l.source_name,
          l.source_git_sha,
          l.source_file,
          l.lookup_id,
          l.rcid,
          l.sequence_order,
          l.object_acronym,
          l.object_code,
          l.object_name,
          l.primitive_type,
          l.lookup_table,
          l.display_category,
          l.display_priority,
          l.radar_priority,
          l.attribute_predicates,
          l.instruction AS lookup_instruction,
          l.symbol_refs AS lookup_symbol_refs,
          l.line_style_refs AS lookup_line_style_refs,
          l.pattern_refs AS lookup_pattern_refs,
          l.color_refs AS lookup_color_refs,
          l.conditional_refs AS lookup_conditional_refs,
          l.text_refs AS lookup_text_refs,
          ast.parse_status AS db_ast_status,
          ast.command_sequence AS db_ast_command_sequence,
          ast.ast AS db_ast,
          ast.symbol_refs AS ast_symbol_refs,
          ast.line_style_refs AS ast_line_style_refs,
          ast.pattern_refs AS ast_pattern_refs,
          ast.color_refs AS ast_color_refs,
          ast.conditional_refs AS ast_conditional_refs,
          ast.text_refs AS ast_text_refs,
          ast.parse_errors AS db_ast_parse_errors,
          r.asset AS resolver_asset,
          r.helm_catalog_id,
          r.resolver_status,
          r.s101_mapping_type,
          r.s101_crosswalk_class,
          r.basis AS s101_basis,
          r.runtime_scope,
          r.s101_feature_type AS resolver_s101_feature_type,
          r.s101_rule_file,
          r.s101_direct_symbol_id,
          r.exact_filename_match,
          r.false_filename_gap,
          r.s101_attributes AS resolver_s101_attributes,
          r.portrayal_evidence,
          r.unresolved_reasons AS resolver_unresolved_reasons,
          r.source_root AS resolver_source_root
        FROM runtime_symbol_candidate_v1 c
        LEFT JOIN s52_portrayal_lookup l ON l.id = c.s52_lookup_id
        LEFT JOIN s52_instruction_ast ast ON ast.s52_lookup_id = c.s52_lookup_id
        LEFT JOIN iconforge_s101_resolver_row r ON r.asset = c.s52_symbol_id
        ORDER BY c.s52_lookup_id
        """
    ).fetchall()


def _gate_rows(conn: sqlite3.Connection) -> dict[int, list[dict[str, Any]]]:
    by_lookup: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in conn.execute(
        """
        SELECT s52_lookup_id, gate_name, gate_status, severity, detail, evidence
        FROM runtime_symbol_gate
        ORDER BY s52_lookup_id, gate_name
        """
    ):
        by_lookup[int(row["s52_lookup_id"])].append({
            "name": row["gate_name"],
            "status": row["gate_status"],
            "severity": row["severity"],
            "detail": row["detail"],
            "evidence": _json_value(row["evidence"], {}),
        })
    return by_lookup


def _existing_chartsymbols() -> Path | None:
    for path in CHARTSYMBOLS_CANDIDATES:
        if path.exists():
            return path
    return None


def _find_s101_file(relative_path: str | None) -> Path | None:
    if not relative_path:
        return None
    rel = Path(relative_path)
    for root in S101_LOCAL_ROOTS:
        candidate = root / rel
        if candidate.exists():
            return candidate
    return None


def _find_s101_feature_catalogue() -> Path | None:
    for root in S101_LOCAL_ROOTS:
        for name in ("FeatureCatalogue.xml", "featureCatalogue.xml"):
            candidate = root / name
            if candidate.exists():
                return candidate
        matches = list(root.glob("**/FeatureCatalogue.xml")) if root.exists() else []
        if matches:
            return matches[0]
    return None


def _decode_colour(value: Any) -> list[str]:
    values = value if isinstance(value, list) else [value]
    return [
        standard_source_table.S57_COLOURS.get(str(item), f"unknown_s57_colour_{item}")
        for item in values
    ]


def _decode_attribute(predicate: dict[str, Any]) -> dict[str, Any]:
    attribute = str(predicate.get("attribute") or "").upper()
    value = predicate.get("value")
    decoded: Any = value
    dictionary = "raw_value_only"
    status = "raw_only"

    if attribute == "COLOUR":
        decoded = _decode_colour(value)
        dictionary = "S57_COLOURS"
        status = "decoded"
    elif attribute == "COLPAT":
        decoded = standard_source_table.S57_PATTERNS.get(str(value), f"unknown_s57_pattern_{value}")
        dictionary = "S57_PATTERNS"
        status = "decoded" if not str(decoded).startswith("unknown_") else "unknown_code"
    elif attribute == "BOYSHP":
        decoded = standard_source_table.BOY_SHAPES.get(str(value), f"unknown_s57_buoy_shape_{value}")
        dictionary = "BOY_SHAPES"
        status = "decoded" if not str(decoded).startswith("unknown_") else "unknown_code"
    elif attribute in {"BCNSHP", "BCNSH", "BCNSHP"}:
        decoded = standard_source_table.BCN_SHAPES.get(str(value), f"unknown_s57_beacon_shape_{value}")
        dictionary = "BCN_SHAPES"
        status = "decoded" if not str(decoded).startswith("unknown_") else "unknown_code"

    return {
        "raw": predicate.get("raw"),
        "attribute": attribute or predicate.get("attribute"),
        "attribute_name": predicate.get("attribute_name"),
        "attribute_code": predicate.get("attribute_code"),
        "attribute_type": predicate.get("attribute_type"),
        "operator": predicate.get("operator"),
        "raw_value": value,
        "decoded_value": decoded,
        "decode_status": status,
        "dictionary": dictionary,
    }


def _decoded_attributes(predicates: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    decoded = [_decode_attribute(predicate) for predicate in predicates]
    gaps = []
    for item in decoded:
        if item["decode_status"] == "unknown_code":
            gaps.append(f"authority_trace:unknown_dictionary_code:{item['attribute']}")
    return decoded, gaps


def _semantic_tuple(db_row: sqlite3.Row) -> dict[str, Any]:
    return _json_value(db_row["semantic_tuple"], {})


def _s52_visual_recipe(db_row: sqlite3.Row, semantic: dict[str, Any]) -> dict[str, Any]:
    ast_symbol_refs = _json_value(db_row["ast_symbol_refs"], [])
    lookup_symbol_refs = _json_value(db_row["lookup_symbol_refs"], [])
    symbol_refs = ast_symbol_refs or lookup_symbol_refs
    ast_line_refs = _json_value(db_row["ast_line_style_refs"], [])
    ast_pattern_refs = _json_value(db_row["ast_pattern_refs"], [])
    recipe = semantic.get("helm_symbol_recipe") or {}
    return {
        "selected_symbol_refs": symbol_refs,
        "selected_line_style_refs": ast_line_refs or _json_value(db_row["lookup_line_style_refs"], []),
        "selected_pattern_refs": ast_pattern_refs or _json_value(db_row["lookup_pattern_refs"], []),
        "selected_colour_refs": _json_value(db_row["ast_color_refs"], []) or _json_value(db_row["lookup_color_refs"], []),
        "selected_conditional_refs": _json_value(db_row["ast_conditional_refs"], []) or _json_value(db_row["lookup_conditional_refs"], []),
        "selected_text_refs": _json_value(db_row["ast_text_refs"], []) or _json_value(db_row["lookup_text_refs"], []),
        "shape_family": recipe.get("shape_family"),
        "colour_tokens": recipe.get("color_tokens") or [],
        "pattern_token": recipe.get("pattern_token"),
        "recipe_status": semantic.get("helm_symbol_recipe_status") or recipe.get("status") or "",
        "recipe_source": "semantic_evidence_db.helm_symbol_recipe",
    }


def _s101_evidence(db_row: sqlite3.Row) -> dict[str, Any]:
    portrayal = _json_value(db_row["portrayal_evidence"], {})
    attrs = _json_value(db_row["resolver_s101_attributes"], {})
    unresolved = _json_value(db_row["resolver_unresolved_reasons"], [])
    rule_file = db_row["s101_rule_file"]
    local_rule = _find_s101_file(rule_file)
    feature_catalogue = _find_s101_feature_catalogue()
    direct = portrayal.get("direct_symbol") or {}
    shape_witness = portrayal.get("shape_witness") or {}
    instruction_basis = portrayal.get("instruction_basis") or []
    rule_instruction_refs = portrayal.get("rule_instruction_refs") or []
    return {
        "resolver_status": db_row["resolver_status"],
        "mapping_type": db_row["s101_mapping_type"],
        "crosswalk_class": db_row["s101_crosswalk_class"],
        "basis": db_row["s101_basis"],
        "runtime_scope": db_row["runtime_scope"],
        "feature_type": db_row["resolver_s101_feature_type"],
        "rule_file": rule_file,
        "rule_file_local_path": str(local_rule) if local_rule else "",
        "rule_file_sha256": _sha256(local_rule) if local_rule else None,
        "feature_catalogue_local_path": str(feature_catalogue) if feature_catalogue else "",
        "feature_catalogue_sha256": _sha256(feature_catalogue) if feature_catalogue else None,
        "direct_symbol_id": db_row["s101_direct_symbol_id"],
        "direct_symbol_file": direct.get("symbol_file"),
        "direct_symbol_matched": direct.get("matched"),
        "shape_witness": {
            "source": shape_witness.get("source"),
            "basis": shape_witness.get("basis"),
            "symbol_id": shape_witness.get("symbol_id"),
            "symbol_file": shape_witness.get("symbol_file"),
            "local_reference_path": shape_witness.get("local_reference_path"),
            "colour_application": shape_witness.get("colour_application"),
        },
        "attributes": attrs,
        "instruction_basis_count": len(instruction_basis),
        "instruction_basis": [
            {
                "basis": item.get("basis"),
                "kind": item.get("kind"),
                "feature_type": item.get("feature_type"),
                "rule_file": item.get("rule_file"),
                "symbol_id": item.get("symbol_id"),
                "symbol_file": item.get("symbol_file"),
                "attributes": item.get("attributes"),
            }
            for item in instruction_basis[:5]
        ],
        "rule_instruction_refs_count": len(rule_instruction_refs),
        "unresolved_reasons": unresolved,
        "source_boundary": (
            "S-101 catalogue/Lua files are local audit references by hash only; "
            "they are not vendored Helm source assets."
        ),
    }


def _source_files() -> dict[str, Any]:
    chartsymbols = _existing_chartsymbols()
    feature_catalogue = _find_s101_feature_catalogue()
    return {
        "db": {
            "path": str(DB_PATH),
            "sha256": _sha256(DB_PATH),
        },
        "chartsymbols_xml": {
            "path": str(chartsymbols) if chartsymbols else "",
            "sha256": _sha256(chartsymbols) if chartsymbols else None,
            "role": "OpenCPN S-52 implementation witness and lookup spine",
        },
        "s57_dictionary_decode": {
            "source": "forge/standard_source_table.py constants",
            "builder_path": str(STANDARD_SOURCE_BUILDER.relative_to(ROOT)),
            "builder_sha256": _sha256(STANDARD_SOURCE_BUILDER),
            "source_table_path": str(STANDARD_SOURCE_TABLE.relative_to(ROOT)),
            "source_table_sha256": _sha256(STANDARD_SOURCE_TABLE),
            "official_catalogue_status": "not_machine_readable_locally",
        },
        "s101_feature_catalogue": {
            "path": str(feature_catalogue) if feature_catalogue else "",
            "sha256": _sha256(feature_catalogue) if feature_catalogue else None,
            "status": "present" if feature_catalogue else "missing",
        },
        "s101_local_roots": [
            {
                "path": str(root),
                "exists": root.exists(),
                "role": "external_local_audit_reference_not_redistributed",
            }
            for root in S101_LOCAL_ROOTS
        ],
        "sidecars": {
            "semantic_evidence_db": {"path": str(SEMANTIC_DB.relative_to(ROOT)), "sha256": _sha256(SEMANTIC_DB)},
            "rule_contract": {"path": str(RULE_CONTRACT.relative_to(ROOT)), "sha256": _sha256(RULE_CONTRACT)},
            "recipe_contract": {"path": str(RECIPE_CONTRACT.relative_to(ROOT)), "sha256": _sha256(RECIPE_CONTRACT)},
            "colour_authority": {"path": str(COLOUR_AUTHORITY.relative_to(ROOT)), "sha256": _sha256(COLOUR_AUTHORITY)},
        },
    }


def _trace_status(reason_codes: list[str], runtime_blocker: bool) -> str:
    if runtime_blocker:
        return "blocked"
    if reason_codes:
        return "warn"
    return "trace_ready"


def _row_trace(
    db_row: sqlite3.Row,
    gates: list[dict[str, Any]],
    indexes: dict[str, Any],
) -> dict[str, Any]:
    symbol_id = str(db_row["s52_symbol_id"] or "")
    predicates = _json_value(db_row["attribute_predicates"], [])
    decoded_predicates, dictionary_gaps = _decoded_attributes(predicates)
    semantic_tuple = _semantic_tuple(db_row)
    semantic = _pick_semantic(db_row, indexes)
    s101 = _s101_evidence(db_row)
    colour = indexes["colour_by_asset"].get(symbol_id) or {}
    recipe_sidecar = indexes["recipe_by_symbol"].get(symbol_id) or {}
    helm_recipe = semantic.get("helm_symbol_recipe") or {}
    helm_interpretation = semantic.get("helm_interpretation") or {}

    reason_codes: list[str] = []
    reason_codes.extend(dictionary_gaps)
    if not predicates:
        reason_codes.append("authority_trace:s57_attribute_predicates_empty")
    if not semantic_tuple:
        reason_codes.append("authority_trace:semantic_tuple_missing")
    if not db_row["lookup_instruction"]:
        reason_codes.append("authority_trace:s52_instruction_missing")
    if db_row["db_ast_status"] != "complete":
        reason_codes.append(f"authority_trace:s52_ast_{db_row['db_ast_status'] or 'missing'}")
    if not semantic:
        reason_codes.append("authority_trace:semantic_sidecar_missing")
    if not recipe_sidecar and not (semantic.get("helm_symbol_recipe") if semantic else None):
        reason_codes.append("authority_trace:helm_recipe_sidecar_missing")
    if not colour:
        reason_codes.append("authority_trace:colour_authority_missing")
    elif colour.get("runtime_blocker"):
        reason_codes.append("authority_trace:colour_authority_blocks_runtime")
    elif colour.get("gate_status") == "pending":
        reason_codes.append("authority_trace:colour_authority_pending")

    s101_class = str(s101.get("crosswalk_class") or "")
    if not db_row["resolver_asset"]:
        reason_codes.append("authority_trace:s101_resolver_row_missing")
    elif s101_class in S101_REQUIRED_CLASSES:
        if not s101.get("feature_type"):
            reason_codes.append("authority_trace:s101_feature_type_missing")
        if not s101.get("rule_file"):
            reason_codes.append("authority_trace:s101_rule_file_missing")
        elif not s101.get("rule_file_sha256"):
            reason_codes.append("authority_trace:s101_rule_file_not_hashed")
        if not s101.get("feature_catalogue_sha256"):
            reason_codes.append("authority_trace:s101_feature_catalogue_missing")
    elif s101_class in NON_S101_CLASSES:
        reason_codes.append(f"authority_trace:{s101_class}")
    else:
        reason_codes.append("authority_trace:s101_crosswalk_class_unresolved")
    if s101.get("unresolved_reasons"):
        reason_codes.append("authority_trace:s101_resolver_unresolved_reasons_present")

    if (semantic.get("helm_symbol_recipe_status") or helm_recipe.get("status")) != "recipe_ready":
        reason_codes.append("authority_trace:helm_recipe_not_ready")
    if semantic.get("helm_interpretation_status") != "helm_interpretation_ready":
        reason_codes.append("authority_trace:helm_interpretation_not_ready")
    if not db_row["runtime_eligible"]:
        reason_codes.append("authority_trace:runtime_candidate_not_eligible")
    for gate in gates:
        if gate["status"] in {"blocked", "pending"}:
            reason_codes.append(f"authority_trace:runtime_gate_{gate['name']}_{gate['status']}")

    runtime_blocker = bool(reason_codes)
    return {
        "schema": SCHEMA,
        "trace_id": f"s52_lookup:{db_row['s52_lookup_id']}",
        "s52_lookup_id": db_row["s52_lookup_id"],
        "row_key": db_row["row_key"],
        "symbol_id": symbol_id,
        "object_class": db_row["object_class"],
        "authority_status": _trace_status(reason_codes, runtime_blocker),
        "gate_status": "blocked" if runtime_blocker else "pass",
        "runtime_blocker": runtime_blocker,
        "reason_codes": sorted(set(reason_codes)),
        "s57_feature": {
            "object_class": db_row["object_class"],
            "object_name": db_row["object_name"],
            "geometry": db_row["geometry"],
            "primitive_type": db_row["primitive_type"],
            "raw_attribute_predicates": predicates,
            "decoded_attribute_predicates": decoded_predicates,
            "semantic_tuple": semantic_tuple,
        },
        "s57_dictionary_decode": {
            "status": "decoded_with_gaps" if dictionary_gaps else "decoded",
            "decoded_colours": [
                colour
                for item in decoded_predicates
                if item.get("attribute") == "COLOUR"
                for colour in (item.get("decoded_value") if isinstance(item.get("decoded_value"), list) else [item.get("decoded_value")])
            ],
            "source": "forge.standard_source_table.S57_COLOURS/S57_PATTERNS/BOY_SHAPES/BCN_SHAPES",
            "source_hash": _sha256(STANDARD_SOURCE_BUILDER),
            "official_catalogue_status": "not_machine_readable_locally",
        },
        "s52_lookup": {
            "source_name": db_row["source_name"],
            "source_git_sha": db_row["source_git_sha"],
            "source_file": db_row["source_file"],
            "lookup_id": db_row["lookup_id"],
            "rcid": db_row["rcid"],
            "sequence_order": db_row["sequence_order"],
            "lookup_table": db_row["lookup_table"],
            "display_category": db_row["display_category"],
            "display_priority": db_row["display_priority"],
            "radar_priority": db_row["radar_priority"],
            "instruction": db_row["lookup_instruction"],
        },
        "s52_instruction_ast": {
            "parse_status": db_row["db_ast_status"],
            "command_sequence": _json_value(db_row["db_ast_command_sequence"], []),
            "symbol_refs": _json_value(db_row["ast_symbol_refs"], []),
            "line_style_refs": _json_value(db_row["ast_line_style_refs"], []),
            "pattern_refs": _json_value(db_row["ast_pattern_refs"], []),
            "conditional_refs": _json_value(db_row["ast_conditional_refs"], []),
            "text_refs": _json_value(db_row["ast_text_refs"], []),
            "parse_errors": _json_value(db_row["db_ast_parse_errors"], []),
        },
        "s52_visual_recipe": _s52_visual_recipe(db_row, semantic),
        "s101_mapping": s101,
        "helm_interpretation": {
            "status": semantic.get("helm_interpretation_status") or "missing",
            "source": semantic.get("helm_interpretation_source") or "",
            "section_keys": sorted((helm_interpretation.get("sections") or {}).keys()),
        },
        "helm_recipe": {
            "status": semantic.get("helm_symbol_recipe_status") or helm_recipe.get("status") or "missing",
            "version": helm_recipe.get("version"),
            "shape_family": helm_recipe.get("shape_family"),
            "color_tokens": helm_recipe.get("color_tokens") or [],
            "pattern_token": helm_recipe.get("pattern_token"),
            "palette_version": helm_recipe.get("palette_version"),
            "style_version": helm_recipe.get("style_version"),
            "reason_codes": helm_recipe.get("reason_codes") or [],
        },
        "colour_authority": {
            "status": colour.get("status"),
            "gate_status": colour.get("gate_status"),
            "runtime_blocker": bool(colour.get("runtime_blocker")),
            "render_colour_authority": colour.get("render_colour_authority"),
            "feature_colour_sequence": colour.get("feature_colour_sequence") or [],
            "visual_colour_sequence": colour.get("visual_colour_sequence") or [],
            "visual_pattern": colour.get("visual_pattern"),
            "reason_codes": colour.get("reason_codes") or [],
        },
        "runtime_gate": {
            "runtime_eligible": bool(db_row["runtime_eligible"]),
            "candidate_status": db_row["candidate_status"],
            "blocking_gate_count": db_row["blocking_gate_count"],
            "pending_gate_count": db_row["pending_gate_count"],
            "warning_gate_count": db_row["warning_gate_count"],
            "gates": [
                {
                    "name": gate["name"],
                    "status": gate["status"],
                    "severity": gate["severity"],
                    "detail": gate["detail"],
                }
                for gate in gates
            ],
        },
    }


def _asset_summaries(
    conn: sqlite3.Connection,
    trace_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    traces_by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in trace_rows:
        traces_by_symbol[row["symbol_id"]].append(row)

    resolver_rows = conn.execute(
        """
        SELECT asset, helm_catalog_id, object_class, resolver_status,
               s101_mapping_type, s101_crosswalk_class, unresolved_reasons
        FROM iconforge_s101_resolver_row
        ORDER BY asset
        """
    ).fetchall()
    summaries = []
    for row in resolver_rows:
        asset = str(row["asset"])
        traces = traces_by_symbol.get(asset, [])
        status_counts = Counter(trace["authority_status"] for trace in traces)
        reason_counts: Counter[str] = Counter()
        for trace in traces:
            reason_counts.update(trace["reason_codes"])
        runtime_blocker = not traces or any(trace["runtime_blocker"] for trace in traces)
        summaries.append({
            "asset": asset,
            "helm_catalog_id": row["helm_catalog_id"],
            "object_class": row["object_class"],
            "resolver_status": row["resolver_status"],
            "s101_mapping_type": row["s101_mapping_type"],
            "s101_crosswalk_class": row["s101_crosswalk_class"],
            "authority_status": "blocked" if runtime_blocker else "trace_ready",
            "gate_status": "blocked" if runtime_blocker else "pass",
            "runtime_blocker": runtime_blocker,
            "trace_row_count": len(traces),
            "status_counts": dict(sorted(status_counts.items())),
            "top_reason_codes": dict(reason_counts.most_common(12)),
            "unresolved_reasons": _json_value(row["unresolved_reasons"], []),
            "representative_trace_ids": [trace["trace_id"] for trace in traces[:5]],
        })
    return summaries


def _gap_rows(trace_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gaps = []
    for row in trace_rows:
        for reason in row["reason_codes"]:
            gaps.append({
                "schema": "helm.iconforge.authority_trace_gap.v1",
                "trace_id": row["trace_id"],
                "s52_lookup_id": row["s52_lookup_id"],
                "row_key": row["row_key"],
                "symbol_id": row["symbol_id"],
                "object_class": row["object_class"],
                "reason_code": reason,
                "gate_status": "blocked" if row["runtime_blocker"] else "warn",
            })
    return gaps


def build(*, db_path: Path = DB_PATH) -> dict[str, Any]:
    indexes = _indexes()
    with _connect(db_path) as conn:
        gate_index = _gate_rows(conn)
        lookup_rows = _lookup_rows(conn)
        trace_rows = [
            _row_trace(row, gate_index.get(int(row["s52_lookup_id"]), []), indexes)
            for row in lookup_rows
        ]
        asset_summaries = _asset_summaries(conn, trace_rows)

    reason_counts: Counter[str] = Counter()
    status_counts = Counter(row["authority_status"] for row in trace_rows)
    asset_status_counts = Counter(row["authority_status"] for row in asset_summaries)
    for row in trace_rows:
        reason_counts.update(row["reason_codes"])
    gaps = _gap_rows(trace_rows)

    payload = {
        "schema": SCHEMA,
        "schema_version": 1,
        "status": "authority_trace_gate_complete",
        "policy": {
            "browser_business_logic_allowed": False,
            "runtime_export_rule": (
                "Runtime/package export must remain blocked unless the authority trace "
                "is pass, all upstream gates pass, and a signed human approval exists."
            ),
            "no_authority_from": [
                "OpenCPN PNG pixels",
                "S-101 filename equality alone",
                "asset prefix heuristics",
                "visual similarity alone",
                "browser JavaScript fallbacks",
            ],
            "clean_room_boundary": (
                "OpenCPN/S-52 and S-101 materials are evidence/comparison inputs. "
                "Helm generated SVGs and manifests remain owned outputs."
            ),
        },
        "source": _source_files(),
        "summary": {
            "s52_lookup_rows": len(trace_rows),
            "authority_trace_rows": len(trace_rows),
            "authority_trace_gap_rows": len(gaps),
            "asset_summary_rows": len(asset_summaries),
            "authority_status_counts": dict(sorted(status_counts.items())),
            "asset_authority_status_counts": dict(sorted(asset_status_counts.items())),
            "reason_counts": dict(sorted(reason_counts.items())),
            "runtime_blocker_rows": sum(1 for row in trace_rows if row["runtime_blocker"]),
            "runtime_trace_ready_rows": sum(1 for row in trace_rows if not row["runtime_blocker"]),
        },
        "golden_fixtures": {
            "required_symbols": [
                "BOYLAT13",
                "BOYLAT23",
                "BOYLAT25",
                "BOYLAT52",
                "BOYLAT53",
                "BOYLAT54",
                "BOYLAT55",
                "BOYLAT56",
                "BOYSPH79",
                "TOPSHP28",
                "TOPMAR01",
                "VRMEBL01",
                "CLRLIN01",
                "BORDER01",
            ],
            "colour_decode_fixture": {
                "raw": "COLOUR4,3,4",
                "expected_decoded_colours": ["green", "red", "green"],
                "source": "forge.standard_source_table.S57_COLOURS",
            },
        },
        "tables": {
            "authority_trace": {"rows_key": "rows", "row_count": len(trace_rows)},
            "authority_trace_gap": {"rows_key": "gap_rows", "row_count": len(gaps)},
            "authority_asset_summary": {"rows_key": "asset_summaries", "row_count": len(asset_summaries)},
        },
        "rows": trace_rows,
        "gap_rows": gaps,
        "asset_summaries": asset_summaries,
    }
    _write_reports(payload)
    return payload


def _write_reports(payload: dict[str, Any]) -> None:
    _write_json(REPORT_JSON, payload)
    summary = payload["summary"]
    lines = [
        "# Authority Trace Gate",
        "",
        "FORGE-34 backend-owned trace from S-57/S-52 inputs to Helm runtime/package gating.",
        "",
        f"- schema: `{payload['schema']}`",
        f"- status: `{payload['status']}`",
        f"- s52_lookup_rows: `{summary['s52_lookup_rows']}`",
        f"- authority_trace_rows: `{summary['authority_trace_rows']}`",
        f"- authority_trace_gap_rows: `{summary['authority_trace_gap_rows']}`",
        f"- asset_summary_rows: `{summary['asset_summary_rows']}`",
        f"- runtime_blocker_rows: `{summary['runtime_blocker_rows']}`",
        "",
        "## Policy",
        "",
        "- Backend/DB owns the authority chain. Browser pages display it only.",
        "- Runtime export remains fail-closed when any required authority link is missing.",
        "- OpenCPN rendered assets and S-101 SVG witnesses are comparison/evidence inputs, not Helm-owned artwork source.",
        "- S-101 Lua files may be hashed as local audit references but are not vendored into the generated symbol package.",
        "",
        "## Status Counts",
        "",
        "| Status | Count |",
        "| --- | ---: |",
    ]
    for status, count in summary["authority_status_counts"].items():
        lines.append(f"| `{status}` | {count} |")
    lines.extend([
        "",
        "## Top Gap Reasons",
        "",
        "| Reason | Count |",
        "| --- | ---: |",
    ])
    for reason, count in Counter(summary["reason_counts"]).most_common(20):
        lines.append(f"| `{reason}` | {count} |")
    lines.extend([
        "",
        "## Golden Fixture Coverage",
        "",
        "| Symbol | Trace rows | Status counts |",
        "| --- | ---: | --- |",
    ])
    traces_by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in payload["rows"]:
        traces_by_symbol[row["symbol_id"]].append(row)
    for symbol in payload["golden_fixtures"]["required_symbols"]:
        traces = traces_by_symbol.get(symbol, [])
        counts = dict(sorted(Counter(row["authority_status"] for row in traces).items()))
        lines.append(f"| `{symbol}` | {len(traces)} | `{counts}` |")
    REPORT_MD.write_text("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--json", type=Path, default=REPORT_JSON)
    parser.add_argument("--markdown", type=Path, default=REPORT_MD)
    args = parser.parse_args(argv)
    payload = build(db_path=args.db)
    if args.json != REPORT_JSON:
        _write_json(args.json, payload)
    if args.markdown != REPORT_MD:
        args.markdown.write_text(REPORT_MD.read_text())
    print(json.dumps({
        "status": payload["status"],
        "summary": payload["summary"],
        "json": str(args.json),
        "markdown": str(args.markdown),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
