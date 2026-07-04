"""Export row-scoped renderer repair queue from the standard source table.

Run:
  python -m forge.standard_repair_queue
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
SOURCE_TABLE = CATALOG / "standard_source_table.json"
REPAIR_JSON = CATALOG / "standard_repair_queue.json"
REPAIR_MD = CATALOG / "standard_repair_queue.md"


def build() -> dict:
    table = json.loads(SOURCE_TABLE.read_text())
    items = []
    routed_items = []
    routed_by_bucket: dict[str, list[dict]] = defaultdict(list)
    for row in table["rows"]:
        routing = row.get("batch98_routing")
        if routing:
            routed = {
                **routing,
                "name": row.get("name"),
                "kind": row.get("kind"),
                "family": row.get("family"),
                "semantic_brief": row.get("semantic_brief"),
                "s57_structure": row.get("s57_structure"),
                "opencpn_s52_spine": row.get("opencpn_s52_spine"),
                "reference_providers": row.get("reference_providers"),
                "helm_candidate": row.get("helm_candidate"),
                "judge": row.get("judge", {}).get("latest"),
            }
            routed_items.append(routed)
            routed_by_bucket[routing["routing_bucket"]].append(routed)
        repair = row.get("repair_queue_item")
        if not repair:
            continue
        items.append({
            **repair,
            "name": row.get("name"),
            "kind": row.get("kind"),
            "family": row.get("family"),
            "semantic_brief": row.get("semantic_brief"),
            "s57_structure": row.get("s57_structure"),
            "opencpn_s52_spine": row.get("opencpn_s52_spine"),
            "reference_providers": row.get("reference_providers"),
            "helm_candidate": row.get("helm_candidate"),
            "judge": row.get("judge", {}).get("latest"),
        })
    result = {
        "schema_version": 1,
        "status": "queued_for_renderer_repair_with_batch98_routing",
        "source_table": "catalog/standard_source_table.json",
        "summary": {
            "repair_queue_rows": len(items),
            "normal_icon_art_repair_queue_rows": len(items),
            "routed_queue_rows": len(routed_items),
            "witness_needed_queue_rows": len(routed_by_bucket["chart1_parity_witness_needed"]) + len(routed_by_bucket["witness_needed_official_symbol"]),
            "manual_exception_queue_rows": len(routed_by_bucket["manual_policy_exception"]),
            "style_primitive_registry_rows": len(routed_by_bucket["style_primitive_registry"]),
            "portrayal_rule_registry_rows": len(routed_by_bucket["portrayal_rule_registry"]),
            "routing_bucket_counts": {key: len(value) for key, value in sorted(routed_by_bucket.items())},
            "safety_blocked_rows": sum(
                1
                for item in items
                if {
                    "missing_reference_crop",
                    "missing_exact_reference",
                    "insufficient_visual_evidence",
                }.intersection(item.get("safety_reason_codes", []))
            ),
        },
        "items": items,
        "routed_items": routed_items,
        "routed_by_bucket": dict(sorted(routed_by_bucket.items())),
    }
    REPAIR_JSON.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    _write_md(result)
    return result


def _write_md(result: dict) -> None:
    lines = [
        "# Standard Repair Queue",
        "",
        "Row-scoped renderer repair queue generated from the normalized source table.",
        "",
    ]
    for key, value in result["summary"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Items", ""])
    for item in result["items"]:
        lines.append(f"- `{item['asset']}`: {item.get('required_change')}")
    lines.extend(["", "## Routed Items", ""])
    for bucket, items in result.get("routed_by_bucket", {}).items():
        lines.append(f"### `{bucket}`")
        for item in items:
            lines.append(f"- `{item['asset']}`: {item.get('next_action')}")
        lines.append("")
    while lines and lines[-1] == "":
        lines.pop()
    REPAIR_MD.write_text("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args(argv)
    result = build()
    print(json.dumps({
        "status": result["status"],
        "summary": result["summary"],
        "outputs": {
            "json": str(REPAIR_JSON.relative_to(ROOT)),
            "markdown": str(REPAIR_MD.relative_to(ROOT)),
        },
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
