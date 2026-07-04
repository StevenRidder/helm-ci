"""Backfill canonical S-52 TOPSHP -> S-101 TOPMAR mapping evidence.

This module deliberately separates row-level truth from asset-level preview
shortcuts. The runtime DB is keyed by S-52 lookup rows; the review UI may only
use an asset-level TOPMAR witness when all rows for that asset reduce to one
shape-safe S-101 symbol.

Run:
  python3 -m forge.topmark_s101_db_contract
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent


def _default_db() -> Path:
    local = ROOT / "artifacts" / "opencpn_s52_portrayal.sqlite"
    if local.exists():
        return local
    repo_root = ROOT.parents[1]
    return repo_root / "artifacts" / "opencpn_s52_portrayal.sqlite"


DB = _default_db()
CATALOG = ROOT / "catalog"
REPORT_JSON = CATALOG / "topmark_s101_db_mapping.json"
REPORT_MD = CATALOG / "topmark_s101_db_mapping.md"
S101_TOPMAR_RULE = "PortrayalCatalog/Rules/TOPMAR02.lua"
S101_TOPMAR_RULE_URL = (
    "https://github.com/iho-ohi/S-101_Portrayal-Catalogue/"
    "blob/main/PortrayalCatalog/Rules/TOPMAR02.lua"
)
DEFAULT_WITNESSES = {"TMARDEF1", "TMARDEF2"}


# Official S-101 TOPMAR02.lua tables. The topmark shape number comes from the
# S-57 TOPSHP attribute; S-101 chooses a different witness depending on whether
# the topmark is floating (buoy) or rigid/fixed (beacon/daymark).
FLOATING_TOPMARKS = {
    1: "TOPMAR02",
    2: "TOPMAR04",
    3: "TOPMAR10",
    4: "TOPMAR12",
    5: "TOPMAR13",
    6: "TOPMAR14",
    7: "TOPMAR65",
    8: "TOPMAR17",
    9: "TOPMAR16",
    10: "TOPMAR08",
    11: "TOPMAR07",
    12: "TOPMAR14",
    13: "TOPMAR05",
    14: "TOPMAR06",
    15: "TMARDEF2",
    16: "TMARDEF2",
    17: "TMARDEF2",
    18: "TOPMAR10",
    19: "TOPMAR13",
    20: "TOPMAR14",
    21: "TOPMAR13",
    22: "TOPMAR14",
    23: "TOPMAR14",
    24: "TOPMAR02",
    25: "TOPMAR04",
    26: "TOPMAR10",
    27: "TOPMAR17",
    28: "TOPMAR18",
    29: "TOPMAR02",
    30: "TOPMAR17",
    31: "TOPMAR14",
    32: "TOPMAR10",
    33: "TMARDEF2",
}

RIGID_TOPMARKS = {
    1: "TOPMAR22",
    2: "TOPMAR24",
    3: "TOPMAR30",
    4: "TOPMAR32",
    5: "TOPMAR33",
    6: "TOPMAR34",
    7: "TOPMAR85",
    8: "TOPMAR86",
    9: "TOPMAR36",
    10: "TOPMAR28",
    11: "TOPMAR27",
    12: "TOPMAR14",
    13: "TOPMAR25",
    14: "TOPMAR26",
    15: "TOPMAR88",
    16: "TOPMAR87",
    17: "TMARDEF1",
    18: "TOPMAR30",
    19: "TOPMAR33",
    20: "TOPMAR34",
    21: "TOPMAR33",
    22: "TOPMAR34",
    23: "TOPMAR34",
    24: "TOPMAR22",
    25: "TOPMAR24",
    26: "TOPMAR30",
    27: "TOPMAR86",
    28: "TOPMAR89",
    29: "TOPMAR22",
    30: "TOPMAR86",
    31: "TOPMAR14",
    32: "TOPMAR30",
    33: "TMARDEF1",
}


def _loads(text: str | None, default: Any) -> Any:
    if text is None or text == "":
        return default
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return default


def _dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _shape_code(semantic: dict, attrs: dict) -> int | None:
    for key in ("topmark_shape_code", "topmarkShapeCode", "topmarkDaymarkShape", "s57_topmark_shape"):
        value = semantic.get(key)
        if value is None:
            value = attrs.get(key)
        if value in (None, ""):
            continue
        try:
            return int(float(value))
        except (TypeError, ValueError):
            continue
    status = semantic.get("status_condition")
    if isinstance(status, dict) and status.get("topmark_shape") not in (None, ""):
        try:
            return int(float(status["topmark_shape"]))
        except (TypeError, ValueError):
            pass
    return None


def _resource_descriptions(con: sqlite3.Connection) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in con.execute(
        """
        select name, description
        from s52_portrayal_resource
        where resource_type = 'symbol'
        """
    ):
        name = row["name"]
        if name:
            out[str(name)] = str(row["description"] or "")
    return out


def _decode_rows(con: sqlite3.Connection) -> dict[int, dict]:
    out: dict[int, dict] = {}
    for row in con.execute("select * from s52_topmark_shape_decode"):
        out[int(row["code"])] = dict(row)
    return out


def _context_for(row: sqlite3.Row, attrs: dict, description: str) -> tuple[str, str]:
    object_class = str(row["object_class"] or "").upper()
    desc = description.lower()
    if object_class == "DAYMAR" or object_class.startswith("BCN"):
        return "rigid", "object_class_fixed_daymark_or_beacon"
    if object_class.startswith("BOY"):
        return "floating", "object_class_floating_buoy"
    if str(attrs.get("beaconShape") or "").strip():
        return "rigid", "s101_attribute_beaconShape"
    if str(attrs.get("buoyShape") or "").strip():
        return "floating", "s101_attribute_buoyShape"
    if "for beacons" in desc or "beacon top mark" in desc or "beacon topmark" in desc:
        return "rigid", "s52_symbol_description_beacon"
    if "for buoys" in desc or "buoy top mark" in desc or "buoy topmark" in desc:
        return "floating", "s52_symbol_description_buoy"
    if str(attrs.get("topmarkContext") or "").lower() == "daymark":
        return "rigid", "s101_attribute_topmarkContext_daymark"
    return "context_required", "standalone_topmark_requires_host_feature"


def witness_for(code: int | None, context: str) -> tuple[str | None, str | None, bool, str]:
    if code is None:
        return None, None, False, "missing_shape_code"
    if context == "rigid":
        symbol_id = RIGID_TOPMARKS.get(code)
        rule_context = "rigidTopmarks"
    elif context == "floating":
        symbol_id = FLOATING_TOPMARKS.get(code)
        rule_context = "floatingTopmarks"
    else:
        return None, None, False, "context_required"
    if not symbol_id:
        return None, rule_context, False, "missing_s101_rule_symbol"
    if symbol_id in DEFAULT_WITNESSES:
        return symbol_id, rule_context, False, "default_witness_not_shape_safe"
    return symbol_id, rule_context, True, "mapped_shape_witness"


def _witness_path(symbol_id: str | None) -> str | None:
    if not symbol_id:
        return None
    return f"out/topmark_standards_pass/s101_svg/{symbol_id}.svg"


def _s101_symbol_file(symbol_id: str | None) -> str | None:
    if not symbol_id:
        return None
    return f"PortrayalCatalog/Symbols/{symbol_id}.svg"


def _row_mapping(con: sqlite3.Connection) -> list[dict]:
    descriptions = _resource_descriptions(con)
    decodes = _decode_rows(con)
    rows: list[dict] = []
    for row in con.execute(
        """
        select s52_lookup_id, row_key, object_class, s52_symbol_id,
               semantic_tuple, s101_attributes, candidate_status,
               runtime_eligible
        from runtime_symbol_candidate
        where json_extract(semantic_tuple, '$.topmark_shape_code') is not null
           or json_extract(s101_attributes, '$.topmarkShapeCode') is not null
           or json_extract(s101_attributes, '$.topmarkDaymarkShape') is not null
           or object_class = 'TOPMAR'
        order by s52_lookup_id
        """
    ):
        semantic = _loads(row["semantic_tuple"], {})
        attrs = _loads(row["s101_attributes"], {})
        code = _shape_code(semantic, attrs)
        description = descriptions.get(str(row["s52_symbol_id"] or ""), "")
        context, context_basis = _context_for(row, attrs, description)
        symbol_id, rule_context, shape_safe, status = witness_for(code, context)
        decode = decodes.get(code or -1, {})
        evidence = {
            "basis": "canonical_db_runtime_symbol_candidate_plus_TOPMAR02",
            "context_basis": context_basis,
            "s101_rule_file": S101_TOPMAR_RULE,
            "s101_rule_url": S101_TOPMAR_RULE_URL,
            "shape_safe": shape_safe,
            "source_boundary": "reference_only_not_bundled",
        }
        rows.append(
            {
                "s52_lookup_id": int(row["s52_lookup_id"]),
                "row_key": row["row_key"],
                "asset": row["s52_symbol_id"],
                "object_class": row["object_class"],
                "source_topmark_shape_code": code,
                "source_topmark_shape_label": decode.get("source_label")
                or semantic.get("topmark_shape_label")
                or attrs.get("topmarkShapeLabel"),
                "source_topmark_normalized_name": decode.get("normalized_name")
                or semantic.get("topmark"),
                "topmark_context": context,
                "context_basis": context_basis,
                "s101_symbol_id": symbol_id,
                "s101_symbol_file": _s101_symbol_file(symbol_id),
                "s101_local_reference_path": _witness_path(symbol_id),
                "s101_rule_file": S101_TOPMAR_RULE,
                "s101_rule_context": rule_context,
                "shape_safe": 1 if shape_safe else 0,
                "map_status": status,
                "semantic_json": semantic,
                "s101_attributes_json": attrs,
                "evidence_json": evidence,
            }
        )
    return rows


def _asset_rows(rows: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        asset = row.get("asset")
        if asset:
            grouped[str(asset)].append(row)

    out: list[dict] = []
    for asset, asset_rows in sorted(grouped.items()):
        codes = {row["source_topmark_shape_code"] for row in asset_rows if row["source_topmark_shape_code"] is not None}
        safe = [row for row in asset_rows if row["shape_safe"]]
        safe_witnesses = {row["s101_symbol_id"] for row in safe if row["s101_symbol_id"]}
        statuses = {row["map_status"] for row in asset_rows}
        preferred = safe[0] if len(safe_witnesses) == 1 and len(codes) == 1 else asset_rows[0]
        if len(codes) > 1:
            asset_status = "manual_review_ambiguous_asset"
        elif len(safe_witnesses) == 1:
            asset_status = "unambiguous_shape_witness"
        elif "default_witness_not_shape_safe" in statuses:
            asset_status = "default_witness_not_shape_safe"
        elif "context_required" in statuses:
            asset_status = "context_required"
        elif "missing_shape_code" in statuses:
            asset_status = "missing_shape_code"
        else:
            asset_status = "manual_review_unresolved"
        evidence = {
            "row_statuses": sorted(statuses),
            "row_count": len(asset_rows),
            "lookup_ids": [row["s52_lookup_id"] for row in asset_rows],
            "source_topmark_shape_codes": sorted(code for code in codes if code is not None),
            "safe_witnesses": sorted(str(item) for item in safe_witnesses if item),
        }
        out.append(
            {
                "asset": asset,
                "asset_status": asset_status,
                "preferred_s52_lookup_id": preferred["s52_lookup_id"],
                "source_topmark_shape_code": preferred["source_topmark_shape_code"],
                "source_topmark_shape_label": preferred["source_topmark_shape_label"],
                "topmark_context": preferred["topmark_context"],
                "context_basis": preferred["context_basis"],
                "s101_symbol_id": preferred["s101_symbol_id"] if asset_status == "unambiguous_shape_witness" else None,
                "s101_symbol_file": preferred["s101_symbol_file"] if asset_status == "unambiguous_shape_witness" else None,
                "s101_local_reference_path": preferred["s101_local_reference_path"] if asset_status == "unambiguous_shape_witness" else None,
                "shape_safe": 1 if asset_status == "unambiguous_shape_witness" else 0,
                "row_count": len(asset_rows),
                "safe_row_count": len(safe),
                "context_required_count": sum(1 for row in asset_rows if row["map_status"] == "context_required"),
                "evidence_json": evidence,
            }
        )
    return out


def _ensure_schema(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        create table if not exists iconforge_s101_topmark_mapping_row (
          s52_lookup_id integer primary key references runtime_symbol_candidate(s52_lookup_id) on delete cascade,
          row_key text not null,
          asset text,
          object_class text not null,
          source_topmark_shape_code integer,
          source_topmark_shape_label text,
          source_topmark_normalized_name text,
          topmark_context text not null check (topmark_context in ('rigid', 'floating', 'context_required')),
          context_basis text not null,
          s101_symbol_id text,
          s101_symbol_file text,
          s101_local_reference_path text,
          s101_rule_file text not null,
          s101_rule_context text,
          shape_safe integer not null check (shape_safe in (0, 1)),
          map_status text not null,
          semantic_json text not null check (json_valid(semantic_json)),
          s101_attributes_json text not null check (json_valid(s101_attributes_json)),
          evidence_json text not null check (json_valid(evidence_json)),
          source_boundary text not null default 'reference_only_not_bundled',
          created_at text not null default current_timestamp
        );

        create index if not exists idx_iconforge_s101_topmark_mapping_asset
          on iconforge_s101_topmark_mapping_row(asset);

        create table if not exists iconforge_s101_topmark_asset_map (
          asset text primary key,
          asset_status text not null,
          preferred_s52_lookup_id integer references runtime_symbol_candidate(s52_lookup_id) on delete set null,
          source_topmark_shape_code integer,
          source_topmark_shape_label text,
          topmark_context text,
          context_basis text,
          s101_symbol_id text,
          s101_symbol_file text,
          s101_local_reference_path text,
          shape_safe integer not null check (shape_safe in (0, 1)),
          row_count integer not null,
          safe_row_count integer not null,
          context_required_count integer not null,
          evidence_json text not null check (json_valid(evidence_json)),
          source_boundary text not null default 'reference_only_not_bundled',
          created_at text not null default current_timestamp
        );
        """
    )


