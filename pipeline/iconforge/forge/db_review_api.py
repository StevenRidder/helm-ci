"""DB-backed review payloads for Icon Forge proof and approval UI.

The browser must display backend evidence, not derive symbol meaning. This
module reads the merged runtime-contract SQLite DB and returns one canonical
payload shape for review pages, tests, and later UI endpoints.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT.parent.parent / "artifacts" / "opencpn_s52_portrayal.sqlite"
SEMANTIC_DB = ROOT / "catalog" / "semantic_evidence_db.json"
PROOF_MANIFEST = ROOT / "proof" / "manifest.json"
SIGNOFF_JSON = ROOT / "out" / "human_review" / "icon_review_signoff.json"
STYLE_AUDIT = ROOT / "catalog" / "standard_style_audit.json"
COLOUR_AUTHORITY = ROOT / "catalog" / "colour_authority_contract.json"
AUTHORITY_TRACE = ROOT / "catalog" / "authority_trace_gate.json"

SCHEMA = "helm.iconforge.db_review_api.v1"


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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _semantic_indexes() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    payload = _read_json(SEMANTIC_DB)
    rows = payload.get("rows") or []
    by_key = {str(row.get("canonical_row_key")): row for row in rows if row.get("canonical_row_key")}
    by_catalog = {str(row.get("helm_catalog_id")): row for row in rows if row.get("helm_catalog_id")}
    by_symbol: dict[str, dict[str, Any]] = {}
    for row in rows:
        symbol_id = row.get("symbol_id")
        if symbol_id and str(symbol_id) not in by_symbol:
            by_symbol[str(symbol_id)] = row
    return by_key, by_catalog, by_symbol


def _proof_index() -> dict[str, dict[str, Any]]:
    payload = _read_json(PROOF_MANIFEST)
    return {
        str(row.get("symbol_id")): row
        for row in payload.get("symbols") or []
        if row.get("symbol_id")
    }


def _approval_index() -> dict[str, dict[str, Any]]:
    payload = _read_json(SIGNOFF_JSON)
    out = {}
    for row in payload.get("rows") or []:
        asset = row.get("asset")
        if asset:
            out[str(asset)] = row
    return out


def _style_index() -> dict[str, dict[str, Any]]:
    payload = _read_json(STYLE_AUDIT)
    return {
        str(row.get("asset")): row
        for row in payload.get("rows") or []
        if row.get("asset")
    }


def _colour_authority_index() -> dict[str, dict[str, Any]]:
    payload = _read_json(COLOUR_AUTHORITY)
    out: dict[str, dict[str, Any]] = {}
    for row in payload.get("rows") or []:
        asset = str(row.get("asset") or "")
        if not asset:
            continue
        out.setdefault(asset, row)
        out.setdefault(asset.upper(), row)
        out.setdefault(asset.lower(), row)
    return out


def _authority_trace_indexes() -> tuple[dict[int, dict[str, Any]], dict[str, dict[str, Any]]]:
    payload = _read_json(AUTHORITY_TRACE)
    by_lookup: dict[int, dict[str, Any]] = {}
    for row in payload.get("rows") or []:
        lookup_id = row.get("s52_lookup_id")
        if lookup_id is None:
            continue
        try:
            by_lookup[int(lookup_id)] = row
        except (TypeError, ValueError):
            continue
    by_asset = {
        str(row.get("asset")): row
        for row in payload.get("asset_summaries") or []
        if row.get("asset")
    }
    return by_lookup, by_asset


def _style_gate(symbol_id: str, style: dict[str, Any] | None) -> dict[str, Any]:
    if not symbol_id:
        return {
            "schema": "helm.iconforge.style_contract_gate.v1",
            "status": "style_contract_missing",
            "gate_status": "pending",
            "runtime_blocker": True,
            "reason_codes": ["style_contract:symbol_id_missing"],
            "issues": ["symbol_id_missing"],
            "notes": [],
            "audit_path": str(STYLE_AUDIT),
        }
    if not style:
        return {
            "schema": "helm.iconforge.style_contract_gate.v1",
            "status": "style_contract_missing",
            "gate_status": "pending",
            "runtime_blocker": True,
            "reason_codes": ["style_contract:audit_row_missing"],
            "issues": ["audit_row_missing"],
            "notes": [],
            "audit_path": str(STYLE_AUDIT),
        }
    status = style.get("status") or "style_review"
    gate_status = style.get("gate_status")
    if not gate_status:
        gate_status = "pass" if status == "style_pass" else "failed" if status == "style_blocked" else "pending"
    return {
        "schema": "helm.iconforge.style_contract_gate.v1",
        "status": status,
        "gate_status": gate_status,
        "runtime_blocker": gate_status != "pass",
        "reason_codes": style.get("reason_codes") or [f"style_contract:{issue}" for issue in style.get("issues") or []],
        "issues": style.get("issues") or [],
        "notes": style.get("notes") or [],
        "asset_path": style.get("path") or "",
        "audit_path": str(STYLE_AUDIT),
    }


def _colour_authority_gate(symbol_id: str, authority: dict[str, Any] | None) -> dict[str, Any]:
    if not symbol_id:
        return {
            "schema": "helm.iconforge.colour_authority_contract.v1",
            "status": "not_colour_bearing",
            "gate_status": "pass",
            "runtime_blocker": False,
            "render_colour_authority": "not_colour_bearing",
            "feature_colour_sequence": [],
            "visual_colour_sequence": [],
            "visual_pattern": "no_symbol_id",
            "reason_codes": ["colour_authority:not_colour_bearing"],
            "notes": ["s52_lookup_has_no_symbol_id"],
            "report_path": str(COLOUR_AUTHORITY),
        }
    if not authority:
        return {
            "schema": "helm.iconforge.colour_authority_contract.v1",
            "status": "unresolved",
            "gate_status": "pending",
            "runtime_blocker": True,
            "render_colour_authority": "manual_review_required",
            "feature_colour_sequence": [],
            "visual_colour_sequence": [],
            "visual_pattern": "missing_authority_row",
            "reason_codes": ["colour_authority:authority_row_missing"],
            "notes": [],
            "report_path": str(COLOUR_AUTHORITY),
        }
    gate_status = authority.get("gate_status") or "pending"
    return {
        "schema": authority.get("schema") or "helm.iconforge.colour_authority_contract.v1",
        "status": authority.get("status") or "unresolved",
        "gate_status": gate_status,
        "runtime_blocker": bool(authority.get("runtime_blocker")) or gate_status == "pending",
        "render_colour_authority": authority.get("render_colour_authority") or "manual_review_required",
        "feature_colour_sequence": authority.get("feature_colour_sequence") or [],
        "feature_unique_colours": authority.get("feature_unique_colours") or [],
        "missing_feature_colours": authority.get("missing_feature_colours") or [],
        "feature_colour_source": authority.get("feature_colour_source") or "",
        "visual_colour_sequence": authority.get("visual_colour_sequence") or [],
        "visual_unique_colours": authority.get("visual_unique_colours") or [],
        "extra_visual_colours": authority.get("extra_visual_colours") or [],
        "visual_stroke_sequence": authority.get("visual_stroke_sequence") or [],
        "visual_pattern": authority.get("visual_pattern") or "",
        "visual_colour_source": authority.get("visual_colour_source") or "",
        "canonical_svg": authority.get("canonical_svg") or "",
        "reason_codes": authority.get("reason_codes") or [],
        "notes": authority.get("notes") or [],
        "report_path": str(COLOUR_AUTHORITY),
    }


def _authority_trace_gate(
    *,
    lookup_id: int,
    symbol_id: str,
    trace: dict[str, Any] | None,
    asset_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    if not trace:
        return {
            "schema": "helm.iconforge.authority_trace_gate.v1",
            "authority_status": "missing",
            "gate_status": "blocked",
            "runtime_blocker": True,
            "reason_codes": ["authority_trace:trace_row_missing"],
            "s52_lookup_id": lookup_id,
            "symbol_id": symbol_id,
            "asset_summary": asset_summary or {},
            "report_path": str(AUTHORITY_TRACE),
        }
    return {
        "schema": trace.get("schema") or "helm.iconforge.authority_trace_gate.v1",
        "authority_status": trace.get("authority_status") or "missing",
        "gate_status": trace.get("gate_status") or "blocked",
        "runtime_blocker": bool(trace.get("runtime_blocker")) or trace.get("gate_status") != "pass",
        "reason_codes": trace.get("reason_codes") or [],
        "trace_id": trace.get("trace_id"),
        "s52_lookup_id": trace.get("s52_lookup_id") or lookup_id,
        "symbol_id": trace.get("symbol_id") or symbol_id,
        "s57_feature": trace.get("s57_feature") or {},
        "s57_dictionary_decode": trace.get("s57_dictionary_decode") or {},
        "s52_lookup": trace.get("s52_lookup") or {},
        "s52_instruction_ast": trace.get("s52_instruction_ast") or {},
        "s52_visual_recipe": trace.get("s52_visual_recipe") or {},
        "s101_mapping": trace.get("s101_mapping") or {},
        "helm_recipe": trace.get("helm_recipe") or {},
        "helm_interpretation": trace.get("helm_interpretation") or {},
        "runtime_gate": trace.get("runtime_gate") or {},
        "asset_summary": asset_summary or {},
        "report_path": str(AUTHORITY_TRACE),
    }


def _root_path_exists(value: str | None) -> bool:
    if not value:
        return False
    candidate = ROOT / str(value)
    try:
        candidate.resolve().relative_to(ROOT.resolve())
    except ValueError:
        return False
    return candidate.exists()


def _connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _summary(conn: sqlite3.Connection, db_path: Path) -> dict[str, Any]:
    status_counts = {
        row["candidate_status"]: row["count"]
        for row in conn.execute(
            """
            SELECT candidate_status, count(*) AS count
            FROM runtime_symbol_candidate_v1
            GROUP BY candidate_status
            ORDER BY candidate_status
            """
        )
    }
    gate_counts = [
        dict(row)
        for row in conn.execute(
            """
            SELECT gate_name, gate_status, count(*) AS count
            FROM runtime_symbol_gate
            GROUP BY gate_name, gate_status
            ORDER BY gate_name, gate_status
            """
        )
    ]
    total = conn.execute("SELECT count(*) FROM runtime_symbol_candidate_v1").fetchone()[0]
    eligible = conn.execute(
        "SELECT count(*) FROM runtime_symbol_candidate_v1 WHERE runtime_eligible = 1"
    ).fetchone()[0]
    runtime_rows = conn.execute("SELECT count(*) FROM runtime_symbol_portrayal_v1").fetchone()[0]
    partial_ast = conn.execute(
        "SELECT count(*) FROM s52_instruction_ast WHERE parse_status != 'complete'"
    ).fetchone()[0]
    return {
        "db_path": str(db_path),
        "db_sha256": _sha256(db_path),
        "total_candidates": total,
        "runtime_eligible": eligible,
        "runtime_portrayal_rows": runtime_rows,
        "candidate_status_counts": status_counts,
        "gate_counts": gate_counts,
        "partial_s52_instruction_ast_rows": partial_ast,
        "runtime_position": "fail_closed_until_all_required_gates_pass",
    }


def _row_query(symbol_ids: list[str] | None) -> tuple[str, list[Any]]:
    params: list[Any] = []
    where = ""
    if symbol_ids:
        placeholders = ",".join("?" for _ in symbol_ids)
        where = f"WHERE c.s52_symbol_id IN ({placeholders})"
        params.extend(symbol_ids)
    sql = f"""
        SELECT
          c.*,
          l.object_name,
          l.primitive_type,
          l.lookup_table,
          l.display_category,
          l.display_priority,
          l.radar_priority,
          l.attribute_predicates,
          l.instruction AS opencpn_instruction,
          ast.parse_status AS s52_ast_status,
          ast.command_sequence AS s52_command_sequence,
          ast.ast AS s52_ast,
          ast.parse_errors AS s52_parse_errors,
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
          r.s101_attributes AS resolver_s101_attributes,
          r.portrayal_evidence,
          r.unresolved_reasons AS resolver_unresolved_reasons
        FROM runtime_symbol_candidate_v1 c
        LEFT JOIN s52_portrayal_lookup l ON l.id = c.s52_lookup_id
        LEFT JOIN s52_instruction_ast ast ON ast.s52_lookup_id = c.s52_lookup_id
        LEFT JOIN iconforge_s101_resolver_row r ON r.asset = c.s52_symbol_id
        {where}
        ORDER BY c.blocking_gate_count DESC, c.pending_gate_count DESC, c.s52_symbol_id, c.row_key
    """
    return sql, params


def _gates(conn: sqlite3.Connection, lookup_id: int) -> list[dict[str, Any]]:
    return [
        {
            "name": row["gate_name"],
            "status": row["gate_status"],
            "severity": row["severity"],
            "detail": row["detail"],
            "evidence": _json_value(row["evidence"], {}),
        }
        for row in conn.execute(
            """
            SELECT gate_name, gate_status, severity, detail, evidence
            FROM runtime_symbol_gate
            WHERE s52_lookup_id = ?
            ORDER BY
              CASE gate_status
                WHEN 'blocked' THEN 0
                WHEN 'pending' THEN 1
                WHEN 'warn' THEN 2
                ELSE 3
              END,
              gate_name
            """,
            (lookup_id,),
        )
    ]


def _image_paths(
    symbol_id: str,
    semantic: dict[str, Any],
    proof: dict[str, Any] | None,
    portrayal_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    proof_payload = semantic.get("proof_page_payload") or {}
    candidate = proof_payload.get("helm_candidate") or {}
    comparison = (proof or {}).get("comparison_references") or {}
    generated = (proof or {}).get("generated_assets") or {}
    s101 = (
        ((portrayal_evidence or {}).get("shape_witness") or {})
        or ((semantic.get("proof_page_payload") or {}).get("s101_rule_evidence") or {}).get("shape_witness")
        or ((semantic.get("s101_rule_contract") or {}).get("shape_witness") or {})
        or {}
    )
    helm_path = candidate.get("canonical_svg") or generated.get("canonical_svg")
    opencpn_paths = ((comparison.get("opencpn") or {}).get("paths") or {})
    opencpn_path = opencpn_paths.get("day") or next(iter(opencpn_paths.values()), None)
    s101_path = s101.get("local_reference_path")
    return {
        "helm": {
            "canonical_svg": helm_path,
            "palette_resolved_svg": generated.get("palette_resolved_svg") or {},
            "backend_url": f"/api/proof-review/image/{symbol_id}/helm" if _root_path_exists(helm_path) else None,
        },
        "opencpn": {
            "paths": opencpn_paths,
            "role": (comparison.get("opencpn") or {}).get("role") or "comparison_target_only",
            "backend_url": f"/api/proof-review/image/{symbol_id}/opencpn" if _root_path_exists(opencpn_path) else None,
        },
        "s101": {
            "shape_witness": s101,
            "backend_url": f"/api/proof-review/image/{symbol_id}/s101" if _root_path_exists(s101_path) else None,
        },
    }


def _pick_semantic(
    db_row: sqlite3.Row,
    by_key: dict[str, dict[str, Any]],
    by_catalog: dict[str, dict[str, Any]],
    by_symbol: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    row_key = str(db_row["row_key"] or "")
    catalog_id = str(db_row["helm_catalog_id"] or "")
    symbol_id = str(db_row["s52_symbol_id"] or "")
    return by_key.get(row_key) or by_catalog.get(catalog_id) or by_symbol.get(symbol_id) or {}


def _review_row(
    conn: sqlite3.Connection,
    db_row: sqlite3.Row,
    semantic: dict[str, Any],
    proof: dict[str, Any] | None,
    approval: dict[str, Any] | None,
    style: dict[str, Any] | None,
    colour_authority: dict[str, Any] | None,
    authority_trace: dict[str, Any] | None,
    authority_asset_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    symbol_id = str(db_row["s52_symbol_id"] or "")
    semantic_tuple = _json_value(db_row["semantic_tuple"], {})
    source_refs = _json_value(db_row["source_refs"], {})
    s101_attributes = _json_value(db_row["resolver_s101_attributes"], None)
    if s101_attributes is None:
        s101_attributes = _json_value(db_row["s101_attributes"], {})
    portrayal_evidence = _json_value(db_row["portrayal_evidence"], {})
    unresolved = _json_value(db_row["resolver_unresolved_reasons"], [])
    if not unresolved:
        unresolved = semantic.get("unresolved_reasons") or []
    gate_summary = _json_value(db_row["gate_summary"], {})
    gates = _gates(conn, int(db_row["s52_lookup_id"]))
    proof_payload = semantic.get("proof_page_payload") or {}
    helm_candidate = proof_payload.get("helm_candidate") or {}
    runtime_gate = semantic.get("runtime_gate_summary") or {}
    missing: list[str] = []
    if not semantic:
        missing.append("semantic_evidence_sidecar_missing")
    if not symbol_id:
        missing.append("symbol_id_missing")
    if not gates:
        missing.append("runtime_gates_missing")
    if not (semantic.get("helm_interpretation") or {}).get("sections"):
        missing.append("helm_interpretation_text_missing")
    if not helm_candidate.get("canonical_svg"):
        missing.append("helm_candidate_svg_missing")
    style_contract = _style_gate(symbol_id, style)
    if style_contract["gate_status"] == "pending":
        missing.append("style_contract_pending")
    elif style_contract["gate_status"] == "failed":
        missing.append("style_contract_failed")
    colour_contract = _colour_authority_gate(symbol_id, colour_authority)
    if colour_contract["gate_status"] == "pending":
        missing.append("colour_authority_unresolved")
    elif colour_contract["runtime_blocker"]:
        missing.append("colour_authority_blocked")
    authority_contract = _authority_trace_gate(
        lookup_id=int(db_row["s52_lookup_id"]),
        symbol_id=symbol_id,
        trace=authority_trace,
        asset_summary=authority_asset_summary,
    )
    if authority_contract["gate_status"] == "blocked":
        missing.append("authority_trace_blocked")
    elif authority_contract["gate_status"] == "pending":
        missing.append("authority_trace_pending")

    return {
        "row_id": db_row["s52_lookup_id"],
        "row_key": db_row["row_key"],
        "symbol_id": symbol_id,
        "helm_catalog_id": db_row["helm_catalog_id"] or semantic.get("helm_catalog_id"),
        "status": db_row["candidate_status"],
        "opencpn": {
            "description": semantic.get("open_cpn_description")
            or db_row["object_name"]
            or (source_refs.get("opencpn") or {}).get("object_name")
            or "",
            "object_name": db_row["object_name"],
            "instruction": db_row["opencpn_instruction"] or db_row["s52_instruction"],
            "lookup_table": db_row["lookup_table"],
            "display_category": db_row["display_category"],
            "display_priority": db_row["display_priority"],
            "radar_priority": db_row["radar_priority"],
            "role": "comparison_target_and_source_standard_vocabulary",
        },
        "s57": {
            "object_class": db_row["object_class"],
            "description": semantic.get("s57_description") or semantic_tuple.get("semantic_brief") or "",
            "description_source": semantic.get("s57_description_source") or "derived_or_missing",
            "attribute_tuple": semantic.get("s57_attribute_tuple") or semantic_tuple,
            "attribute_predicates": _json_value(db_row["attribute_predicates"], []),
            "geometry": db_row["geometry"],
        },
        "s52": {
            "instruction": db_row["s52_instruction"],
            "ast_status": semantic.get("s52_instruction_ast_status") or db_row["s52_ast_status"],
            "command_sequence": _json_value(db_row["s52_command_sequence"], []),
            "ast": semantic.get("s52_instruction_ast") or _json_value(db_row["s52_ast"], {}),
            "parse_errors": _json_value(db_row["s52_parse_errors"], []),
        },
        "s101": {
            "resolver_status": db_row["resolver_status"] or semantic.get("resolver_status"),
            "mapping_type": db_row["s101_mapping_type"] or semantic.get("s101_mapping_type"),
            "crosswalk_class": db_row["s101_crosswalk_class"] or semantic.get("s101_crosswalk_class"),
            "feature_type": db_row["resolver_s101_feature_type"] or semantic.get("s101_feature_type"),
            "rule_file": db_row["s101_rule_file"] or semantic.get("s101_rule_file"),
            "direct_symbol_id": db_row["s101_direct_symbol_id"],
            "attributes": s101_attributes,
            "portrayal_evidence": portrayal_evidence,
            "unresolved_reasons": unresolved,
            "rule_contract": semantic.get("s101_rule_contract") or {},
            "rule_contract_status": semantic.get("s101_rule_contract_status") or "",
        },
        "helm": {
            "interpretation": semantic.get("helm_interpretation") or {},
            "interpretation_status": semantic.get("helm_interpretation_status") or "missing",
            "recipe": semantic.get("helm_symbol_recipe") or {},
            "recipe_status": semantic.get("helm_symbol_recipe_status") or "missing",
            "candidate": helm_candidate,
        },
        "qa": {
            "runtime_eligible": bool(db_row["runtime_eligible"]),
            "runtime_gate_summary": runtime_gate or gate_summary,
            "style_contract": style_contract,
            "colour_authority": colour_contract,
            "authority_trace": authority_contract,
            "blocking_gate_count": db_row["blocking_gate_count"],
            "pending_gate_count": db_row["pending_gate_count"],
            "warning_gate_count": db_row["warning_gate_count"],
            "gates": gates,
            "missing_evidence": missing,
        },
        "approval": {
            "state": approval or {},
            "controls": {
                "save_review": "/api/save-review",
                "save_signoff": "/api/save-signoff",
                "review_schema": "helm.iconforge.human_review.v1",
                "signoff_schema": "helm.iconforge.human_signoff.v1",
            },
        },
        "images": _image_paths(symbol_id, semantic, proof, portrayal_evidence),
        "source_refs": source_refs,
    }


def build_review_payload(
    *,
    limit: int = 100,
    offset: int = 0,
    symbol_ids: list[str] | None = None,
    db_path: Path = DB_PATH,
) -> dict[str, Any]:
    if not db_path.exists():
        raise FileNotFoundError(f"runtime review DB missing: {db_path}")
    by_key, by_catalog, by_symbol = _semantic_indexes()
    proofs = _proof_index()
    approvals = _approval_index()
    styles = _style_index()
    colour_authorities = _colour_authority_index()
    authority_traces, authority_assets = _authority_trace_indexes()
    with _connect(db_path) as conn:
        sql, params = _row_query(symbol_ids)
        if symbol_ids:
            rows = conn.execute(sql, params).fetchall()
        else:
            rows = conn.execute(sql + " LIMIT ? OFFSET ?", [*params, limit, offset]).fetchall()
        out_rows = []
        for db_row in rows:
            semantic = _pick_semantic(db_row, by_key, by_catalog, by_symbol)
            symbol_id = str(db_row["s52_symbol_id"] or "")
            out_rows.append(
                _review_row(
                    conn,
                    db_row,
                    semantic,
                    proofs.get(symbol_id),
                    approvals.get(symbol_id),
                    styles.get(symbol_id),
                    colour_authorities.get(symbol_id),
                    authority_traces.get(int(db_row["s52_lookup_id"])),
                    authority_assets.get(symbol_id),
                )
            )
        return {
            "schema": SCHEMA,
            "source": {
                "db": str(db_path),
                "db_sha256": _sha256(db_path),
                "semantic_evidence": str(SEMANTIC_DB),
                "proof_manifest": str(PROOF_MANIFEST),
                "style_audit": str(STYLE_AUDIT),
                "colour_authority": str(COLOUR_AUTHORITY),
                "authority_trace": str(AUTHORITY_TRACE),
                "sidecars_are_display_evidence_only": True,
            },
            "summary": _summary(conn, db_path),
            "pagination": {
                "limit": limit,
                "offset": offset,
                "returned": len(out_rows),
                "symbol_filter": symbol_ids or [],
            },
            "rows": out_rows,
        }


def image_path_for(symbol_id: str, kind: str) -> Path | None:
    payload = build_review_payload(symbol_ids=[symbol_id])
    if not payload["rows"]:
        return None
    row = payload["rows"][0]
    images = row["images"]
    if kind == "helm":
        path = images["helm"].get("canonical_svg")
    elif kind == "opencpn":
        paths = images["opencpn"].get("paths") or {}
        path = paths.get("day") or next(iter(paths.values()), None)
    elif kind == "s101":
        witness = images["s101"].get("shape_witness") or {}
        path = witness.get("local_reference_path")
    else:
        return None
    if not path:
        return None
    candidate = ROOT / str(path)
    try:
        candidate.resolve().relative_to(ROOT.resolve())
    except ValueError:
        return None
    return candidate if candidate.exists() else None
