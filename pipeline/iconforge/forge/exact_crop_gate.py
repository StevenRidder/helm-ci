"""Build the FORGE-14 exact Chart No.1 crop gate.

This report is intentionally stricter than the source registry. It only treats
an asset as approved when the current Chart No.1 parity report has exact crop
evidence and the verifier passed. Broad class panels, multi-symbol panels,
S-101 SVGs, and Commons SVGs are useful references/candidates, but they cannot
stand in for exact Chart No.1 crop parity.

Run:  python -m forge.exact_crop_gate
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHART1_REPORT = ROOT / "out" / "chart1_parity" / "report.json"
HARD_PILE = ROOT / "out" / "chart1_parity" / "hard_pile.json"
EXHAUSTIVE = ROOT / "catalog" / "exhaustive_symbol_inventory.json"
CROSSWALK = ROOT / "catalog" / "s52_s57_s101_crosswalk.json"
OUT = ROOT / "out" / "forge14_exact_crop_gate"

STATUS_TAXONOMY = {
    "exact_crop_approved": "Exact Chart No.1 crop exists and the strict visual verifier passed.",
    "exact_crop_failed_verifier": "Exact Chart No.1 crop exists, but rendered SVG still failed strict parity.",
    "commons_pd_candidate_needs_review": "Public-domain/CC0 Commons candidate exists; it needs semantic and visual QA before promotion.",
    "class_reference_only": "Only a broad Chart No.1 class-panel crop is available; final approval is forbidden.",
    "multi_symbol_reference_only": "Only a Chart No.1 panel containing multiple symbols is available; exact crop isolation is still required.",
    "license_blocked_reference_only": "S-101 or other external art is mapped but remains reference-only until license/permission clears.",
    "manual_exception": "The row needs human/counsel/domain review before generation or promotion.",
    "missing_exact_crop": "No exact Chart No.1 crop, approved external candidate, or accepted manual exception is available.",
}

STRICT_INVARIANTS = {
    "cardinal": [
        "north/east/south/west topmark orientation must match the S-57/S-52 asset",
        "black/yellow band order must match the target cardinal quadrant",
        "sibling discrimination must reject rotated or flipped cones",
    ],
    "lateral": [
        "region A/B red/green semantics must match the source catalog row",
        "can/cone/pillar/spar body silhouette must match Chart No.1",
        "topmark, if present, must agree with the lateral sibling",
    ],
    "safe_water": [
        "red/white vertical stripe semantics must be preserved",
        "sphere/topmark and body silhouette must not collapse into a generic buoy",
    ],
    "isolated_danger": [
        "black/red banding must remain distinct from cardinal marks",
        "paired-sphere topmark must be present where required",
    ],
    "special": [
        "yellow body/topmark semantics must survive day/dusk/night palette rendering",
        "special-purpose siblings must not reuse lateral or safe-water colors",
    ],
    "topmark": [
        "standalone topmark glyphs must not be confused with complete beacon/buoy symbols",
        "triangle/circle/cross/X/board/cube silhouettes must match their TOPSHP mapping",
    ],
    "beacon": [
        "fixed beacon/daymark/stake/tower body must not degrade to a generic placeholder",
        "topmark and colour semantics must match the attached beacon class",
    ],
}


def _read_json(path: Path) -> dict | list:
    return json.loads(path.read_text())


def _ensure_chart1_report() -> dict:
    if not CHART1_REPORT.exists() or not HARD_PILE.exists():
        from . import chart1_parity

        rc = chart1_parity.main([])
        if rc != 0:
            raise RuntimeError("chart1 parity report generation failed")
    return _read_json(CHART1_REPORT)


def _asset_map(path: Path) -> dict[str, dict]:
    data = _read_json(path)
    return {row["s52"]["asset"]: row for row in data["rows"]}


def _gate_rows(report: dict) -> list[dict]:
    return [row for row in report["rows"] if row["reference_evidence_status"] != "out_of_scope"]


def _status(row: dict, inventory: dict, crosswalk: dict) -> str:
    evidence = row["reference_evidence_status"]
    if evidence == "exact_symbol_crop":
        if row["final_approval"]:
            return "exact_crop_approved"
        return "exact_crop_failed_verifier"
    if evidence == "class_panel_reference":
        if inventory.get("status") == "external_pd_candidate":
            return "commons_pd_candidate_needs_review"
        return "class_reference_only"
    if evidence == "multi_symbol_reference":
        if inventory.get("status") == "external_pd_candidate":
            return "commons_pd_candidate_needs_review"
        if inventory.get("status") == "license_blocked" or crosswalk.get("s101", {}).get("exact_symbol_match"):
            return "license_blocked_reference_only"
        return "multi_symbol_reference_only"
    if evidence == "manual_exception":
        return "manual_exception"
    if inventory.get("status") == "external_pd_candidate":
        return "commons_pd_candidate_needs_review"
    if inventory.get("status") == "license_blocked":
        return "license_blocked_reference_only"
    return "missing_exact_crop"


def _next_action(status: str) -> str:
    return {
        "exact_crop_approved": "keep in approved set; preserve crop hash and visual-verifier evidence",
        "exact_crop_failed_verifier": "repair owned SVG against exact crop, then rerun strict visual parity",
        "commons_pd_candidate_needs_review": "review per-file license and semantic match, then compare visually before promotion",
        "class_reference_only": "create an isolated exact Chart No.1 crop or mark a reviewed manual exception",
        "multi_symbol_reference_only": "split the panel into exact symbol crops before any final approval",
        "license_blocked_reference_only": "use as mapping/QA reference only until counsel clears artwork reuse",
        "manual_exception": "record domain/counsel signoff or convert to exact crop evidence",
        "missing_exact_crop": "add source crosswalk and exact crop evidence before generation",
    }[status]


def _row_payload(row: dict, inventory: dict, crosswalk: dict) -> dict:
    status = _status(row, inventory, crosswalk)
    commons_candidates = inventory.get("commons", {}).get("public_domain_candidates", [])
    s101 = crosswalk.get("s101", {})
    chart1_refs = inventory.get("chart1_mappings_q_reference", [])
    return {
        "asset": row["asset"],
        "status": status,
        "next_action": _next_action(status),
        "chart1_class": row["chart1_class"],
        "description": row.get("description", ""),
        "reference_evidence_status": row["reference_evidence_status"],
        "reference_crop_id": row.get("reference_crop_id"),
        "reference_crop": row.get("reference_crop"),
        "reference_crop_box_unit": row.get("reference_crop_box_unit"),
        "reference_pages": row.get("reference_pages", []),
        "reference_section": row.get("reference_section"),
        "final_approval": row["final_approval"],
        "verdict": row["verdict"],
        "reason_codes": row.get("reason_codes", []),
        "strict_invariants": _invariants_for(row["asset"], row["chart1_class"]),
        "s57": inventory.get("s57", {}),
        "s101": {
            "exact_symbol_match": bool(s101.get("exact_symbol_match")),
            "feature_rule": s101.get("feature_rule"),
            "symbol_file": s101.get("symbol_file"),
            "license_status": s101.get("license_status", "license_pending_reference"),
        },
        "commons": {
            "public_domain_candidate_count": len(commons_candidates),
            "candidate_titles": [candidate["title"] for candidate in commons_candidates[:5]],
        },
        "chart1_mappings_q_reference": chart1_refs,
        "forbidden_sources": [
            "OpenCPN GPL rastersymbol sprites",
            "Chart 1 Mappings cropped/extracted artwork without explicit permission",
            "S-101 SVG bodies unless license/permission is cleared for canonical use",
        ],
    }


def _invariants_for(asset: str, chart1_class: str) -> list[str]:
    text = f"{asset} {chart1_class}".lower()
    groups: list[str] = []
    if "car" in asset.lower() or "cardinal" in text:
        groups.append("cardinal")
    if "lat" in asset.lower() or "lateral" in text:
        groups.append("lateral")
    if "saw" in asset.lower() or "safe" in text:
        groups.append("safe_water")
    if "isd" in asset.lower() or "isolated" in text:
        groups.append("isolated_danger")
    if "spp" in asset.lower() or "special" in text:
        groups.append("special")
    if asset.startswith("TOP") or "topmark" in text or "topshp" in text:
        groups.append("topmark")
    if asset.startswith("BCN") or "beacon" in text:
        groups.append("beacon")
    if not groups:
        groups.append("beacon" if asset.startswith("BCN") else "topmark" if asset.startswith("TOP") else "lateral")
    invariants: list[str] = []
    for group in groups:
        invariants.extend(STRICT_INVARIANTS[group])
    return sorted(set(invariants))


def build() -> dict:
    report = _ensure_chart1_report()
    inventory_by_asset = _asset_map(EXHAUSTIVE)
    crosswalk_by_asset = _asset_map(CROSSWALK)

    rows = []
    for row in sorted(_gate_rows(report), key=lambda item: item["asset"]):
        asset = row["asset"]
        rows.append(_row_payload(row, inventory_by_asset.get(asset, {}), crosswalk_by_asset.get(asset, {})))

    status_counts = Counter(row["status"] for row in rows)
    evidence_counts = Counter(row["reference_evidence_status"] for row in rows)
    final_approved = sum(1 for row in rows if row["final_approval"])
    hard_pile = [row for row in rows if not row["final_approval"]]

    summary = {
        "id": "forge14_exact_crop_gate",
        "status": "review_required" if hard_pile else "pass",
        "gate_assets": len(rows),
        "final_approved": final_approved,
        "hard_pile_entries": len(hard_pile),
        "chart1_report": "out/chart1_parity/report.json",
        "status_counts": dict(sorted(status_counts.items())),
        "evidence_counts": dict(sorted(evidence_counts.items())),
        "non_go_conditions": [
            "No row may pass without exact_symbol_crop evidence and final_approval=true.",
            "Class panels and multi-symbol panels are references only; they cannot approve canonical art.",
            "Commons public-domain candidates require per-file license review and visual/semantic QA before promotion.",
            "S-101 assets remain license_pending_reference unless counsel or IHO permission clears canonical reuse.",
            "OpenCPN GPL raster sprites are forbidden as canonical artwork sources.",
        ],
    }
    output = {
        "schema_version": 1,
        "summary": summary,
        "status_taxonomy": STATUS_TAXONOMY,
        "strict_invariants": STRICT_INVARIANTS,
        "rows": rows,
    }

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report.json").write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    (OUT / "hard_pile.json").write_text(json.dumps(hard_pile, indent=2, sort_keys=True) + "\n")
    return output


def main() -> int:
    output = build()
    summary = output["summary"]
    print(f"FORGE-14 exact crop gate: {summary['status']}")
    print(f"gate assets: {summary['gate_assets']}")
    print(f"final approved: {summary['final_approved']}")
    print(f"hard pile: {summary['hard_pile_entries']}")
    print(f"report: {OUT / 'report.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
