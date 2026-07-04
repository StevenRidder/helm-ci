"""Smoke Standard Routing Batch 98.

Run:  python3 -m forge.tests.test_standard_routing_batch98
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_routing_batch98


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "standard_routing_batch98.json"


def main():
    result = standard_routing_batch98.build()
    summary = result["summary"]
    assert result["status"] == "standard_routing_batch98_written"
    assert summary["total_routed"] == 26
    assert summary["still_normal_icon_art_queue"] == 0
    assert summary["chart1_parity_witness_needed"] == 2
    assert summary["witness_needed_official_symbol"] == 3
    assert summary["manual_policy_exception"] == 2
    assert summary["style_primitive_registry"] == 4
    assert summary["portrayal_rule_registry"] == 15

    by_asset = {row["asset"]: row for row in result["records"]}
    assert set(by_asset) == {
        "ARCSLN01",
        "BCNCON81",
        "DANGER53",
        "DASH",
        "DATCVR01",
        "DEPARE01",
        "DEPARE02",
        "DEPCNT02",
        "DGPS01DRFSTA01",
        "DOTT",
        "LEGLIN02",
        "NEWOBJ 01",
        "NEWOBJ01",
        "OWNSHP02",
        "QUAPOS01;TX(OBJNAM",
        "RESARE01",
        "RESARE02",
        "RESTRN01",
        "SLCONS03",
        "SOLD",
        "SYMINS01",
        "TOPMARI1",
        "VEHTRF01",
        "VESSEL01",
        "VRMEBL01",
        "boyspp50",
    }
    assert by_asset["BCNCON81"]["routing_bucket"] == "chart1_parity_witness_needed"
    assert by_asset["boyspp50"]["routing_bucket"] == "chart1_parity_witness_needed"
    assert by_asset["DANGER53"]["routing_bucket"] == "witness_needed_official_symbol"
    assert by_asset["DGPS01DRFSTA01"]["next_action"] == "attach_tight_reference_before_render"
    assert by_asset["VEHTRF01"]["registry_target"] == "witness_needed_batch98"
    assert by_asset["NEWOBJ 01"]["routing_bucket"] == "manual_policy_exception"
    assert by_asset["NEWOBJ01"]["queue_policy"] == "exclude_from_normal_icon_art_queue_until_product_policy_decision"
    assert by_asset["DASH"]["routing_bucket"] == "style_primitive_registry"
    assert by_asset["SOLD"]["next_action"] == "cover_by_renderer_style_contract_tests"
    assert by_asset["RESARE01"]["routing_bucket"] == "portrayal_rule_registry"
    assert by_asset["VRMEBL01"]["registry_target"] == "portrayal_rule_registry_batch98"
    assert all(row["excluded_from_normal_icon_art_queue"] for row in result["records"])
    assert not any(row["still_normal_icon_art_queue"] for row in result["records"])

    registries = result["registries"]
    assert len(registries["witness_needed_batch98"]) == 5
    assert len(registries["manual_exception_policy_batch98"]) == 2
    assert len(registries["style_primitive_registry_batch98"]) == 4
    assert len(registries["portrayal_rule_registry_batch98"]) == 15

    assert REPORT.exists()
    assert (ROOT / "catalog" / "standard_routing_batch98.csv").exists()
    assert (ROOT / "catalog" / "standard_routing_batch98.md").exists()
    assert (ROOT / "catalog" / "witness_needed_batch98.json").exists()
    assert (ROOT / "catalog" / "witness_needed_batch98.md").exists()
    assert (ROOT / "catalog" / "style_primitive_registry_batch98.json").exists()
    assert (ROOT / "catalog" / "style_primitive_registry_batch98.md").exists()
    assert (ROOT / "catalog" / "portrayal_rule_registry_batch98.json").exists()
    assert (ROOT / "catalog" / "portrayal_rule_registry_batch98.md").exists()
    assert (ROOT / "catalog" / "manual_exception_policy_batch98.json").exists()
    assert (ROOT / "catalog" / "manual_exception_policy_batch98.md").exists()
    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["total_routed"] == 26
    print("standard routing batch 98: OK")


if __name__ == "__main__":
    main()
