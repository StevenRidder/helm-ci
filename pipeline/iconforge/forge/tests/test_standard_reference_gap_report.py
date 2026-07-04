"""Smoke the standard reference-gap report.

Run:  python3 -m forge.tests.test_standard_reference_gap_report
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_reference_gap_report


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "standard_reference_gap_report.json"


def main():
    result = standard_reference_gap_report.build()
    summary = result["summary"]
    assert result["status"] == "reference_gap_report_written"
    assert summary["source_table_rows"] == 824
    assert summary["recognition_packets"] == 824
    assert summary["reference_gap_rows"] == 41
    assert summary["gap_class_counts"] == {
        "candidate_blocked_no_reference_images": 15,
        "routed_manual_exception": 2,
        "routed_portrayal_rule": 15,
        "routed_style_primitive": 4,
        "routed_witness_needed": 5,
    }
    by_asset = {row["asset"]: row for row in result["rows"]}
    assert by_asset["BCNCON81"]["gap_class"] == "routed_witness_needed"
    assert by_asset["BCNCON81"]["routing_bucket"] == "chart1_parity_witness_needed"
    assert by_asset["BOYLAT52"]["gap_class"] == "candidate_blocked_no_reference_images"
    assert by_asset["ARCSLN01"]["gap_class"] == "routed_style_primitive"
    assert by_asset["ARCSLN01"]["source_batch"] == "catalog/owned_repair_batch91.json"
    assert by_asset["DANGER53"]["provider_counts"]["opencpn_render"] == 0
    assert by_asset["DANGER53"]["gap_class"] == "routed_witness_needed"
    assert by_asset["RESARE01"]["gap_class"] == "routed_portrayal_rule"
    assert by_asset["NEWOBJ01"]["gap_class"] == "routed_manual_exception"
    assert "tight reference image" in by_asset["BOYLAT52"]["expected_action"]
    assert REPORT.exists()
    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["reference_gap_rows"] == 41
    assert (ROOT / "catalog" / "standard_reference_gap_report.md").exists()
    assert (ROOT / "catalog" / "standard_reference_gap_report.csv").exists()
    print("standard reference gap report: OK")


if __name__ == "__main__":
    main()