def _replace_mapping_rows(con: sqlite3.Connection, rows: list[dict], asset_rows: list[dict]) -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    con.execute("delete from iconforge_s101_topmark_mapping_row")
    con.execute("delete from iconforge_s101_topmark_asset_map")
    con.executemany(
        """
        insert into iconforge_s101_topmark_mapping_row (
          s52_lookup_id, row_key, asset, object_class,
          source_topmark_shape_code, source_topmark_shape_label,
          source_topmark_normalized_name, topmark_context, context_basis,
          s101_symbol_id, s101_symbol_file, s101_local_reference_path,
          s101_rule_file, s101_rule_context, shape_safe, map_status,
          semantic_json, s101_attributes_json, evidence_json, created_at
        ) values (
          :s52_lookup_id, :row_key, :asset, :object_class,
          :source_topmark_shape_code, :source_topmark_shape_label,
          :source_topmark_normalized_name, :topmark_context, :context_basis,
          :s101_symbol_id, :s101_symbol_file, :s101_local_reference_path,
          :s101_rule_file, :s101_rule_context, :shape_safe, :map_status,
          :semantic_json, :s101_attributes_json, :evidence_json, :created_at
        )
        """,
        [
            {
                **row,
                "semantic_json": _dumps(row["semantic_json"]),
                "s101_attributes_json": _dumps(row["s101_attributes_json"]),
                "evidence_json": _dumps(row["evidence_json"]),
                "created_at": now,
            }
            for row in rows
        ],
    )
    con.executemany(
        """
        insert into iconforge_s101_topmark_asset_map (
          asset, asset_status, preferred_s52_lookup_id, source_topmark_shape_code,
          source_topmark_shape_label, topmark_context, context_basis,
          s101_symbol_id, s101_symbol_file, s101_local_reference_path,
          shape_safe, row_count, safe_row_count, context_required_count,
          evidence_json, created_at
        ) values (
          :asset, :asset_status, :preferred_s52_lookup_id, :source_topmark_shape_code,
          :source_topmark_shape_label, :topmark_context, :context_basis,
          :s101_symbol_id, :s101_symbol_file, :s101_local_reference_path,
          :shape_safe, :row_count, :safe_row_count, :context_required_count,
          :evidence_json, :created_at
        )
        """,
        [{**row, "evidence_json": _dumps(row["evidence_json"]), "created_at": now} for row in asset_rows],
    )


