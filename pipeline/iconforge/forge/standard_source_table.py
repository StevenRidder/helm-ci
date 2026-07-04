"""Build the normalized source table for Icon Forge.

OpenCPN/S-52 is the structural spine. S-101, Aqua Map, and rendered OpenCPN
examples are provider references mapped onto each S-52/S-57 row. Helm-owned
candidates, judge state, and repair routing attach to the same row.

Run:
  python -m forge.standard_source_table
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

from .s52_normalization import CANONICAL_ASSET_ALIASES
from .s52_normalization import asset_keys as _asset_keys
from .s52_normalization import canonical_asset as _canonical_asset
from .s52_normalization import canonicalize_legacy_value as _canonicalize_legacy_value
from .s52_normalization import repair_s52_instruction as _repair_s52_instruction
from . import triad_reference_candidate_pack as triad


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
OUT = ROOT / "out" / "standard_source_table"
S52 = Path("/Users/steveridder/.helm/runtime/s57data/chartsymbols.xml")

MASTER = CATALOG / "master_symbol_list.json"
TRIAD_PACK = CATALOG / "triad_reference_candidate_pack.json"
TABLE_JSON = CATALOG / "standard_source_table.json"
TABLE_CSV = CATALOG / "standard_source_table.csv"
TABLE_MD = CATALOG / "standard_source_table.md"
JUDGE_QUEUE = OUT / "judge_queue.json"
SEMANTIC_JUDGE_QUEUE = CATALOG / "standard_semantic_shape_judge_queue.json"
ROUTING_BATCH98 = CATALOG / "standard_routing_batch98.json"
ROUTED_QUEUE = CATALOG / "standard_routed_queue.json"

S57_COLOURS = {
    "1": "white",
    "2": "black",
    "3": "red",
    "4": "green",
    "5": "blue",
    "6": "yellow",
    "7": "grey",
    "8": "brown",
    "9": "amber",
    "10": "violet",
    "11": "orange",
    "12": "magenta",
}

S57_PATTERNS = {
    "1": "horizontal bands/stripes in the listed colour order",
    "2": "vertical bands/stripes in the listed colour order",
    "3": "diagonal stripes in the listed colour order",
    "4": "squared/checkered pattern in the listed colour order",
    "5": "border stripe pattern in the listed colour order",
}

BOY_SHAPES = {
    "1": "conical/nun buoy body",
    "2": "can/cylindrical buoy body",
    "3": "spherical buoy body",
    "4": "pillar buoy body",
    "5": "spar buoy body",
    "6": "barrel buoy body",
    "7": "super-buoy body",
    "8": "ice buoy body",
}

BCN_SHAPES = {
    "1": "stake/perch beacon",
    "2": "withy beacon",
    "3": "beacon tower",
    "4": "lattice/tower beacon",
    "5": "pile beacon",
    "6": "cairn beacon",
    "7": "buoyant beacon",
}

OBJECT_USE = {
    "ACHARE": "anchorage-area or anchoring-related chart marking",
    "BCNCAR": "cardinal beacon used to indicate the safe side of danger",
    "BCNISD": "isolated-danger beacon used to mark a hazard with navigable water around it",
    "BCNLAT": "lateral beacon used for channel-side marking",
    "BCNSAW": "safe-water beacon used to mark navigable water",
    "BCNSPP": "special-purpose beacon used for named local purposes",
    "BOYCAR": "cardinal buoy used to indicate the safe side of danger",
    "BOYINB": "installation buoy",
    "BOYISD": "isolated-danger buoy used to mark a hazard with navigable water around it",
    "BOYLAT": "lateral buoy used for port/starboard channel marking",
    "BOYMOR": "mooring buoy",
    "BOYSAW": "safe-water buoy used to mark navigable water",
    "BOYSPP": "special-purpose buoy used for named local purposes",
    "HRBFAC": "harbour facility or service point",
    "LIGHTS": "light characteristic or lighted aid-to-navigation symbol",
    "MORFAC": "mooring facility",
    "OBSTRN": "obstruction or hazard marking",
    "TOPMAR": "topmark symbol attached to an aid to navigation",
    "UWTROC": "underwater/awash rock hazard",
    "WRECKS": "wreck hazard",
}

def _read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _text(node: ET.Element, child: str) -> str | None:
    value = node.findtext(child)
    return value if value not in {"", None} else None


def _int_attr(node: ET.Element | None, key: str) -> int | None:
    if node is None or node.get(key) is None:
        return None
    return int(node.get(key) or 0)


def _point(node: ET.Element | None) -> dict | None:
    if node is None:
        return None
    return {"x": _int_attr(node, "x"), "y": _int_attr(node, "y")}


def _bitmap(node: ET.Element) -> dict | None:
    bitmap = node.find("bitmap")
    if bitmap is None:
        return None
    location = bitmap.find("graphics-location")
    return {
        "width": _int_attr(bitmap, "width"),
        "height": _int_attr(bitmap, "height"),
        "graphics_location": _point(location),
        "pivot": _point(bitmap.find("pivot")),
        "origin": _point(bitmap.find("origin")),
    }


def _vector(node: ET.Element) -> dict | None:
    vector = node.find("vector")
    hpgl = node.findtext("HPGL") or (vector.findtext("HPGL") if vector is not None else None)
    if vector is None and not hpgl:
        return None
    return {
        "width": _int_attr(vector, "width") if vector is not None else None,
        "height": _int_attr(vector, "height") if vector is not None else None,
        "pivot": _point(vector.find("pivot")) if vector is not None else None,
        "origin": _point(vector.find("origin")) if vector is not None else None,
        "hpgl_present": bool(hpgl),
        "hpgl_length": len(hpgl or ""),
    }


def _asset_defs() -> dict[str, list[dict]]:
    root = ET.parse(S52).getroot()
    defs: dict[str, list[dict]] = defaultdict(list)
    for kind, container, item in [
        ("symbol", "symbols", "symbol"),
        ("line-style", "line-styles", "line-style"),
        ("pattern", "patterns", "pattern"),
    ]:
        parent = root.find(container)
        if parent is None:
            continue
        for node in parent.findall(item):
            name = _text(node, "name")
            if not name:
                continue
            defs[name].append({
                "kind": kind,
                "rcid": node.get("RCID"),
                "name": name,
                "description": _text(node, "description"),
                "color_ref": _text(node, "color-ref"),
                "definition": _text(node, "definition"),
                "filltype": _text(node, "filltype"),
                "spacing": _text(node, "spacing"),
                "bitmap": _bitmap(node),
                "vector": _vector(node),
            })
    return defs


def _tokens(instruction: str) -> list[str]:
    return re.findall(r"\b(?:SY|LS|AP|CS|TE)\(([^)]*)\)", instruction or "")


def _lookup_asset_names(instruction: str) -> set[str]:
    names: set[str] = set()
    for command, args in re.findall(r"\b(SY|LS|AP)\(([^)]*)\)", instruction or ""):
        first = args.split(",", 1)[0].strip().strip("'\"")
        if first:
            names.add(first)
    return names


def _lookups_by_asset() -> dict[str, list[dict]]:
    root = ET.parse(S52).getroot()
    out: dict[str, list[dict]] = defaultdict(list)
    parent = root.find("lookups")
    if parent is None:
        return out
    for node in parent.findall("lookup"):
        instruction = _text(node, "instruction") or ""
        lookup = {
            "id": node.get("id"),
            "rcid": node.get("RCID"),
            "object_class": node.get("name"),
            "type": _text(node, "type"),
            "display_priority": _text(node, "disp-prio"),
            "radar_priority": _text(node, "radar-prio"),
            "table_name": _text(node, "table-name"),
            "display_category": _text(node, "display-cat"),
            "comment": _text(node, "comment"),
            "attrib_codes": [child.text for child in node.findall("attrib-code") if child.text],
            "instruction": instruction,
            "instruction_tokens": _tokens(instruction),
        }
        assets = set(_lookup_asset_names(instruction))
        assets.update(
            legacy
            for legacy in CANONICAL_ASSET_ALIASES
            if legacy in instruction
        )
        for asset in assets:
            canonical_asset = _canonical_asset(asset)
            clean_lookup = _canonicalize_legacy_value({
                **lookup,
                "instruction": _repair_s52_instruction(instruction),
                "instruction_tokens": _tokens(_repair_s52_instruction(instruction) or ""),
            })
            out[asset].append(clean_lookup)
            if canonical_asset != asset:
                out[canonical_asset].append(clean_lookup)
    return out


def _master_by_asset() -> dict[str, dict]:
    rows: dict[str, dict] = {}
    for row in _read_json(MASTER).get("rows", []):
        asset = row["asset"]
        clean_row = _canonicalize_legacy_value(row)
        rows[asset] = clean_row
        canonical = _canonical_asset(asset)
        if canonical != asset:
            rows[canonical] = clean_row
    return rows


def _triad_by_asset() -> dict[str, dict]:
    return {row["id"]: row for row in _read_json(TRIAD_PACK).get("rows", [])}


def _routing_by_asset() -> dict[str, dict]:
    if not ROUTING_BATCH98.exists():
        return {}
    rows: dict[str, dict] = {}
    for row in _read_json(ROUTING_BATCH98).get("records", []):
        asset = row["asset"]
        clean_row = _canonicalize_legacy_value(row)
        rows[asset] = clean_row
        canonical = _canonical_asset(asset)
        if canonical != asset:
            rows[canonical] = clean_row
    return rows


def _judge_verdicts() -> dict[str, list[dict]]:
    verdicts: dict[str, list[dict]] = defaultdict(list)
    paths = [
        *sorted(CATALOG.glob("triad_judge_batch_001*.json")),
        *sorted(CATALOG.glob("standard_judge_batch_*.json")),
    ]
    for path in paths:
        data = _read_json(path)
        for verdict in data.get("verdicts", []):
            asset = verdict.get("symbol_id")
            if asset:
                verdicts[_canonical_asset(asset)].append(_canonicalize_legacy_value({
                    "batch": path.stem,
                    "pass": verdict.get("pass"),
                    "confidence": verdict.get("confidence"),
                    "observed": verdict.get("observed"),
                    "expected": verdict.get("expected"),
                    "judge_comments": verdict.get("judge_comments"),
                    "required_change": verdict.get("required_change"),
                    "safety_reason_codes": verdict.get("safety_reason_codes", []),
                    "source_refs_used": verdict.get("source_refs_used", []),
                }))
    return verdicts


def _shape_judge_verdicts() -> dict[str, list[dict]]:
    verdicts: dict[str, list[dict]] = defaultdict(list)
    for path in sorted(CATALOG.glob("standard_shape_judge_batch_*.json")):
        data = _read_json(path)
        source_batch = data.get("source_batch")
        for verdict in data.get("verdicts", []):
            asset = verdict.get("symbol_id")
            if asset:
                passed = verdict.get("shape_semantic_pass")
                if passed is None:
                    passed = verdict.get("pass")
                verdicts[_canonical_asset(asset)].append(_canonicalize_legacy_value({
                    "batch": path.stem,
                    "source_batch": source_batch,
                    "pass": passed,
                    "confidence": verdict.get("confidence"),
                    "observed_shape": verdict.get("observed_shape"),
                    "expected_shape": verdict.get("expected_shape"),
                    "wrong_family_if_any": verdict.get("wrong_family_if_any"),
                    "judge_comments": verdict.get("judge_comments"),
                    "required_change": verdict.get("required_change"),
                    "safety_reason_codes": verdict.get("safety_reason_codes", []),
                    "source_refs_used": verdict.get("source_refs_used", []),
                }))
    return verdicts


def _latest_judge_state(asset: str, verdicts: dict[str, list[dict]]) -> dict | None:
    items = verdicts.get(asset) or []
    return items[-1] if items else None


def _lookup_with_alias(mapping: dict[str, dict], source_asset: str, canonical_asset: str) -> dict:
    for key in _asset_keys(source_asset, canonical_asset):
        if key in mapping:
            return mapping[key]
    return {}


def _latest_judge_state_with_alias(
    source_asset: str,
    canonical_asset: str,
    verdicts: dict[str, list[dict]],
) -> dict | None:
    for key in _asset_keys(source_asset, canonical_asset):
        latest = _latest_judge_state(key, verdicts)
        if latest:
            return latest
    return None


def _display_name(source_asset: str, canonical_asset: str, trow: dict, mrow: dict, defs: dict[str, list[dict]]) -> str | None:
    if canonical_asset != source_asset:
        definition = (defs.get(canonical_asset) or [{}])[0]
        return definition.get("description") or mrow.get("description") or canonical_asset
    return trow.get("name")


def _defs_with_aliases(defs: dict[str, list[dict]], source_asset: str, canonical_asset: str) -> list[dict]:
    for key in _asset_keys(source_asset, canonical_asset):
        if defs.get(key):
            return _canonicalize_legacy_value(defs[key])
    return []


def _lookups_with_aliases(lookups: dict[str, list[dict]], source_asset: str, canonical_asset: str) -> list[dict]:
    items: list[dict] = []
    for key in _asset_keys(source_asset, canonical_asset):
        items.extend(lookups.get(key, []))
    unique: list[dict] = []
    seen: set[str] = set()
    for item in items:
        marker = json.dumps(item, sort_keys=True)
        if marker in seen:
            continue
        seen.add(marker)
        unique.append(_canonicalize_legacy_value(item))
    return unique


def _latest_current_judge_state(row: dict, verdicts: dict[str, list[dict]]) -> dict | None:
    canonical_asset = _canonical_asset(row["id"])
    items = []
    for key in _asset_keys(row["id"], canonical_asset):
        items.extend(verdicts.get(key, []))
    source_batch = row.get("asset", {}).get("source_batch")
    source_svg = row.get("asset", {}).get("source_svg")
    if source_batch or source_svg:
        current = []
        for item in items:
            refs = " ".join(str(ref) for ref in item.get("source_refs_used", []))
            if source_batch and source_batch in refs:
                current.append(item)
            elif source_svg and source_svg in refs:
                current.append(item)
        return current[-1] if current else None
    return items[-1] if items else None


def _latest_current_shape_judge_state(row: dict, verdicts: dict[str, list[dict]]) -> dict | None:
    canonical_asset = _canonical_asset(row["id"])
    items = []
    for key in _asset_keys(row["id"], canonical_asset):
        items.extend(verdicts.get(key, []))
    source_batch = row.get("asset", {}).get("source_batch")
    if source_batch:
        current = [item for item in items if item.get("source_batch") == source_batch]
        return current[-1] if current else None
    return items[-1] if items else None


def _candidate_source_judge(row: dict) -> str | None:
    source_batch = row.get("asset", {}).get("source_batch")
    if not source_batch:
        return None
    path = ROOT / source_batch
    if not path.exists():
        return None
    data = _read_json(path)
    asset = row.get("id")
    asset_keys = set(_asset_keys(asset, _canonical_asset(asset)))
    for symbol in data.get("symbols", []):
        if symbol.get("asset") in asset_keys and symbol.get("source_judge"):
            return Path(symbol["source_judge"]).stem
    source_judge = data.get("source_judge")
    if not source_judge:
        return None
    return Path(source_judge).stem


def _candidate_status(row: dict, verdicts: dict[str, list[dict]], shape_verdicts: dict[str, list[dict]]) -> str:
    if not row.get("asset", {}).get("canonical"):
        return "no_helm_candidate"
    qa_state = row.get("qa", {}).get("visual_parity")
    repaired_state = qa_state in {"repaired_pending_judge_rerun", "repaired_pending_shape_rerun"}
    latest = _latest_judge_state_with_alias(row["id"], _canonical_asset(row["id"]), verdicts)
    latest_shape = _latest_current_shape_judge_state(row, shape_verdicts)
    if latest_shape:
        if not latest_shape.get("pass"):
            return "shape_fail_repair_queue"
    if latest:
        if repaired_state and not latest.get("pass") and _candidate_source_judge(row) == latest.get("batch"):
            return "repaired_pending_judge_rerun"
        return "judge_pass_pending_final_approval" if latest.get("pass") else "judge_fail_repair_queue"
    if qa_state == "repaired_pending_shape_rerun":
        if latest_shape:
            return "shape_pass_pending_visual_rerun" if latest_shape.get("pass") else "shape_fail_repair_queue"
        return "repaired_pending_shape_rerun"
    if latest_shape and latest_shape.get("pass") and qa_state == "repaired_pending_judge_rerun":
        return "shape_pass_pending_visual_rerun"
    if qa_state == "repaired_pending_judge_rerun":
        return "repaired_pending_judge_rerun"
    return "pending_judge"


CHART1_BLOCKING_REASON_CODES = {
    "generic_placeholder_body",
    "no_exact_symbol_crop_final_pass_forbidden",
    "wrong_silhouette_or_symbol_body",
    "wrong_shape",
}


def _chart1_parity_blocker(master_row: dict, candidate_status: str) -> dict | None:
    """Prevent broad/multi-symbol Chart 1 failures from masquerading as visual passes."""
    if candidate_status != "judge_pass_pending_final_approval":
        return None
    reason_codes = set(master_row.get("chart1_reason_codes") or [])
    blocking_codes = sorted(reason_codes & CHART1_BLOCKING_REASON_CODES)
    exact_pass_forbidden = (
        "no_exact_symbol_crop_final_pass_forbidden" in reason_codes
        and master_row.get("visual_approval") != "approved"
        and master_row.get("chart1_gate_status") in {
            "class_reference_only",
            "multi_symbol_reference_only",
        }
    )
    if not (
        master_row.get("chart1_verdict") == "fail" and blocking_codes
    ) and not exact_pass_forbidden:
        return None
    return {
        "status": "blocked_by_chart1_parity_gate",
        "chart1_verdict": master_row.get("chart1_verdict"),
        "chart1_gate_status": master_row.get("chart1_gate_status"),
        "chart1_evidence_status": master_row.get("chart1_evidence_status"),
        "chart1_crop_id": master_row.get("chart1_crop_id"),
        "chart1_mappings_int1_refs": master_row.get("chart1_mappings_int1_refs") or [],
        "reason_codes": blocking_codes or ["no_exact_symbol_crop_final_pass_forbidden"],
        "required_change": (
            "Do not treat the earlier automated visual pass as final-pass eligible. "
            "Redraw against exact Chart No.1/OpenCPN/S-52 witness geometry, preserving "
            "silhouette, band count/order, topmark/board details, and load-bearing colours; "
            "then rerun visual judge."
        ),
    }


def _condition_values(conditions: list[str], attr: str) -> list[str]:
    values: list[str] = []
    for condition in conditions:
        text = str(condition).upper()
        if not text.startswith(attr):
            continue
        values.extend(part for part in re.split(r"[,./]", text[len(attr):]) if part)
    return values


def _colour_tokens(record: dict) -> list[str]:
    values = _condition_values(record["s57_structure"].get("conditions", []), "COLOUR")
    colours = [S57_COLOURS.get(value, f"s57-colour-{value}") for value in values]
    if colours:
        return colours

    color_refs = [
        definition.get("color_ref") or ""
        for definition in record["opencpn_s52_spine"].get("definitions", [])
    ]
    refs = " ".join(color_refs).upper()
    candidates = [
        ("RED", "red"),
        ("GRN", "green"),
        ("YEL", "yellow"),
        ("WHT", "white"),
        ("BLK", "black"),
        ("MAG", "magenta"),
        ("BRN", "brown"),
        ("BLU", "blue"),
        ("GRY", "grey"),
        ("ORN", "orange"),
    ]
    return list(dict.fromkeys(token for needle, token in candidates if needle in refs))


def _colour_pattern(record: dict) -> str | None:
    values = _condition_values(record["s57_structure"].get("conditions", []), "COLPAT")
    if not values:
        return None
    return "; ".join(S57_PATTERNS.get(value, f"S-57 colour pattern {value}") for value in values)


def _shape_requirement(record: dict) -> str:
    asset = record["asset"].upper()
    text = f"{asset} {record.get('name') or ''}".lower()
    conditions = record["s57_structure"].get("conditions", [])
    object_class = (record["s57_structure"].get("object_class") or "").upper()

    boy_shapes = _condition_values(conditions, "BOYSHP")
    if boy_shapes:
        return "; ".join(BOY_SHAPES.get(value, f"S-57 buoy shape {value}") for value in boy_shapes)
    bcn_shapes = _condition_values(conditions, "BCNSHP")
    if bcn_shapes:
        return "; ".join(BCN_SHAPES.get(value, f"S-57 beacon shape {value}") for value in bcn_shapes)
    top_shapes = _condition_values(conditions, "TOPSHP")
    if top_shapes or asset.startswith(("TOPMAR", "TOPSHP")) or object_class == "TOPMAR":
        return "exact topmark silhouette/count/orientation from the references"
    if asset.startswith(("BOYCAN", "BCNCAN")) or "can buoy" in text:
        return "can/cylindrical buoy body"
    if asset.startswith(("BOYCON", "BCNCON")) or "conical" in text or "nun" in text:
        return "conical/nun buoy body"
    if asset.startswith(("BOYSPH", "BCNSPH")) or "spherical" in text:
        return "spherical buoy body"
    if asset.startswith(("BOYBAR", "BCNBAR")) or "barrel" in text:
        return "barrel buoy body"
    if asset.startswith(("BOYSPR", "BCNSTK")) or "spar" in text or "stake" in text:
        return "spar/stake vertical body"
    if asset.startswith(("BOYCAR", "BCNCAR")):
        return "cardinal aid body/topmark geometry; verify quadrant/topmark orientation"
    if asset.startswith("WRECKS"):
        return "recognized wreck symbol, not a generic decorative icon"
    if asset.startswith(("UWTROC", "WTROC")):
        return "recognized rock/underwater rock symbol, not a generic mountain or star"
    if asset.startswith("OBSTRN"):
        return "recognized obstruction hazard symbol"
    if asset.startswith(("ACH", "ANC")) or "anchor" in text:
        return "anchor/anchorage symbol"
    if asset.startswith(("MORFAC", "BOYMOR")) or "mooring" in text:
        return "mooring facility/buoy symbol"
    if asset.startswith(("HRBFAC", "SMCFAC")):
        return "harbour-service/facility symbol; preserve letter/icon convention where references use it"
    if asset.startswith("LIGHTS"):
        return "light symbol with the correct color cue and no invented hazard silhouette"
    if asset.startswith("BCN"):
        return "beacon/daymark symbol matching the S-57 beacon family"
    if asset.startswith("BOY"):
        return "buoy symbol matching the S-57 buoy family"
    return "symbol silhouette must match the strongest S-101/OpenCPN/Aqua Map reference"


def _use_case(record: dict) -> str:
    object_class = (record["s57_structure"].get("object_class") or "").upper()
    return OBJECT_USE.get(object_class, record.get("name") or "nautical chart symbol")


def _semantic_brief(record: dict) -> dict:
    colours = _colour_tokens(record)
    pattern = _colour_pattern(record)
    shape = _shape_requirement(record)
    use_case = _use_case(record)
    name = record.get("name") or record["asset"]
    colour_text = ", ".join(colours) if colours else "reference-defined"
    pattern_text = f" with {pattern}" if pattern else ""
    brief = (
        f"{record['asset']} is {name}. It is used as a {use_case}. "
        f"Required geometry: {shape}. Required colours: {colour_text}{pattern_text}."
    )
    invariants = [
        "Preserve the S-57/S-52 symbol class; do not substitute a different buoy/beacon/topmark/hazard family.",
        "Preserve load-bearing colours and colour order.",
        "Preserve topmark count/orientation and band pattern when present.",
        "Use provider images as semantic/shape witnesses; Helm output remains generated-owned artwork.",
    ]
    if "can/cylindrical" in shape:
        invariants.append("Can/cylindrical buoy rows must not be rendered as conical/nun buoy rows.")
    if "conical/nun" in shape:
        invariants.append("Conical/nun buoy rows must not be rendered as can/cylindrical buoy rows.")
    return {
        "brief": brief,
        "use_case": use_case,
        "required_shape": shape,
        "required_colours": colours,
        "unique_required_colours": list(dict.fromkeys(colours)),
        "colour_pattern": pattern,
        "safety_invariants": invariants,
    }


def _repair_queue_item(record: dict, latest: dict | None, latest_shape: dict | None) -> dict | None:
    status = record["helm_candidate"]["candidate_status"]
    if status in {"repaired_pending_judge_rerun", "repaired_pending_shape_rerun", "shape_pass_pending_visual_rerun"}:
        return None
    if status == "shape_fail_repair_queue" and latest_shape:
        return {
            "asset": record["asset"],
            "source_table_id": record["source_table_id"],
            "status": "queued_for_shape_semantic_repair",
            "required_change": latest_shape.get("required_change"),
            "judge_comments": latest_shape.get("judge_comments"),
            "safety_reason_codes": latest_shape.get("safety_reason_codes", []),
            "semantic_brief": record["semantic_brief"],
            "return_to": "standard_semantic_shape_judge_queue",
        }
    if status == "chart1_fail_repair_queue":
        blocker = record.get("chart1_parity_gate") or {}
        return {
            "asset": record["asset"],
            "source_table_id": record["source_table_id"],
            "status": "queued_for_chart1_parity_repair",
            "required_change": blocker.get("required_change"),
            "judge_comments": (
                "Chart No.1 parity metadata blocks this row from final-pass eligibility "
                "despite an earlier automated visual pass."
            ),
            "safety_reason_codes": blocker.get("reason_codes", []),
            "semantic_brief": record["semantic_brief"],
            "chart1_parity_gate": blocker,
            "return_to": "standard_source_table_judge_queue",
        }
    if not latest or latest.get("pass"):
        return None
    return {
        "asset": record["asset"],
        "source_table_id": record["source_table_id"],
        "status": "queued_for_render_repair",
        "required_change": latest.get("required_change"),
        "judge_comments": latest.get("judge_comments"),
        "safety_reason_codes": latest.get("safety_reason_codes", []),
        "return_to": "standard_source_table_judge_queue",
    }


def _judge_packet(record: dict) -> dict:
    return {
        "status": "queued_for_one_symbol_llm_judge",
        "source_table_id": record["source_table_id"],
        "asset": record["asset"],
        "name": record["name"],
        "opencpn_s52_spine": record["opencpn_s52_spine"],
        "s57_structure": record["s57_structure"],
        "semantic_brief": record["semantic_brief"],
        "reference_providers": record["reference_providers"],
        "helm_candidate": record["helm_candidate"],
        "judge_contract": {
            "compare": "all provider reference images/metadata against Helm-owned candidate for this one row",
            "approval": "semantic visual parity only; final_approved remains false until promoted by the pipeline",
            "semantic_gate": "first confirm the candidate is the correct symbol class/shape/topmark/colour-order from semantic_brief; then judge visual style",
            "on_fail": "write critique with exact missing/wrong shape/color/cue and enqueue render repair for this row only",
            "output_fields": [
                "pass",
                "confidence",
                "observed",
                "expected",
                "judge_comments",
                "required_change",
                "safety_reason_codes",
                "source_refs_used",
            ],
        },
    }


def _semantic_judge_packet(record: dict) -> dict:
    return {
        "status": "queued_for_shape_semantic_judge",
        "source_table_id": record["source_table_id"],
        "asset": record["asset"],
        "name": record["name"],
        "semantic_brief": record["semantic_brief"],
        "s57_structure": record["s57_structure"],
        "opencpn_s52_spine": record["opencpn_s52_spine"],
        "reference_providers": record["reference_providers"],
        "helm_candidate": record["helm_candidate"],
        "judge_contract": {
            "compare": "semantic_brief plus S-57/S-52 metadata against provider references and Helm-owned candidate",
            "approval": "candidate uses the correct chart-symbol class, required geometry, topmark orientation/count, and colour order",
            "ignore": "minor Helm style differences, line polish, and final antialiasing unless they change semantics",
            "on_fail": "write exact shape-semantic mismatch and the required class/shape/color repair",
            "output_fields": [
                "shape_semantic_pass",
                "confidence",
                "observed_shape",
                "expected_shape",
                "wrong_family_if_any",
                "required_change",
                "safety_reason_codes",
            ],
        },
    }


def _routing_record(record: dict, route: dict, pre_routing_status: str) -> dict:
    return {
        "asset": record["asset"],
        "source_table_id": record["source_table_id"],
        "name": record.get("name"),
        "kind": record.get("kind"),
        "family": record.get("family"),
        "candidate_status": route["routing_bucket"],
        "pre_routing_candidate_status": pre_routing_status,
        "routing_bucket": route["routing_bucket"],
        "queue_policy": route["queue_policy"],
        "registry_target": route["registry_target"],
        "next_action": route["next_action"],
        "classification": route.get("classification"),
        "resolution": route.get("resolution"),
        "evidence_required": route.get("evidence_required", []),
        "excluded_from_normal_icon_art_queue": True,
        "semantic_brief": record["semantic_brief"],
        "s57_structure": record["s57_structure"],
        "opencpn_s52_spine": record["opencpn_s52_spine"],
        "reference_providers": record["reference_providers"],
        "helm_candidate": record["helm_candidate"],
        "judge": record.get("judge", {}).get("latest"),
        "chart1_parity_gate": record.get("chart1_parity_gate"),
    }


def build() -> dict:
    master = _master_by_asset()
    triad_rows = _triad_by_asset()
    routing_rows = _routing_by_asset()
    defs = _asset_defs()
    lookups = _lookups_by_asset()
    verdicts = _judge_verdicts()
    shape_verdicts = _shape_judge_verdicts()
    rows = []
    judge_queue = []
    semantic_judge_queue = []
    repair_queue = []
    routed_queue = []
    for source_asset in sorted(triad_rows):
        canonical_asset = _canonical_asset(source_asset)
        trow = triad_rows[source_asset]
        mrow = _lookup_with_alias(master, source_asset, canonical_asset)
        latest = _latest_judge_state_with_alias(source_asset, canonical_asset, verdicts)
        latest_shape = _latest_current_shape_judge_state(trow, shape_verdicts)
        source_table_id = f"opencpn-s52:{canonical_asset}"
        provider_refs = _canonicalize_legacy_value({
            "s101": trow["triad_refs"].get("s101", []),
            "aquamap": trow["triad_refs"].get("aquamap", []),
            "opencpn_render": trow["triad_refs"].get("opencpn", []),
        })
        s52_instruction = _repair_s52_instruction(
            mrow.get("s52_instruction") or trow.get("s57", {}).get("instruction")
        )
        definitions = _defs_with_aliases(defs, source_asset, canonical_asset)
        lookup_rows = _lookups_with_aliases(lookups, source_asset, canonical_asset)
        record = {
            "source_table_id": source_table_id,
            "asset": canonical_asset,
            "name": _display_name(source_asset, canonical_asset, trow, mrow, defs),
            "kind": trow.get("kind"),
            "family": trow.get("family"),
            "s57_structure": {
                "object_class": mrow.get("s57_object_class") or trow.get("s57", {}).get("object_class"),
                "conditions": mrow.get("s57_conditions") or trow.get("s57", {}).get("conditions") or [],
                "lookup_id": mrow.get("s57_lookup_id"),
                "lookup_rcid": mrow.get("s57_rcid"),
                "s52_instruction": s52_instruction,
            },
            "opencpn_s52_spine": {
                "definitions": definitions,
                "lookups": lookup_rows,
                "definition_count": len(definitions),
                "lookup_count": len(lookup_rows),
            },
            "reference_providers": provider_refs,
            "provider_coverage": {
                "s101": bool(provider_refs["s101"]),
                "aquamap": bool(provider_refs["aquamap"]),
                "opencpn": bool(provider_refs["opencpn_render"]),
            },
            "helm_candidate": {
                "canonical_svg": trow.get("asset", {}).get("canonical"),
                "renders": trow.get("asset", {}).get("renders", {}),
                "source": trow.get("asset", {}).get("source"),
                "source_batch": trow.get("asset", {}).get("source_batch"),
                "source_svg": trow.get("asset", {}).get("source_svg"),
                "origin": trow.get("provenance", {}).get("origin"),
                "style_contract": "helm-openbridge-navigation-v1",
                "qa": trow.get("qa", {}),
                "candidate_status": _candidate_status(trow, verdicts, shape_verdicts),
            },
            "chart1_parity_gate": None,
            "semantic_brief": {},
            "semantic_shape_judge": {
                "latest": latest_shape,
                "history": _lookups_with_aliases(shape_verdicts, source_asset, canonical_asset),
            },
            "judge": {
                "latest": latest,
                "history": _lookups_with_aliases(verdicts, source_asset, canonical_asset),
            },
            "repair_queue_item": None,
            "provenance": {
                "source_spine": "OpenCPN S-52 chartsymbols.xml metadata and local reference renders",
                "reference_art_policy": "S-101/Aqua Map/OpenCPN are reference witnesses; Helm canonical art is generated-owned SVG",
                "clean_ip_policy": "Do not import OpenCPN raster pixels, Aqua Map images, or S-101 bodies as canonical artwork unless cleared",
            },
        }
        chart1_blocker = _chart1_parity_blocker(mrow, record["helm_candidate"]["candidate_status"])
        if chart1_blocker:
            latest_current = _latest_current_judge_state(trow, verdicts)
            repaired_pending_visual_judge = (
                record["helm_candidate"]["qa"].get("visual_parity") == "repaired_pending_judge_rerun"
                and latest
                and latest.get("pass")
                and not latest_current
            )
            current_repair_passed = bool(
                record["helm_candidate"]["qa"].get("visual_parity") == "repaired_pending_judge_rerun"
                and latest_current
                and latest_current.get("pass")
                and any("chart1_crop:" in str(ref) for ref in latest_current.get("source_refs_used", []))
            )
            if repaired_pending_visual_judge:
                record["helm_candidate"]["candidate_status"] = "repaired_pending_judge_rerun"
            elif current_repair_passed:
                record["helm_candidate"]["candidate_status"] = "judge_pass_pending_final_approval"
            else:
                record["helm_candidate"]["candidate_status"] = "chart1_fail_repair_queue"
                record["chart1_parity_gate"] = chart1_blocker
        record["semantic_brief"] = _semantic_brief(record)
        route = routing_rows.get(source_asset) or routing_rows.get(canonical_asset)
        if route:
            pre_routing_status = record["helm_candidate"]["candidate_status"]
            record["batch98_routing"] = _routing_record(record, route, pre_routing_status)
            record["helm_candidate"]["pre_routing_candidate_status"] = pre_routing_status
            record["helm_candidate"]["candidate_status"] = route["routing_bucket"]
            record["repair_queue_item"] = None
            routed_queue.append(record["batch98_routing"])
            repair = None
        else:
            record["batch98_routing"] = None
            repair = _repair_queue_item(record, latest, latest_shape)
            record["repair_queue_item"] = repair
        record["repair_queue_item"] = repair
        record = _canonicalize_legacy_value(record)
        rows.append(record)
        if record["helm_candidate"]["canonical_svg"] and not route:
            judge_queue.append(_judge_packet(record))
            semantic_judge_queue.append(_semantic_judge_packet(record))
        if repair:
            repair_queue.append(repair)

    coverage = Counter()
    for row in rows:
        for key, value in row["provider_coverage"].items():
            if value:
                coverage[key] += 1
    status_counts = Counter(row["helm_candidate"]["candidate_status"] for row in rows)
    route_counts = Counter(row["batch98_routing"]["routing_bucket"] for row in rows if row.get("batch98_routing"))
    result = {
        "schema_version": 1,
        "generator": "forge.standard_source_table",
        "status": "normalized_source_table_routing_enforced",
        "summary": {
            "rows": len(rows),
            "judge_queue_rows": len(judge_queue),
            "repair_queue_rows": len(repair_queue),
            "routed_queue_rows": len(routed_queue),
            "s101_rows": coverage["s101"],
            "aquamap_rows": coverage["aquamap"],
            "opencpn_rows": coverage["opencpn"],
            "opencpn_definitions_total": sum(row["opencpn_s52_spine"]["definition_count"] for row in rows),
            "opencpn_lookup_links_total": sum(row["opencpn_s52_spine"]["lookup_count"] for row in rows),
            "candidate_status_counts": dict(sorted(status_counts.items())),
            "routing_bucket_counts": dict(sorted(route_counts.items())),
            "semantic_shape_judge_queue_rows": len(semantic_judge_queue),
        },
        "rows": rows,
        "judge_queue": judge_queue,
        "semantic_shape_judge_queue": semantic_judge_queue,
        "repair_queue": repair_queue,
        "routed_queue": routed_queue,
        "outputs": {
            "json": str(TABLE_JSON.relative_to(ROOT)),
            "csv": str(TABLE_CSV.relative_to(ROOT)),
            "markdown": str(TABLE_MD.relative_to(ROOT)),
            "judge_queue": str(JUDGE_QUEUE.relative_to(ROOT)),
            "semantic_shape_judge_queue": str(SEMANTIC_JUDGE_QUEUE.relative_to(ROOT)),
            "routed_queue": str(ROUTED_QUEUE.relative_to(ROOT)),
        },
    }
    _write_outputs(result)
    return result


def _write_outputs(result: dict) -> None:
    table_result = {key: value for key, value in result.items() if key != "semantic_shape_judge_queue"}
    TABLE_JSON.write_text(json.dumps(table_result, indent=2, sort_keys=True) + "\n")
    _write_csv(result["rows"])
    _write_md(result)
    OUT.mkdir(parents=True, exist_ok=True)
    JUDGE_QUEUE.write_text(json.dumps({
        "schema_version": 1,
        "status": "queued_for_standard_source_row_judging",
        "summary": result["summary"],
        "items": result["judge_queue"],
    }, indent=2, sort_keys=True) + "\n")
    SEMANTIC_JUDGE_QUEUE.write_text(json.dumps({
        "schema_version": 1,
        "status": "queued_for_shape_semantic_judging",
        "summary": result["summary"],
        "items": result["semantic_shape_judge_queue"],
    }, indent=2, sort_keys=True) + "\n")
    ROUTED_QUEUE.write_text(json.dumps({
        "schema_version": 1,
        "status": "routed_out_of_normal_icon_art_queue",
        "routing_source": str(ROUTING_BATCH98.relative_to(ROOT)),
        "summary": result["summary"],
        "items": result["routed_queue"],
    }, indent=2, sort_keys=True) + "\n")


def _write_csv(rows: list[dict]) -> None:
    fields = [
        "source_table_id",
        "asset",
        "name",
        "kind",
        "s57_object_class",
        "s57_conditions",
        "s52_instruction",
        "opencpn_definition_count",
        "opencpn_lookup_count",
        "opencpn_color_refs",
        "opencpn_reference_day",
        "s101_symbol_ids",
        "s101_paths",
        "aquamap_labels",
        "aquamap_paths",
        "semantic_brief",
        "required_shape",
        "required_colours",
        "colour_pattern",
        "helm_candidate_svg",
        "helm_candidate_day",
        "candidate_status",
        "pre_routing_candidate_status",
        "batch98_routing_bucket",
        "latest_judge_pass",
        "latest_required_change",
    ]
    with TABLE_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            defs = row["opencpn_s52_spine"]["definitions"]
            opencpn_refs = row["reference_providers"]["opencpn_render"]
            s101_refs = row["reference_providers"]["s101"]
            aquamap_refs = row["reference_providers"]["aquamap"]
            latest = row["judge"]["latest"] or {}
            writer.writerow({
                "source_table_id": row["source_table_id"],
                "asset": row["asset"],
                "name": row["name"],
                "kind": row["kind"],
                "s57_object_class": row["s57_structure"]["object_class"],
                "s57_conditions": ";".join(row["s57_structure"]["conditions"]),
                "s52_instruction": row["s57_structure"]["s52_instruction"],
                "opencpn_definition_count": row["opencpn_s52_spine"]["definition_count"],
                "opencpn_lookup_count": row["opencpn_s52_spine"]["lookup_count"],
                "opencpn_color_refs": ";".join(sorted({definition.get("color_ref") or "" for definition in defs if definition.get("color_ref")})),
                "opencpn_reference_day": ";".join(ref.get("day") or "" for ref in opencpn_refs),
                "s101_symbol_ids": ";".join(ref.get("symbol_id") or ref.get("label") or "" for ref in s101_refs),
                "s101_paths": ";".join(ref.get("path") or "" for ref in s101_refs),
                "aquamap_labels": ";".join(ref.get("label") or "" for ref in aquamap_refs),
                "aquamap_paths": ";".join(ref.get("path") or "" for ref in aquamap_refs),
                "semantic_brief": row["semantic_brief"]["brief"],
                "required_shape": row["semantic_brief"]["required_shape"],
                "required_colours": ";".join(row["semantic_brief"]["required_colours"]),
                "colour_pattern": row["semantic_brief"].get("colour_pattern") or "",
                "helm_candidate_svg": row["helm_candidate"]["canonical_svg"],
                "helm_candidate_day": row["helm_candidate"]["renders"].get("day"),
                "candidate_status": row["helm_candidate"]["candidate_status"],
                "pre_routing_candidate_status": row["helm_candidate"].get("pre_routing_candidate_status", ""),
                "batch98_routing_bucket": (row.get("batch98_routing") or {}).get("routing_bucket", ""),
                "latest_judge_pass": latest.get("pass"),
                "latest_required_change": latest.get("required_change"),
            })


def _write_md(result: dict) -> None:
    lines = [
        "# Standard Source Table",
        "",
        "Normalized S-52/S-57 source table for Icon Forge. OpenCPN/S-52 metadata is the spine; S-101, Aqua Map, and OpenCPN rendered references are provider witnesses; Helm SVGs and judge state attach to the same row.",
        "",
        "## Summary",
        "",
    ]
    for key, value in result["summary"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend([
        "",
        "## Outputs",
        "",
        f"- JSON: `{TABLE_JSON.relative_to(ROOT)}`",
        f"- CSV: `{TABLE_CSV.relative_to(ROOT)}`",
        f"- Judge queue: `{JUDGE_QUEUE.relative_to(ROOT)}`",
        f"- Semantic shape judge queue: `{SEMANTIC_JUDGE_QUEUE.relative_to(ROOT)}`",
        f"- Routed queue: `{ROUTED_QUEUE.relative_to(ROOT)}`",
        "",
        "## Process",
        "",
        "1. Normalize OpenCPN/S-52 definitions and lookup rows into `opencpn_s52_spine`.",
        "2. Map S-101, Aqua Map, and OpenCPN rendered references into `reference_providers`.",
        "3. Attach deterministic `semantic_brief` shape/use/colour requirements for judge and renderer.",
        "4. Attach Helm-owned SVG/renders and QA state in `helm_candidate`.",
        "5. Judge consumes the full row packet. Failures produce a row-scoped `repair_queue_item`.",
        "6. Renderer repairs only that row, regenerates the table, then the same judge packet runs again.",
        "7. Batch-98 routed rows are excluded from ordinary icon-art queues and sent to witness/manual/style/rule registries.",
    ])
    TABLE_MD.write_text("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args(argv)
    result = build()
    print(json.dumps({
        "status": result["status"],
        "summary": result["summary"],
        "outputs": result["outputs"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
