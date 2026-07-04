"""Build the Icon Forge reference-gap report.

Rows in this report have generated Helm candidates but cannot safely enter the
recognition judge because one or more required provider images are missing.

Run:
  python3 -m forge.standard_reference_gap_report
"""
from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
SOURCE_TABLE = CATALOG / "standard_source_table.json"
RECOGNITION_QUEUE = CATALOG / "standard_recognition_judge_queue.json"
OUT_JSON = CATALOG / "standard_reference_gap_report.json"
OUT_MD = CATALOG / "standard_reference_gap_report.md"
OUT_CSV = CATALOG / "standard_reference_gap_report.csv"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _provider_counts(row: dict) -> dict[str, int]:
    refs = row.get("reference_providers") or {}
    return {
        "opencpn_render": len(refs.get("opencpn_render") or []),
        "s101": len(refs.get("s101") or []),
        "aquamap": len(refs.get("aquamap") or []),
    }


def _gap_class(row: dict, blockers: list[str]) -> str:
    routing = row.get("batch98_routing") or {}
    bucket = routing.get("routing_bucket")
    if bucket in {"chart1_parity_witness_needed", "witness_needed_official_symbol"}:
        return "routed_witness_needed"
    if bucket == "manual_policy_exception":
        return "routed_manual_exception"
    if bucket == "style_primitive_registry":
        return "routed_style_primitive"
    if bucket == "portrayal_rule_registry":
        return "routed_portrayal_rule"
    status = (row.get("helm_candidate") or {}).get("candidate_status")
    if status == "judge_fail_repair_queue":
        return "repair_queue_needs_reference"
    if "no_reference_images" in blockers:
        return "candidate_blocked_no_reference_images"
    return "candidate_blocked_other"


def _expected_action(row: dict, blockers: list[str]) -> str:
    routing = row.get("batch98_routing") or {}
    if routing.get("next_action"):
        resolution = routing.get("resolution")
        if resolution:
            return f"{routing['next_action']}: {resolution}"
        return routing["next_action"]
    repair = row.get("repair_queue_item") or {}
    if repair.get("required_change"):
        return repair["required_change"]
    semantic = row.get("semantic_brief") or {}
    shape = semantic.get("required_shape") or "reference-defined symbol"
    colours = ", ".join(semantic.get("required_colours") or []) or "reference-defined colours"
    if "no_reference_images" in blockers:
        return (
            f"Attach or generate a tight reference image for {row['asset']} before recognition judging; "
            f"candidate shape contract is {shape}; colours are {colours}."
        )
    return f"Resolve blockers before recognition judging: {', '.join(blockers)}."


def build() -> dict:
    table = _read_json(SOURCE_TABLE)
    queue = _read_json(RECOGNITION_QUEUE)
    rows_by_asset = {row["asset"]: row for row in table["rows"]}
    gaps = []
    for packet in queue.get("packets", []):
        blockers = list(packet.get("blockers") or [])
        if "no_reference_images" not in blockers:
            continue
        row = rows_by_asset[packet["asset"]]
        helm = row.get("helm_candidate") or {}
        semantic = row.get("semantic_brief") or {}
        refs = _provider_counts(row)
        gaps.append({
            "asset": row["asset"],
            "name": row.get("name") or "",
            "family": row.get("family") or "",
            "kind": row.get("kind") or "",
            "gap_class": _gap_class(row, blockers),
            "routing_bucket": (row.get("batch98_routing") or {}).get("routing_bucket"),
            "blockers": blockers,
            "candidate_status": helm.get("candidate_status"),
            "source_batch": helm.get("source_batch"),
            "canonical_svg": helm.get("canonical_svg"),
            "required_shape": semantic.get("required_shape") or "",
            "required_colours": semantic.get("required_colours") or [],
            "provider_counts": refs,
            "s57_conditions": (row.get("s57_structure") or {}).get("conditions") or [],
            "s52_instruction": (row.get("s57_structure") or {}).get("s52_instruction") or "",
            "expected_action": _expected_action(row, blockers),
        })

    gap_counts: dict[str, int] = {}
    for gap in gaps:
        gap_counts[gap["gap_class"]] = gap_counts.get(gap["gap_class"], 0) + 1
    result = {
        "schema_version": "iconforge.standard_reference_gap_report.v1",
        "status": "reference_gap_report_written",
        "summary": {
            "source_table_rows": table.get("summary", {}).get("rows"),
            "recognition_packets": queue.get("summary", {}).get("packets"),
            "reference_gap_rows": len(gaps),
            "gap_class_counts": gap_counts,
        },
        "rows": gaps,
        "outputs": {
            "json": str(OUT_JSON.relative_to(ROOT)),
            "markdown": str(OUT_MD.relative_to(ROOT)),
            "csv": str(OUT_CSV.relative_to(ROOT)),
        },
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    _write_csv(gaps)
    _write_md(result)
    return result


def _write_csv(rows: list[dict]) -> None:
    fields = [
        "asset",
        "gap_class",
        "routing_bucket",
        "candidate_status",
        "source_batch",
        "required_shape",
        "required_colours",
        "blockers",
        "opencpn_refs",
        "s101_refs",
        "aquamap_refs",
        "expected_action",
    ]
    with OUT_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            counts = row["provider_counts"]
            writer.writerow({
                "asset": row["asset"],
                "gap_class": row["gap_class"],
                "routing_bucket": row.get("routing_bucket") or "",
                "candidate_status": row["candidate_status"],
                "source_batch": row["source_batch"],
                "required_shape": row["required_shape"],
                "required_colours": ";".join(row["required_colours"]),
                "blockers": ";".join(row["blockers"]),
                "opencpn_refs": counts["opencpn_render"],
                "s101_refs": counts["s101"],
                "aquamap_refs": counts["aquamap"],
                "expected_action": row["expected_action"],
            })


def _write_md(result: dict) -> None:
    lines = [
        "# Standard Reference Gap Report",
        "",
        "Rows here have Helm SVG candidates but are blocked from recognition judging because usable reference images are missing.",
        "",
        "## Summary",
        "",
        f"- source_table_rows: `{result['summary']['source_table_rows']}`",
        f"- recognition_packets: `{result['summary']['recognition_packets']}`",
        f"- reference_gap_rows: `{result['summary']['reference_gap_rows']}`",
        "",
        "| Gap class | Count |",
        "| --- | ---: |",
    ]
    for gap_class, count in sorted(result["summary"]["gap_class_counts"].items()):
        lines.append(f"| `{gap_class}` | {count} |")
    lines.extend([
        "",
        "## Rows",
        "",
        "| Asset | Class | Routing bucket | Candidate status | Source batch | Shape | Colours | Expected action |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ])
    for row in result["rows"]:
        colours = ", ".join(row["required_colours"]) or "reference-defined"
        lines.append(
            f"| `{row['asset']}` | `{row['gap_class']}` | `{row.get('routing_bucket') or ''}` | `{row['candidate_status']}` | "
            f"`{row['source_batch']}` | {row['required_shape']} | {colours} | {row['expected_action']} |"
        )
    OUT_MD.write_text("\n".join(lines) + "\n")


def main() -> int:
    result = build()
    print(json.dumps({"status": result["status"], "summary": result["summary"], "outputs": result["outputs"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