def _augment_attrs(attrs: dict, mapping: dict) -> dict:
    out = dict(attrs)
    out["topmarkS101MappingStatus"] = mapping["map_status"]
    out["topmarkS101Context"] = mapping["topmark_context"]
    out["topmarkS101ContextBasis"] = mapping["context_basis"]
    out["topmarkS101ShapeSafe"] = bool(mapping["shape_safe"])
    if mapping["s101_symbol_id"]:
        out["topmarkS101SymbolId"] = mapping["s101_symbol_id"]
    return out


def _shape_witness(mapping: dict) -> dict | None:
    symbol_id = mapping.get("s101_symbol_id")
    if not symbol_id:
        return None
    return {
        "matched": bool(mapping["shape_safe"]),
        "symbol_id": symbol_id,
        "symbol_file": mapping["s101_symbol_file"],
        "local_reference_path": mapping["s101_local_reference_path"],
        "basis": f"s101_TOPMAR02_{mapping['s101_rule_context']}_rule_output",
        "source": "official_s101_topmark_rule",
        "colour_application": "renderer_applies_s101_attributes",
        "shape_safe": bool(mapping["shape_safe"]),
        "topmark_context": mapping["topmark_context"],
        "topmark_shape_code": mapping["source_topmark_shape_code"],
        "topmark_shape_label": mapping["source_topmark_shape_label"],
    }


