"""Resolve the remaining reference-gap rows for batch 96.

This is a classification gate, not an art-generation batch. It records which
remaining rows are real symbols needing a SymbolSpec, which are style
primitives/rules, and which are manual/reference blockers.

Run:
  python3 -m forge.standard_reference_resolution_batch96
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
SOURCE_TABLE = CATALOG / "standard_source_table.json"
OUT_JSON = CATALOG / "standard_reference_resolution_batch96.json"
OUT_CSV = CATALOG / "standard_reference_resolution_batch96.csv"
OUT_MD = CATALOG / "standard_reference_resolution_batch96.md"
SPECS_JSON = CATALOG / "symbol_specs_batch96.json"
SPECS_YAML = CATALOG / "symbol_specs_batch96.yaml"
SPECS_MD = CATALOG / "symbol_specs_batch96.md"

BLOCKER_ASSETS = {
    "BCNCON81": {
        "classification": "renderable_from_s57_symbolspec",
        "resolution": "Generate owned beacon/conical special-purpose mark from explicit S-57 conditions; no external art import required.",
        "next_action": "render_batch_from_symbolspec",
        "geometry": {
            "primitive": "conical_beacon_or_buoy_body",
            "colour_pattern": "horizontal_bands",
            "colpat": ["1", "2"],
            "colours": ["blue", "red", "white", "blue"],
            "required_marks": ["OBJNAM text remains separate label, not part of canonical icon"],
        },
        "confidence": 0.78,
    },
    "DANGER53": {
        "classification": "reference_blocked_official_symbol",
        "resolution": "Official S-52 danger symbol row exists, but no tight OpenCPN/S-101/AquaMap/Chart-1 one-symbol witness is attached.",
        "next_action": "attach_tight_reference_before_render",
        "geometry": {
            "primitive": "unknown_danger_symbol",
            "colours": ["black"],
            "required_marks": ["do not promote a generic diamond without official witness"],
        },
        "confidence": 0.34,
    },
    "DGPS01DRFSTA01": {
        "classification": "reference_blocked_official_symbol",
        "resolution": "DGPS/radio-station composite row exists, but current merged token lacks a tight symbol witness.",
        "next_action": "split_or_attach_dgps_and_radio_station_reference",
        "geometry": {
            "primitive": "dgps_radio_station_composite",
            "colours": ["magenta", "black"],
            "required_marks": ["DGPS/radio-station semantics must be confirmed before drawing"],
        },
        "confidence": 0.40,
    },
    "NEWOBJ 01": {
        "classification": "manual_exception_newobj_placeholder",
        "resolution": "NEWOBJ is a placeholder/new-object hook, not a stable nautical symbol to visually promote.",
        "next_action": "manual_exception_or_runtime_placeholder_policy",
        "geometry": {
            "primitive": "new_object_placeholder",
            "colours": ["magenta"],
            "required_marks": ["do not treat as finished chart symbology without product policy"],
        },
        "confidence": 0.70,
    },
    "NEWOBJ01": {
        "classification": "manual_exception_newobj_placeholder",
        "resolution": "NEWOBJ area symbol is a placeholder/new-object hook; line style is handled by the renderer, not a canonical pictogram.",
        "next_action": "manual_exception_or_runtime_placeholder_policy",
        "geometry": {
            "primitive": "new_object_area_placeholder",
            "colours": ["magenta"],
            "line_style": "DASH,2,CHMGD",
            "required_marks": ["do not promote as normal chart artifact without product policy"],
        },
        "confidence": 0.70,
    },
    "VEHTRF01": {
        "classification": "reference_blocked_official_symbol",
        "resolution": "Vehicle-traffic area row exists, but no tight witness is attached; keep blocked until a symbol crop/render is available.",
        "next_action": "attach_tight_reference_before_render",
        "geometry": {
            "primitive": "vehicle_traffic_area",
            "colours": ["gray"],
            "line_style": "DASH,1,CHGRF",
            "required_marks": ["vehicle/traffic geometry must be confirmed before drawing"],
        },
        "confidence": 0.42,
    },
    "boyspp50": {
        "classification": "renderable_from_s57_symbolspec",
        "resolution": "Lowercase legacy special-purpose waterway mark can be generated from S-57 conditions as a yellow special-purpose buoy marker.",
        "next_action": "render_batch_from_symbolspec",
        "geometry": {
            "primitive": "special_purpose_buoy_or_waterway_marker",
            "colours": ["yellow"],
            "conditions": ["catwwm19", "COLOUR6"],
            "required_marks": ["OBJNAM text remains separate label, not part of canonical icon"],
        },
        "confidence": 0.72,
    },
}

PRIMITIVE_ROWS = {
    "ARCSLN01": "arc/sector line style primitive; renderer stroke contract, not a standalone icon",
    "DASH": "generic dashed line primitive used by many lookups; style contract, not a standalone icon",
    "DOTT": "generic dotted line primitive used by obstruction/foul-area rules; style contract, not a standalone icon",
    "SOLD": "generic solid line primitive used by many area/contour rules; style contract, not a standalone icon",
}

CONDITIONAL_RULE_ROWS = {
    "DATCVR01": "data-coverage conditional procedure",
    "DEPARE01": "depth-area conditional procedure",
    "DEPARE02": "depth-area conditional procedure",
    "DEPCNT02": "depth-contour conditional procedure",
    "LEGLIN02": "leg-line conditional procedure",
    "OWNSHP02": "own-ship conditional procedure",
    "QUAPOS01;TX(OBJNAM": "quality-of-position/text conditional procedure",
    "RESARE01": "restricted-area conditional procedure",
    "RESARE02": "restricted-area conditional procedure",
    "RESTRN01": "restriction conditional procedure",
    "SLCONS03": "shoreline-construction conditional procedure",
    "SYMINS01": "symbol-instruction conditional procedure",
    "TOPMARI1": "topmark conditional procedure",
    "VESSEL01": "vessel conditional procedure",
    "VRMEBL01": "VRM/EBL conditional procedure",
}


def _read_rows() -> dict[str, dict]:
    return {row["asset"]: row for row in json.loads(SOURCE_TABLE.read_text())["rows"]}


def _yaml_scalar(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if text == "":
        return '""'
    if all(ch.isalnum() or ch in "_./:-" for ch in text):
        return text
    return json.dumps(text)


def _yaml_lines(value, indent: int = 0) -> list[str]:
    pad = " " * indent
    if isinstance(value, dict):
        lines: list[str] = []
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}{key}:")
                lines.extend(_yaml_lines(item, indent + 2))
            else:
                lines.append(f"{pad}{key}: {_yaml_scalar(item)}")
        return lines
    if isinstance(value, list):
        if not value:
            return [f"{pad}[]"]
        lines: list[str] = []
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}-")
                lines.extend(_yaml_lines(item, indent + 2))
            else:
                lines.append(f"{pad}- {_yaml_scalar(item)}")
        return lines
    return [f"{pad}{_yaml_scalar(value)}"]


def _spec(asset: str, row: dict, decision: dict) -> dict:
    conditions = row.get("s57_structure", {}).get("conditions") or []
    classification = decision["classification"]
    return {
        "id": asset,
        "name": row.get("name") or asset,
        "kind": row.get("kind"),
        "tier": "chart-artifact" if classification == "renderable_from_s57_symbolspec" else "reference-blocked-or-manual-exception",
        "s52_token": asset,
        "s57": {
            "object_class": row.get("s57_structure", {}).get("object_class"),
            "conditions": conditions,
            "instruction": row.get("s57_structure", {}).get("s52_instruction"),
            "lookup_id": row.get("s57_structure", {}).get("lookup_id"),
            "lookup_rcid": row.get("s57_structure", {}).get("lookup_rcid"),
        },
        "source_refs": {
            "s52": asset,
            "opencpn_s52_spine": "chartsymbols.xml lookup metadata only; no raster/vector art imported",
            "standard_source_table": "catalog/standard_source_table.json",
        },
        "asset": {
            "canonical": f"assets/svg/triad_generated/{asset.replace('|;TX(OBJNAM', '_TX_OBJNAM').replace(' ', '_')}.svg",
            "status": classification,
        },
        "qa": {
            "semantic_pass": classification == "renderable_from_s57_symbolspec",
            "visual_parity": "blocked_until_reference_or_next_render"
            if classification != "renderable_from_s57_symbolspec"
            else "ready_for_batch96_render",
            "final_approved": False,
        },
        "geometry": decision["geometry"],
        "generation": {
            "status": decision["next_action"],
            "confidence": decision["confidence"],
            "resolution": decision["resolution"],
        },
        "provenance": {
            "origin": "generated-owned-artwork-plan",
            "allowed_sources": [
                "OpenCPN S-52 lookup metadata",
                "S-57 condition metadata",
                "future public-domain Chart No.1 or locally rendered tight witness when required",
            ],
            "forbidden_sources": ["do not import OpenCPN raster pixels as canonical art"],
        },
    }


def _classification_record(asset: str, row: dict, classification: str, resolution: str, next_action: str, confidence: float, spec: dict | None = None) -> dict:
    helm = row.get("helm_candidate", {})
    return {
        "asset": asset,
        "name": row.get("name"),
        "kind": row.get("kind"),
        "family": row.get("family"),
        "input_candidate_status": helm.get("pre_routing_candidate_status") or helm.get("candidate_status"),
        "input_source_batch": helm.get("source_batch"),
        "classification": classification,
        "resolution": resolution,
        "next_action": next_action,
        "confidence": confidence,
        "symbol_spec": spec,
        "s57_structure": row.get("s57_structure"),
        "reference_counts": {
            key: len(value) if isinstance(value, list) else bool(value)
            for key, value in (row.get("reference_providers") or {}).items()
        },
    }


def build() -> dict:
    rows = _read_rows()
    records = []
    specs = []

    for asset, decision in BLOCKER_ASSETS.items():
        row = rows[asset]
        spec = _spec(asset, row, decision)
        specs.append(spec)
        records.append(_classification_record(
            asset,
            row,
            decision["classification"],
            decision["resolution"],
            decision["next_action"],
            decision["confidence"],
            spec,
        ))

    for asset, reason in PRIMITIVE_ROWS.items():
        row = rows[asset]
        records.append(_classification_record(
            asset,
            row,
            "style_primitive_not_standalone_icon",
            reason,
            "cover_by_renderer_style_contract_and_exclude_from_icon_art_gate",
            0.86,
        ))

    for asset, reason in CONDITIONAL_RULE_ROWS.items():
        row = rows[asset]
        records.append(_classification_record(
            asset,
            row,
            "portrayal_rule_not_standalone_icon",
            reason,
            "track_in_rule_registry_not_icon_art_queue",
            0.84,
        ))

    records.sort(key=lambda item: item["asset"])
    specs.sort(key=lambda item: item["id"])
    counts = Counter(record["classification"] for record in records)
    result = {
        "schema_version": 1,
        "status": "reference_resolution_batch96_written",
        "project": "vulkan",
        "task_id": "FORGE-15",
        "source_table": "catalog/standard_source_table.json",
        "summary": {
            "rows_classified": len(records),
            "symbol_specs": len(specs),
            "renderable_from_s57_symbolspec": counts["renderable_from_s57_symbolspec"],
            "reference_blocked_official_symbol": counts["reference_blocked_official_symbol"],
            "manual_exception_newobj_placeholder": counts["manual_exception_newobj_placeholder"],
            "style_primitive_not_standalone_icon": counts["style_primitive_not_standalone_icon"],
            "portrayal_rule_not_standalone_icon": counts["portrayal_rule_not_standalone_icon"],
            "classification_counts": dict(sorted(counts.items())),
        },
        "records": records,
        "symbol_specs": specs,
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    SPECS_JSON.write_text(json.dumps({"schema_version": 1, "status": "batch96_symbol_specs_written", "symbols": specs}, indent=2, sort_keys=True) + "\n")
    SPECS_YAML.write_text("\n".join(_yaml_lines({"schema_version": 1, "status": "batch96_symbol_specs_written", "symbols": specs})) + "\n")
    _write_csv(records)
    _write_md(result)
    _write_specs_md(specs)
    return result


def _write_csv(records: list[dict]) -> None:
    with OUT_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "asset",
            "name",
            "kind",
            "input_candidate_status",
            "classification",
            "next_action",
            "confidence",
            "resolution",
        ], lineterminator="\n")
        writer.writeheader()
        for record in records:
            writer.writerow({key: record.get(key) for key in writer.fieldnames})


def _write_md(result: dict) -> None:
    lines = [
        "# Standard Reference Resolution Batch 96",
        "",
        "- Project: `vulkan`",
        "- Task: `FORGE-15`",
        "- Purpose: classify the remaining 7 repair blockers plus 19 pending/no-reference rows before any more rendering.",
        "- Final approval: none; this is a routing and SymbolSpec gate only.",
        "",
        "## Summary",
        "",
        "| Metric | Count |",
        "| --- | ---: |",
    ]
    for key, value in result["summary"].items():
        if key == "classification_counts":
            continue
        lines.append(f"| `{key}` | {value} |")
    lines.extend(["", "## Classifications", "", "| Asset | Classification | Next action | Resolution |", "| --- | --- | --- | --- |"])
    for record in result["records"]:
        lines.append(
            f"| `{record['asset']}` | `{record['classification']}` | `{record['next_action']}` | {record['resolution']} |"
        )
    OUT_MD.write_text("\n".join(lines) + "\n")


def _write_specs_md(specs: list[dict]) -> None:
    lines = [
        "# SymbolSpecs Batch 96",
        "",
        "| Asset | Status | Primitive | Colours | Next action |",
        "| --- | --- | --- | --- | --- |",
    ]
    for spec in specs:
        geometry = spec.get("geometry") or {}
        lines.append(
            f"| `{spec['id']}` | `{spec['asset']['status']}` | `{geometry.get('primitive')}` | "
            f"{', '.join(geometry.get('colours') or [])} | `{spec['generation']['status']}` |"
        )
    SPECS_MD.write_text("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser().parse_args(argv)
    result = build()
    print(json.dumps({"status": "ok", "summary": result["summary"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
