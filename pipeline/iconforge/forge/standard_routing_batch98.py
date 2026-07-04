"""Route remaining non-pass rows out of the normal icon-art queue.

Batch 98 is a queue hygiene gate. It does not approve art and it does not
weaken the Chart No.1 parity gate. It records why the remaining rows are not
ordinary render/judge jobs and gives each row a durable next bucket.

Run:
  python3 -m forge.standard_routing_batch98
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
SOURCE_TABLE = CATALOG / "standard_source_table.json"
BATCH96 = CATALOG / "standard_reference_resolution_batch96.json"
OUT_JSON = CATALOG / "standard_routing_batch98.json"
OUT_CSV = CATALOG / "standard_routing_batch98.csv"
OUT_MD = CATALOG / "standard_routing_batch98.md"
WITNESS_JSON = CATALOG / "witness_needed_batch98.json"
WITNESS_MD = CATALOG / "witness_needed_batch98.md"
STYLE_JSON = CATALOG / "style_primitive_registry_batch98.json"
STYLE_MD = CATALOG / "style_primitive_registry_batch98.md"
RULE_JSON = CATALOG / "portrayal_rule_registry_batch98.json"
RULE_MD = CATALOG / "portrayal_rule_registry_batch98.md"
MANUAL_JSON = CATALOG / "manual_exception_policy_batch98.json"
MANUAL_MD = CATALOG / "manual_exception_policy_batch98.md"

NON_PASS_STATUSES = {
    "chart1_fail_repair_queue",
    "judge_fail_repair_queue",
    "pending_judge",
}

ROUTED_STATUSES = {
    "chart1_parity_witness_needed",
    "witness_needed_official_symbol",
    "manual_policy_exception",
    "style_primitive_registry",
    "portrayal_rule_registry",
}

CHART1_PARITY_ACTION = {
    "routing_bucket": "chart1_parity_witness_needed",
    "queue_policy": "exclude_from_normal_icon_art_queue_until_chart1_parity_evidence",
    "registry_target": "witness_needed_batch98",
    "next_action": "attach_exact_chart1_or_equivalent_witness_then_rerun_parity_gate",
    "evidence_required": [
        "exact_symbol_crop_or_equivalent_tight_witness",
        "s57_s52_condition_confirmation",
        "human_manual_exception_only_if_no_official_witness_exists",
    ],
}

CLASSIFICATION_ROUTES = {
    "reference_blocked_official_symbol": {
        "routing_bucket": "witness_needed_official_symbol",
        "queue_policy": "exclude_from_normal_icon_art_queue_until_tight_witness_attached",
        "registry_target": "witness_needed_batch98",
        "next_action": "attach_tight_reference_before_render",
        "evidence_required": [
            "official_symbol_witness",
            "s57_s52_condition_confirmation",
            "source_crop_or_render_reference_id",
        ],
    },
    "manual_exception_newobj_placeholder": {
        "routing_bucket": "manual_policy_exception",
        "queue_policy": "exclude_from_normal_icon_art_queue_until_product_policy_decision",
        "registry_target": "manual_exception_policy_batch98",
        "next_action": "decide_runtime_placeholder_policy_or_explicit_manual_exception",
        "evidence_required": [
            "product_policy_decision",
            "manual_exception_reason",
            "final_human_signoff_if_published",
        ],
    },
    "style_primitive_not_standalone_icon": {
        "routing_bucket": "style_primitive_registry",
        "queue_policy": "track_in_renderer_style_contract_not_icon_art_approval",
        "registry_target": "style_primitive_registry_batch98",
        "next_action": "cover_by_renderer_style_contract_tests",
        "evidence_required": [
            "stroke_dash_pattern_contract",
            "palette_and_line_width_contract",
            "renderer_golden_or_structural_test",
        ],
    },
    "portrayal_rule_not_standalone_icon": {
        "routing_bucket": "portrayal_rule_registry",
        "queue_policy": "track_in_rule_registry_not_icon_art_approval",
        "registry_target": "portrayal_rule_registry_batch98",
        "next_action": "cover_by_portrayal_rule_or_runtime_renderer_test",
        "evidence_required": [
            "conditional_procedure_mapping",
            "runtime_rule_expected_output",
            "not_comparable_as_standalone_svg_reason",
        ],
    },
}


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _source_rows() -> dict[str, dict]:
    return {row["asset"]: row for row in _read_json(SOURCE_TABLE)["rows"]}


def _batch96_records() -> dict[str, dict]:
    return {row["asset"]: row for row in _read_json(BATCH96)["records"]}


def _non_pass_rows(rows: dict[str, dict], batch96: dict[str, dict]) -> list[dict]:
    selected = [
        row
        for row in rows.values()
        if (row.get("helm_candidate") or {}).get("candidate_status") in NON_PASS_STATUSES | ROUTED_STATUSES
        or row.get("batch98_routing")
    ]
    if selected:
        return selected
    return [rows[asset] for asset in batch96 if asset in rows]


def _route_for(row: dict, batch96: dict[str, dict]) -> dict:
    routing = row.get("batch98_routing") or {}
    bucket = routing.get("routing_bucket") or (row.get("helm_candidate") or {}).get("candidate_status")
    if bucket in ROUTED_STATUSES:
        for route in [CHART1_PARITY_ACTION, *CLASSIFICATION_ROUTES.values()]:
            if route["routing_bucket"] == bucket:
                return route
    helm = row.get("helm_candidate") or {}
    status = helm.get("candidate_status")
    if status == "chart1_fail_repair_queue":
        return CHART1_PARITY_ACTION
    classification = (batch96.get(row["asset"]) or {}).get("classification")
    try:
        return CLASSIFICATION_ROUTES[classification]
    except KeyError as exc:
        raise ValueError(f"no batch98 route for {row['asset']} status={status} classification={classification}") from exc


def _record(row: dict, batch96: dict[str, dict]) -> dict:
    asset = row["asset"]
    helm = row.get("helm_candidate") or {}
    route = _route_for(row, batch96)
    prior = batch96.get(asset) or {}
    input_status = helm.get("pre_routing_candidate_status") or helm.get("candidate_status")
    classification = prior.get("classification")
    if input_status == "chart1_fail_repair_queue":
        classification = "chart1_parity_blocked_after_symbolspec_render"
    return {
        "asset": asset,
        "name": row.get("name"),
        "kind": row.get("kind"),
        "family": row.get("family"),
        "input_candidate_status": input_status,
        "input_source_batch": helm.get("source_batch"),
        "classification": classification,
        "routing_bucket": route["routing_bucket"],
        "queue_policy": route["queue_policy"],
        "registry_target": route["registry_target"],
        "next_action": route["next_action"],
        "excluded_from_normal_icon_art_queue": True,
        "still_normal_icon_art_queue": False,
        "final_approved": False,
        "evidence_required": route["evidence_required"],
        "resolution": prior.get("resolution")
        or "Chart No.1 parity gate blocked a rendered SymbolSpec candidate; keep blocked until exact witness or manual exception.",
        "semantic_brief": row.get("semantic_brief"),
        "s57_structure": row.get("s57_structure"),
        "candidate": {
            "canonical_svg": helm.get("canonical_svg"),
            "source_svg": helm.get("source_svg"),
            "source": helm.get("source"),
            "style_contract": helm.get("style_contract"),
        },
        "reference_counts": {
            key: len(value) if isinstance(value, list) else bool(value)
            for key, value in (row.get("reference_providers") or {}).items()
        },
    }


def build() -> dict:
    rows = _source_rows()
    batch96 = _batch96_records()
    records = [_record(row, batch96) for row in _non_pass_rows(rows, batch96)]
    records.sort(key=lambda item: item["asset"])

    counts = Counter(record["routing_bucket"] for record in records)
    status_counts = Counter(record["input_candidate_status"] for record in records)
    registries: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        registries[record["registry_target"]].append(record)

    result = {
        "schema_version": 1,
        "status": "standard_routing_batch98_written",
        "project": "vulkan",
        "task_id": "FORGE-15",
        "source_table": "catalog/standard_source_table.json",
        "classification_source": "catalog/standard_reference_resolution_batch96.json",
        "queue_policy": "remaining non-pass rows are explicitly routed; none may be silently promoted by the normal icon-art loop",
        "summary": {
            "total_routed": len(records),
            "still_normal_icon_art_queue": sum(1 for row in records if row["still_normal_icon_art_queue"]),
            "chart1_parity_witness_needed": counts["chart1_parity_witness_needed"],
            "witness_needed_official_symbol": counts["witness_needed_official_symbol"],
            "manual_policy_exception": counts["manual_policy_exception"],
            "style_primitive_registry": counts["style_primitive_registry"],
            "portrayal_rule_registry": counts["portrayal_rule_registry"],
            "input_status_counts": dict(sorted(status_counts.items())),
            "routing_bucket_counts": dict(sorted(counts.items())),
        },
        "records": records,
        "registries": dict(sorted(registries.items())),
    }

    OUT_JSON.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    _write_csv(records)
    _write_md(result)
    _write_registry(
        WITNESS_JSON,
        WITNESS_MD,
        "Witness Needed Batch 98",
        "Rows blocked until an exact Chart No.1/equivalent witness or official reference is attached.",
        registries["witness_needed_batch98"],
    )
    _write_registry(
        STYLE_JSON,
        STYLE_MD,
        "Style Primitive Registry Batch 98",
        "Line/stroke primitives that belong to renderer style-contract tests, not standalone icon approval.",
        registries["style_primitive_registry_batch98"],
    )
    _write_registry(
        RULE_JSON,
        RULE_MD,
        "Portrayal Rule Registry Batch 98",
        "Conditional procedures that belong to the rule/runtime registry, not standalone icon approval.",
        registries["portrayal_rule_registry_batch98"],
    )
    _write_registry(
        MANUAL_JSON,
        MANUAL_MD,
        "Manual Exception Policy Batch 98",
        "Placeholder rows that need an explicit product/manual policy before any publishable asset.",
        registries["manual_exception_policy_batch98"],
    )
    return result


def _write_csv(records: list[dict]) -> None:
    with OUT_CSV.open("w", newline="") as f:
        fields = [
            "asset",
            "name",
            "kind",
            "input_candidate_status",
            "classification",
            "routing_bucket",
            "queue_policy",
            "registry_target",
            "next_action",
            "resolution",
        ]
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for record in records:
            writer.writerow({key: record.get(key) for key in fields})


def _write_md(result: dict) -> None:
    lines = [
        "# Standard Routing Batch 98",
        "",
        "- Project: `vulkan`",
        "- Task: `FORGE-15`",
        "- Purpose: route the remaining non-pass rows out of the normal icon-art loop.",
        "- Final approval: none; this is a routing/registry gate only.",
        "- Safety: Chart No.1 parity blocks remain blocking.",
        "",
        "## Summary",
        "",
        "| Metric | Count |",
        "| --- | ---: |",
    ]
    for key, value in result["summary"].items():
        if isinstance(value, dict):
            continue
        lines.append(f"| `{key}` | {value} |")
    lines.extend(["", "## Routes", "", "| Asset | Input status | Bucket | Next action |", "| --- | --- | --- | --- |"])
    for record in result["records"]:
        lines.append(
            f"| `{record['asset']}` | `{record['input_candidate_status']}` | "
            f"`{record['routing_bucket']}` | `{record['next_action']}` |"
        )
    OUT_MD.write_text("\n".join(lines) + "\n")


def _write_registry(path_json: Path, path_md: Path, title: str, description: str, records: list[dict]) -> None:
    payload = {
        "schema_version": 1,
        "status": "batch98_registry_written",
        "project": "vulkan",
        "task_id": "FORGE-15",
        "title": title,
        "description": description,
        "summary": {"rows": len(records)},
        "records": records,
    }
    path_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    lines = [
        f"# {title}",
        "",
        description,
        "",
        "| Asset | Kind | Bucket | Next action |",
        "| --- | --- | --- | --- |",
    ]
    for record in records:
        lines.append(f"| `{record['asset']}` | `{record['kind']}` | `{record['routing_bucket']}` | `{record['next_action']}` |")
    path_md.write_text("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser().parse_args(argv)
    result = build()
    print(json.dumps({"status": "ok", "summary": result["summary"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