def _augment_existing_evidence(con: sqlite3.Connection, rows: list[dict]) -> None:
    by_lookup = {row["s52_lookup_id"]: row for row in rows}
    for row in con.execute(
        """
        select s52_lookup_id, s101_attributes, portrayal_evidence, unresolved_reasons
        from s101_portrayal_equivalence
        where s52_lookup_id in (
          select s52_lookup_id from iconforge_s101_topmark_mapping_row
        )
        """
    ):
        mapping = by_lookup[int(row["s52_lookup_id"])]
        attrs = _augment_attrs(_loads(row["s101_attributes"], {}), mapping)
        evidence = _loads(row["portrayal_evidence"], {})
        evidence["topmark_mapping"] = mapping["evidence_json"] | {
            "map_status": mapping["map_status"],
            "s101_symbol_id": mapping["s101_symbol_id"],
            "s101_symbol_file": mapping["s101_symbol_file"],
            "s101_local_reference_path": mapping["s101_local_reference_path"],
            "topmark_context": mapping["topmark_context"],
            "topmark_shape_code": mapping["source_topmark_shape_code"],
            "topmark_shape_label": mapping["source_topmark_shape_label"],
        }
        evidence["shape_witness"] = _shape_witness(mapping)
        reasons = list(_loads(row["unresolved_reasons"], []))
        if not mapping["shape_safe"]:
            reason = f"topmark_{mapping['map_status']}"
            if reason not in reasons:
                reasons.append(reason)
        con.execute(
            """
            update s101_portrayal_equivalence
            set s101_attributes = ?,
                portrayal_evidence = ?,
                unresolved_reasons = ?
            where s52_lookup_id = ?
            """,
            (_dumps(attrs), _dumps(evidence), _dumps(reasons), row["s52_lookup_id"]),
        )

    for mapping in rows:
        attrs = _augment_attrs(mapping["s101_attributes_json"], mapping)
        con.execute(
            """
            update runtime_symbol_candidate
            set s101_attributes = ?
            where s52_lookup_id = ?
            """,
            (_dumps(attrs), mapping["s52_lookup_id"]),
        )


