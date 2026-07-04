"""Smoke Standard Witness Resolution Batch 100.

Run:  python3 -m forge.tests.test_standard_witness_resolution_batch100
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_witness_resolution_batch100


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "standard_witness_resolution_batch100.json"


def main():
    result = standard_witness_resolution_batch100.build()
    summary = result["summary"]
    assert result["status"] == "standard_witness_resolution_batch100_written"
    assert summary["total_witness_needed"] == 5
    assert summary["exact_witness_resolved"] == 0
    assert summary["promotion_ready"] == 0
    assert summary["still_blocked"] == 5
    assert summary["attached_reference_count"] == 30
    assert summary["resolution_status_counts"] == {
        "composite_parent_witness_attached_not_exact": 1,
        "equivalent_family_witness_attached_not_exact": 2,
        "related_symbol_witness_attached_not_exact": 1,
        "unresolved_no_tight_witness": 1,
    }

    by_asset = {row["asset"]: row for row in result["records"]}
    assert set(by_asset) == {"BCNCON81", "DANGER53", "DGPS01DRFSTA01", "VEHTRF01", "boyspp50"}
    assert by_asset["BCNCON81"]["resolution_status"] == "equivalent_family_witness_attached_not_exact"
    assert by_asset["boyspp50"]["resolution_status"] == "equivalent_family_witness_attached_not_exact"
    assert by_asset["DANGER53"]["remaining_blocker"] == "official_symbol_definition_or_exact_render_missing"
    assert by_asset["DGPS01DRFSTA01"]["resolution_status"] == "composite_parent_witness_attached_not_exact"
    assert by_asset["VEHTRF01"]["resolution_status"] == "unresolved_no_tight_witness"
    assert not any(row["promotion_ready"] for row in result["records"])
    assert not any(row["normal_icon_art_queue_allowed"] for row in result["records"])

    for row in result["records"]:
        assert row["chart1_parity"]["final_pass_allowed"] is False
        assert row["attached_reference_count"] == len(row["attached_references"])
        for ref in row["attached_references"]:
            assert (ROOT / ref["path"]).exists(), (row["asset"], ref["path"])
            assert ref["status"] != "canonical_art"

    assert any(ref.get("related_asset") == "BCNSPP13" for ref in by_asset["BCNCON81"]["attached_references"])
    assert any(ref.get("related_asset") == "BOYSPP11" for ref in by_asset["boyspp50"]["attached_references"])
    assert any(ref.get("related_asset") == "DANGER51" for ref in by_asset["DANGER53"]["attached_references"])
    assert any(ref.get("related_asset") == "RDOSTA02" for ref in by_asset["DGPS01DRFSTA01"]["attached_references"])

    assert REPORT.exists()
    assert (ROOT / "catalog" / "standard_witness_resolution_batch100.csv").exists()
    assert (ROOT / "catalog" / "standard_witness_resolution_batch100.md").exists()
    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["still_blocked"] == 5
    print("standard witness resolution batch 100: OK")


if __name__ == "__main__":
    main()
