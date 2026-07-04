"""Attach truthful witness evidence for the remaining blocked rows.

Batch 100 is a witness-resolution ledger. It does not approve art, and it does
not treat a related provider symbol as an exact crop. The goal is to preserve
the useful evidence while keeping the five remaining rows blocked until they
have a tight per-symbol witness or an explicit manual exception.

Run:
  python3 -m forge.standard_witness_resolution_batch100
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
WITNESS_BATCH98 = CATALOG / "witness_needed_batch98.json"
ROUTED_QUEUE = CATALOG / "standard_routed_queue.json"
CHART1_PARITY = ROOT / "pilots" / "chart1_visual_parity.json"
OUT_JSON = CATALOG / "standard_witness_resolution_batch100.json"
OUT_CSV = CATALOG / "standard_witness_resolution_batch100.csv"
OUT_MD = CATALOG / "standard_witness_resolution_batch100.md"


def _ref(path: str, role: str, status: str, note: str, related_asset: str | None = None) -> dict:
    return {
        "path": path,
        "role": role,
        "status": status,
        "related_asset": related_asset,
        "note": note,
    }


WITNESS_PLANS = {
    "BCNCON81": {
        "resolution_status": "equivalent_family_witness_attached_not_exact",
        "remaining_blocker": "no_exact_symbol_witness",
        "promotion_ready": False,
        "manual_exception_allowed": True,
        "attached_references": [
            _ref(
                "out/source_variant_matrix/renders/BCNCON81/chart1_parity_reference_crop_1.png",
                "broad_chart1_crop",
                "multi_symbol_reference",
                "Broad beacon/dayboard/stake/tower crop; useful class evidence, not an exact BCNCON81 crop.",
            ),
            _ref(
                "out/source_variant_matrix/renders/BCNCON81/chart1_mappings_symbol_reference_1.png",
                "chart1_mapping_snippet",
                "reference_only_not_canonical_artwork",
                "Chart No.1 mapping snippet attached to BCNCON81; not enough alone to call final visual parity.",
            ),
            _ref(
                "out/source_variant_matrix/renders/BCNCON81/chart1_mappings_symbol_reference_2.png",
                "chart1_mapping_snippet",
                "reference_only_not_canonical_artwork",
                "Additional Chart No.1 mapping snippet for class/sibling context.",
            ),
            _ref(
                "out/source_variant_matrix/renders/BCNCON81/chart1_mappings_symbol_reference_3.png",
                "chart1_mapping_snippet",
                "reference_only_not_canonical_artwork",
                "Additional Chart No.1 mapping snippet for class/sibling context.",
            ),
            _ref(
                "out/source_variant_matrix/renders/BCNCON81/chart1_mappings_symbol_reference_4.png",
                "chart1_mapping_snippet",
                "reference_only_not_canonical_artwork",
                "Additional Chart No.1 mapping snippet for class/sibling context.",
            ),
            _ref(
                "out/source_variant_matrix/renders/BCNSPP13/opencpn_s52_reference_render_1.png",
                "related_opencpn_family_witness",
                "comparison_reference_not_exact",
                "Related BCNSPP witness for special-purpose beacon family, not BCNCON81 exact evidence.",
                "BCNSPP13",
            ),
            _ref(
                "out/source_variant_matrix/renders/BCNSPP13/s101_portrayal_catalogue_svg_1.png",
                "related_s101_family_witness",
                "license_pending_reference_not_canonical",
                "Related S-101 BCNSPP witness; mapping/sibling evidence only.",
                "BCNSPP13",
            ),
            _ref(
                "out/source_variant_matrix/renders/BCNSPP21/opencpn_s52_reference_render_1.png",
                "related_opencpn_family_witness",
                "comparison_reference_not_exact",
                "Second related BCNSPP witness for family contrast.",
                "BCNSPP21",
            ),
            _ref(
                "out/source_variant_matrix/renders/BCNSPP21/s101_portrayal_catalogue_svg_1.png",
                "related_s101_family_witness",
                "license_pending_reference_not_canonical",
                "Second related S-101 BCNSPP witness for family contrast.",
                "BCNSPP21",
            ),
            _ref(
                "reference_sources/aquamap_map_symbols/images/BCNSPPY1.png",
                "related_aquamap_family_witness",
                "copyrighted_visual_reference_not_canonical_art",
                "AquaMap beacon-special-purpose yellow reference; visual guidance only.",
                "BCNSPPY1",
            ),
            _ref(
                "reference_sources/aquamap_map_symbols/images/BCNSPPB1.png",
                "related_aquamap_family_witness",
                "copyrighted_visual_reference_not_canonical_art",
                "AquaMap beacon-special-purpose black reference; visual guidance only.",
                "BCNSPPB1",
            ),
        ],
        "next_action": "find or crop exact BCNCON81 one-symbol witness, or get explicit human manual exception before any promotion",
    },
    "boyspp50": {
        "resolution_status": "equivalent_family_witness_attached_not_exact",
        "remaining_blocker": "no_exact_symbol_witness",
        "promotion_ready": False,
        "manual_exception_allowed": True,
        "attached_references": [
            _ref(
                "out/source_variant_matrix/renders/boyspp50/chart1_parity_reference_crop_1.png",
                "broad_chart1_crop",
                "multi_symbol_reference",
                "Broad special-purpose buoy crop; useful class evidence, not exact boyspp50 evidence.",
            ),
            _ref(
                "out/source_variant_matrix/renders/BOYSPP11/opencpn_s52_reference_render_1.png",
                "related_opencpn_family_witness",
                "comparison_reference_not_exact",
                "Related BOYSPP witness for special-purpose buoy family.",
                "BOYSPP11",
            ),
            _ref(
                "out/source_variant_matrix/renders/BOYSPP11/s101_portrayal_catalogue_svg_1.png",
                "related_s101_family_witness",
                "license_pending_reference_not_canonical",
                "Related S-101 BOYSPP witness; mapping/sibling evidence only.",
                "BOYSPP11",
            ),
            _ref(
                "out/source_variant_matrix/renders/BOYSPP15/opencpn_s52_reference_render_1.png",
                "related_opencpn_family_witness",
                "comparison_reference_not_exact",
                "Second related BOYSPP witness for family contrast.",
                "BOYSPP15",
            ),
            _ref(
                "out/source_variant_matrix/renders/BOYSPP25/s101_portrayal_catalogue_svg_1.png",
                "related_s101_family_witness",
                "license_pending_reference_not_canonical",
                "Third related S-101 BOYSPP witness for family contrast.",
                "BOYSPP25",
            ),
            _ref(
                "reference_sources/aquamap_map_symbols/images/BOYSPPY1.png",
                "related_aquamap_family_witness",
                "copyrighted_visual_reference_not_canonical_art",
                "AquaMap yellow special-purpose buoy reference; visual guidance only.",
                "BOYSPPY1",
            ),
            _ref(
                "reference_sources/aquamap_map_symbols/images/BOYSPPB1.png",
                "related_aquamap_family_witness",
                "copyrighted_visual_reference_not_canonical_art",
                "AquaMap black special-purpose buoy reference; visual guidance only.",
                "BOYSPPB1",
            ),
        ],
        "next_action": "find exact boyspp50/BOYWTW witness or approve a manual exception before rendering final art",
    },
    "DANGER53": {
        "resolution_status": "related_symbol_witness_attached_not_exact",
        "remaining_blocker": "official_symbol_definition_or_exact_render_missing",
        "promotion_ready": False,
        "manual_exception_allowed": True,
        "attached_references": [
            _ref(
                "out/source_variant_matrix/renders/DANGER53/chart1_parity_reference_crop_1.png",
                "broad_chart1_crop",
                "out_of_scope",
                "ECDIS summary crop is not a tight DANGER53 symbol witness.",
            ),
            _ref(
                "out/source_variant_matrix/renders/DANGER51/opencpn_s52_reference_render_1.png",
                "related_opencpn_symbol_witness",
                "comparison_reference_not_exact",
                "Related DANGER51 render; useful danger-family evidence, not DANGER53 proof.",
                "DANGER51",
            ),
            _ref(
                "out/source_variant_matrix/renders/DANGER52/opencpn_s52_reference_render_1.png",
                "related_opencpn_symbol_witness",
                "comparison_reference_not_exact",
                "Related DANGER52 render; useful danger-family evidence, not DANGER53 proof.",
                "DANGER52",
            ),
            _ref(
                "out/source_variant_matrix/renders/DANGER53/open_source_icon_concept_1.png",
                "concept_icon",
                "permissive_icon_reference_needs_chart_semantic_review",
                "Concept cue only; cannot satisfy S-52 official DANGER53 witness requirement.",
            ),
        ],
        "next_action": "attach official DANGER53 symbol definition/render or keep in hard-pile for manual review",
    },
    "DGPS01DRFSTA01": {
        "resolution_status": "composite_parent_witness_attached_not_exact",
        "remaining_blocker": "exact_composite_witness_missing",
        "promotion_ready": False,
        "manual_exception_allowed": True,
        "attached_references": [
            _ref(
                "out/source_variant_matrix/renders/DGPS01DRFSTA01/chart1_parity_reference_crop_1.png",
                "broad_chart1_crop",
                "out_of_scope",
                "ECDIS summary crop is not a tight DGPS/radio-station composite witness.",
            ),
            _ref(
                "out/source_variant_matrix/renders/RDOSTA02/opencpn_s52_reference_render_1.png",
                "parent_opencpn_symbol_witness",
                "comparison_reference_not_exact",
                "Related radio-station parent symbol; does not prove the DGPS composite.",
                "RDOSTA02",
            ),
            _ref(
                "out/source_variant_matrix/renders/RDOSTA02/s101_portrayal_catalogue_svg_1.png",
                "parent_s101_symbol_witness",
                "license_pending_reference_not_canonical",
                "Related S-101 radio-station witness; mapping evidence only.",
                "RDOSTA02",
            ),
            _ref(
                "out/source_variant_matrix/renders/RDOSTA02/aquamap_map_symbols_1.png",
                "parent_aquamap_symbol_witness",
                "copyrighted_visual_reference_not_canonical_art",
                "AquaMap radio/radar station reference; visual guidance only.",
                "RDOSTA02",
            ),
            _ref(
                "reference_sources/aquamap_map_symbols/images/RadarStation1.png",
                "related_aquamap_concept",
                "copyrighted_visual_reference_not_canonical_art",
                "Radar station concept reference; not DGPS exact evidence.",
                "RadarStation1",
            ),
            _ref(
                "reference_sources/aquamap_map_symbols/images/RadioCallinPoint1.png",
                "related_aquamap_concept",
                "copyrighted_visual_reference_not_canonical_art",
                "Radio call-in concept reference; not DGPS exact evidence.",
                "RadioCallinPoint1",
            ),
        ],
        "next_action": "split composite into exact DGPS + RDOSTA witnesses or get human-approved composite spec",
    },
    "VEHTRF01": {
        "resolution_status": "unresolved_no_tight_witness",
        "remaining_blocker": "no_tight_visual_witness_found",
        "promotion_ready": False,
        "manual_exception_allowed": True,
        "attached_references": [
            _ref(
                "out/source_variant_matrix/renders/VEHTRF01/chart1_parity_reference_crop_1.png",
                "broad_chart1_crop",
                "out_of_scope",
                "ECDIS summary crop is not a tight vehicle-traffic symbol witness.",
            ),
            _ref(
                "out/source_variant_matrix/renders/VEHTRF01/helm_generated_draft_svg_1.png",
                "generated_candidate_to_reject_or_rework",
                "generated_pending_visual_parity",
                "Existing generated draft is retained for comparison only; it cannot be its own witness.",
            ),
        ],
        "next_action": "search standards/portrayal catalogues for exact VEHTRF01 witness; otherwise keep blocked for manual exception",
    },
}


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _chart1_by_asset() -> dict[str, dict]:
    return {row["asset"]: row for row in _read_json(CHART1_PARITY)["entries"]}


def _routed_by_asset() -> dict[str, dict]:
    return {row["asset"]: row for row in _read_json(ROUTED_QUEUE)["items"]}


def _missing_paths(refs: list[dict]) -> list[str]:
    return [ref["path"] for ref in refs if ref["path"] and not (ROOT / ref["path"]).exists()]


def _record(row: dict, routed: dict[str, dict], chart1: dict[str, dict]) -> dict:
    asset = row["asset"]
    plan = WITNESS_PLANS[asset]
    refs = plan["attached_references"]
    missing = _missing_paths(refs)
    if missing:
        raise FileNotFoundError(f"{asset} has missing witness paths: {missing}")
    parity = chart1.get(asset) or {}
    routed_row = routed.get(asset) or {}
    return {
        "asset": asset,
        "name": row.get("name"),
        "kind": row.get("kind"),
        "routing_bucket": row.get("routing_bucket"),
        "input_candidate_status": row.get("input_candidate_status"),
        "resolution_status": plan["resolution_status"],
        "remaining_blocker": plan["remaining_blocker"],
        "promotion_ready": plan["promotion_ready"],
        "final_approved": False,
        "manual_exception_allowed": plan["manual_exception_allowed"],
        "normal_icon_art_queue_allowed": False,
        "attached_reference_count": len(refs),
        "attached_references": refs,
        "chart1_parity": {
            "reference_crop": parity.get("reference_crop"),
            "reference_crop_id": parity.get("reference_crop_id"),
            "reference_crop_status": parity.get("reference_crop_status"),
            "reference_crop_sha256": parity.get("reference_crop_sha256"),
            "reference_pages": parity.get("reference_pages"),
            "chart1_class": parity.get("chart1_class"),
            "expected_shape": parity.get("expected_shape"),
            "expected_colors": parity.get("expected_colors"),
            "expected_topmark": parity.get("expected_topmark"),
            "final_pass_allowed": parity.get("final_pass_allowed"),
        },
        "s57_structure": row.get("s57_structure") or routed_row.get("s57_structure"),
        "semantic_brief": row.get("semantic_brief") or routed_row.get("semantic_brief"),
        "next_action": plan["next_action"],
        "safety_note": (
            "Do not promote this row from related/broad witnesses. It needs exact symbol evidence "
            "or explicit human manual exception before entering final approval."
        ),
    }


def build() -> dict:
    witness = _read_json(WITNESS_BATCH98)
    routed = _routed_by_asset()
    chart1 = _chart1_by_asset()
    rows = witness["records"]
    unexpected = sorted(set(WITNESS_PLANS) ^ {row["asset"] for row in rows})
    if unexpected:
        raise ValueError(f"batch100 witness set mismatch: {unexpected}")

    records = [_record(row, routed, chart1) for row in rows]
    records.sort(key=lambda item: item["asset"])
    counts = Counter(row["resolution_status"] for row in records)
    blocked = sum(1 for row in records if not row["promotion_ready"])

    result = {
        "schema_version": 1,
        "status": "standard_witness_resolution_batch100_written",
        "project": "vulkan",
        "task_id": "FORGE-15",
        "source": "catalog/witness_needed_batch98.json",
        "policy": (
            "Related OpenCPN/S-101/AquaMap/Chart No.1 evidence may guide repair, but only an exact "
            "symbol crop/render or explicit manual exception can unblock final promotion."
        ),
        "summary": {
            "total_witness_needed": len(records),
            "exact_witness_resolved": 0,
            "promotion_ready": sum(1 for row in records if row["promotion_ready"]),
            "still_blocked": blocked,
            "resolution_status_counts": dict(sorted(counts.items())),
            "attached_reference_count": sum(row["attached_reference_count"] for row in records),
        },
        "records": records,
    }

    OUT_JSON.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    _write_csv(records)
    _write_md(result)
    return result


def _write_csv(records: list[dict]) -> None:
    with OUT_CSV.open("w", newline="") as f:
        fields = [
            "asset",
            "name",
            "routing_bucket",
            "resolution_status",
            "remaining_blocker",
            "promotion_ready",
            "attached_reference_count",
            "next_action",
        ]
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for record in records:
            writer.writerow({key: record.get(key) for key in fields})


def _write_md(result: dict) -> None:
    summary = result["summary"]
    lines = [
        "# Standard Witness Resolution Batch 100",
        "",
        result["policy"],
        "",
        "## Summary",
        "",
        f"- Total witness-needed rows: {summary['total_witness_needed']}",
        f"- Exact witnesses resolved: {summary['exact_witness_resolved']}",
        f"- Promotion-ready rows: {summary['promotion_ready']}",
        f"- Still blocked: {summary['still_blocked']}",
        f"- Attached reference files: {summary['attached_reference_count']}",
        "",
        "## Rows",
        "",
        "| Asset | Status | References | Blocker | Next action |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for record in result["records"]:
        lines.append(
            "| {asset} | {status} | {refs} | {blocker} | {next_action} |".format(
                asset=record["asset"],
                status=record["resolution_status"],
                refs=record["attached_reference_count"],
                blocker=record["remaining_blocker"],
                next_action=record["next_action"],
            )
        )
    lines.append("")
    lines.append("## Evidence")
    lines.append("")
    for record in result["records"]:
        lines.append(f"### {record['asset']}")
        lines.append("")
        for ref in record["attached_references"]:
            related = f" related={ref['related_asset']}" if ref.get("related_asset") else ""
            lines.append(f"- `{ref['path']}` - {ref['role']} / {ref['status']}{related}. {ref['note']}")
        lines.append("")
    while lines and lines[-1] == "":
        lines.pop()
    OUT_MD.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="print JSON summary")
    args = parser.parse_args()
    result = build()
    if args.json:
        print(json.dumps(result["summary"], indent=2, sort_keys=True))
    else:
        print(
            "standard witness resolution batch 100: "
            f"{result['summary']['still_blocked']} still blocked, "
            f"{result['summary']['attached_reference_count']} refs attached"
        )


if __name__ == "__main__":
    main()