def _augment_resolver_rows(con: sqlite3.Connection, asset_rows: list[dict]) -> None:
    by_asset = {row["asset"]: row for row in asset_rows}
    for row in con.execute(
        """
        select asset, s101_attributes, portrayal_evidence, raw_json
        from iconforge_s101_resolver_row
        where asset in (select asset from iconforge_s101_topmark_asset_map)
        """
    ):
        mapping = by_asset.get(row["asset"])
        if not mapping:
            continue
        attrs = _augment_attrs(_loads(row["s101_attributes"], {}), {
            **mapping,
            "map_status": mapping["asset_status"],
        })
        evidence = _loads(row["portrayal_evidence"], {})
        evidence["topmark_asset_mapping"] = {
            "asset_status": mapping["asset_status"],
            "preferred_s52_lookup_id": mapping["preferred_s52_lookup_id"],
            "s101_symbol_id": mapping["s101_symbol_id"],
            "s101_symbol_file": mapping["s101_symbol_file"],
            "s101_local_reference_path": mapping["s101_local_reference_path"],
            "shape_safe": bool(mapping["shape_safe"]),
            "source_boundary": "reference_only_not_bundled",
        }
        evidence["shape_witness"] = _shape_witness({
            **mapping,
            "map_status": mapping["asset_status"],
            "s101_rule_context": "asset_overlay",
            "source_topmark_normalized_name": None,
            "semantic_json": {},
            "s101_attributes_json": {},
            "evidence_json": {},
        })
        raw = _loads(row["raw_json"], {})
        if isinstance(raw, dict):
            raw["s101_attributes"] = attrs
            raw["portrayal_evidence"] = evidence
        con.execute(
            """
            update iconforge_s101_resolver_row
            set s101_attributes = ?,
                portrayal_evidence = ?,
                raw_json = ?
            where asset = ?
            """,
            (_dumps(attrs), _dumps(evidence), _dumps(raw), row["asset"]),
        )


