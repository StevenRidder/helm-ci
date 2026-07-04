"""Smoke the standard repair queue exporter.

Run:  python -m forge.tests.test_standard_repair_queue
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_queue


ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    result = standard_repair_queue.build()
    assert result["status"] == "queued_for_renderer_repair_with_batch98_routing"
    assert result["summary"]["repair_queue_rows"] == 0
    assert result["summary"]["normal_icon_art_repair_queue_rows"] == 0
    assert result["summary"]["routed_queue_rows"] == 26
    assert result["summary"]["witness_needed_queue_rows"] == 5
    assert result["summary"]["manual_exception_queue_rows"] == 2
    assert result["summary"]["style_primitive_registry_rows"] == 4
    assert result["summary"]["portrayal_rule_registry_rows"] == 15
    assert result["items"] == []
    by_asset = {item["asset"]: item for item in result["items"]}
    routed_by_asset = {item["asset"]: item for item in result["routed_items"]}
    former_repair_rows = {
        "BCNCON81",
        "DANGER53",
        "DGPS01DRFSTA01",
        "NEWOBJ 01",
        "NEWOBJ01",
        "VEHTRF01",
        "boyspp50",
    }
    assert former_repair_rows <= set(routed_by_asset)
    assert "ARCSLN01" not in by_asset
    assert "ARCSLN01" in routed_by_asset
    assert "CBLSUB06" not in by_asset
    assert "CLRLIN01" not in by_asset
    assert "DQUALA11" not in by_asset
    assert "FSHHAV02" not in by_asset
    assert "LIGHTS05" not in by_asset
    assert "OBSTRN04" not in by_asset
    assert "RCRTCL14" not in by_asset
    assert "TOWERS74|;TX(OBJNAM" not in by_asset
    assert "WRECKS02" not in by_asset
    assert routed_by_asset["DANGER53"]["s57_structure"]["s52_instruction"]
    assert routed_by_asset["DANGER53"]["reference_providers"]["opencpn_render"] == []
    assert routed_by_asset["DANGER53"]["routing_bucket"] == "witness_needed_official_symbol"
    assert routed_by_asset["DANGER53"]["helm_candidate"]["canonical_svg"]
    assert routed_by_asset["BCNCON81"]["routing_bucket"] == "chart1_parity_witness_needed"
    assert routed_by_asset["boyspp50"]["routing_bucket"] == "chart1_parity_witness_needed"
    assert "exact_symbol_crop_or_equivalent_tight_witness" in routed_by_asset["BCNCON81"]["evidence_required"]
    assert set(result["routed_by_bucket"]) == {
        "chart1_parity_witness_needed",
        "manual_policy_exception",
        "portrayal_rule_registry",
        "style_primitive_registry",
        "witness_needed_official_symbol",
    }

    saved = json.loads((ROOT / "catalog" / "standard_repair_queue.json").read_text())
    assert saved["summary"]["repair_queue_rows"] == result["summary"]["repair_queue_rows"]
    assert saved["summary"]["routed_queue_rows"] == 26
    assert (ROOT / "catalog" / "standard_repair_queue.md").exists()
    print("standard repair queue: OK")


if __name__ == "__main__":
    main()