def _tighten_gate_defaults(con: sqlite3.Connection) -> None:
    for row in con.execute(
        """
        select asset, gate_status, recommended_status, finding_codes, raw_json
        from iconforge_topmark_gate_row
        where primary_s101_symbol_id in ('TMARDEF1', 'TMARDEF2')
        """
    ):
        findings = list(_loads(row["finding_codes"], []))
        if "s101_default_witness_not_shape_safe" not in findings:
            findings.append("s101_default_witness_not_shape_safe")
        raw = _loads(row["raw_json"], {})
        if isinstance(raw, dict):
            raw["gate_status"] = "manual_review_required"
            raw["recommended_status"] = "manual_review"
            existing = {
                str(item.get("code"))
                for item in raw.get("findings", [])
                if isinstance(item, dict)
            }
            if "s101_default_witness_not_shape_safe" not in existing:
                raw.setdefault("findings", []).append(
                    {
                        "code": "s101_default_witness_not_shape_safe",
                        "detail": "S-101 TOPMAR02 resolves this TOPSHP code to TMARDEF; this is standards evidence but not a shape-safe drawing witness.",
                    }
                )
        con.execute(
            """
            update iconforge_topmark_gate_row
            set gate_status = 'manual_review_required',
                recommended_status = 'manual_review',
                finding_codes = ?,
                raw_json = ?
            where asset = ?
            """,
            (_dumps(findings), _dumps(raw), row["asset"]),
        )


def _summary(rows: list[dict], asset_rows: list[dict]) -> dict:
    def counts(items: list[dict], key: str) -> dict[str, int]:
        out: dict[str, int] = {}
        for item in items:
            value = str(item.get(key))
            out[value] = out.get(value, 0) + 1
        return dict(sorted(out.items()))

    return {
        "schema": "helm.forge.s101-topmark-db-mapping.v1",
        "row_level_mappings": len(rows),
        "asset_level_mappings": len(asset_rows),
        "row_map_status": counts(rows, "map_status"),
        "asset_status": counts(asset_rows, "asset_status"),
        "shape_safe_row_mappings": sum(1 for row in rows if row["shape_safe"]),
        "shape_safe_asset_overlays": sum(1 for row in asset_rows if row["shape_safe"]),
        "source_rule": S101_TOPMAR_RULE,
        "source_rule_url": S101_TOPMAR_RULE_URL,
        "source_boundary": "reference_only_not_bundled",
    }


def _write_reports(summary: dict, rows: list[dict], asset_rows: list[dict]) -> None:
    CATALOG.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(
        _dumps(
            {
                "summary": summary,
                "rows": rows,
                "asset_rows": asset_rows,
            }
        )
        + "\n"
    )
    md = [
        "# S-101 Topmark DB Mapping",
        "",
        f"- Row-level mappings: {summary['row_level_mappings']}",
        f"- Asset-level mappings: {summary['asset_level_mappings']}",
        f"- Shape-safe row mappings: {summary['shape_safe_row_mappings']}",
        f"- Shape-safe asset overlays: {summary['shape_safe_asset_overlays']}",
        f"- Source rule: {S101_TOPMAR_RULE}",
        f"- Source URL: {S101_TOPMAR_RULE_URL}",
        "",
        "## Row Status",
    ]
    for key, value in summary["row_map_status"].items():
        md.append(f"- {key}: {value}")
    md.append("")
    md.append("## Asset Status")
    for key, value in summary["asset_status"].items():
        md.append(f"- {key}: {value}")
    md.append("")
    md.append("## Notes")
    md.append("- `TMARDEF1` and `TMARDEF2` are recorded as S-101 rule outputs but are not shape-safe drawing witnesses.")
    md.append("- Asset-level overlays are only emitted when the row-level evidence has one unambiguous shape-safe S-101 witness.")
    REPORT_MD.write_text("\n".join(md) + "\n")


def build(db_path: Path = DB, *, write: bool = True) -> dict:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        rows = _row_mapping(con)
        asset_rows = _asset_rows(rows)
        summary = _summary(rows, asset_rows)
        if write:
            with con:
                _ensure_schema(con)
                _replace_mapping_rows(con, rows, asset_rows)
                _augment_existing_evidence(con, rows)
                _augment_resolver_rows(con, asset_rows)
                _tighten_gate_defaults(con)
        _write_reports(summary, rows, asset_rows)
        return {"summary": summary, "rows": rows, "asset_rows": asset_rows}
    finally:
        con.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DB)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = build(args.db, write=not args.dry_run)
    print(json.dumps(result["summary"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
