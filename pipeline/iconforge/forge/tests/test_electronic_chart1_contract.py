"""Smoke the FORGE-39 electronic Chart 1 DB contract.

Run:
  python3 -m forge.tests.test_electronic_chart1_contract
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from .. import electronic_chart1_contract


def _first(payload: dict, predicate) -> dict:
    for row in payload["rows"]:
        if predicate(row):
            return row
    raise AssertionError("missing matching electronic Chart 1 row")


def main() -> None:
    payload = electronic_chart1_contract.build_contract()
    assert payload["schema"] == "helm.forge.electronic_chart1_contract.v1"
    assert payload["status"] == "contract_ready"
    assert payload["policy"]["runtime_promotion_allowed"] is False
    assert payload["policy"]["browser_business_logic_allowed"] is False
    assert payload["summary"]["rows"] == 3057
    assert payload["summary"]["total_db_rows"] == 3057
    assert payload["summary"]["runtime_symbol_portrayal_rows"] == 0
    assert payload["summary"]["non_fail_closed_rows"] == 0
    assert payload["summary"]["failing_audits"] == []
    assert payload["summary"]["taxonomy_counts"] == {
        "area_fill": 100,
        "conditional_rule": 188,
        "line_style": 283,
        "non_reviewable_construct": 273,
        "placeholder_manual": 238,
        "point_symbol": 1850,
        "runtime_overlay": 16,
        "text_rule": 109,
    }
    assert payload["summary"]["evidence_status_counts"] == {
        "red": 245,
        "yellow": 2812,
    }
    assert all(row["render_eligibility"] == "fail_closed_not_runtime_eligible" for row in payload["rows"])
    assert all(row["reason_codes"] for row in payload["rows"] if row["evidence_status"] in {"red", "yellow"})

    boycan60 = _first(payload, lambda row: row["row_key"] == "BOYSPP_BOYCAN60_1956_30227_1956")
    assert boycan60["row_taxonomy"] == "point_symbol"
    assert boycan60["s101"]["feature_type"] == "BuoySpecialPurposeGeneral"
    assert boycan60["s101"]["rule_file"] == "PortrayalCatalog/Rules/SpecialPurposeGeneralBuoy.lua"
    assert boycan60["helm"]["art_status"] == "canonical_helm_art_recorded"
    assert boycan60["helm"]["art_path"].endswith("BOYCAN60.svg")
    assert boycan60["helm"]["colour_authority"]["colour_sequence"] == ["red"]
    assert boycan60["human_qa_status"]["runtime_eligible"] is False

    vrmebl = _first(payload, lambda row: row["s57"]["attribute_tuple"].get("s52_symbol_id") == "VRMEBL01")
    assert vrmebl["row_taxonomy"] == "runtime_overlay"
    assert "runtime_overlay_profile_required" in vrmebl["reason_codes"]

    non_reviewable = _first(payload, lambda row: row["s57"]["object_class"] == "$AREAS")
    assert non_reviewable["row_taxonomy"] == "non_reviewable_construct"
    assert "presentation_library_construct_not_direct_chart1_symbol" in non_reviewable["reason_codes"]

    manual = _first(payload, lambda row: row["row_taxonomy"] == "placeholder_manual")
    assert manual["evidence_status"] == "red"
    assert "manual_mapping_required" in manual["reason_codes"]

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        result = electronic_chart1_contract.write_contract(
            json_path=tmp_dir / "electronic_chart1_contract.json",
            markdown_path=tmp_dir / "electronic_chart1_contract.md",
        )
        written = json.loads((tmp_dir / "electronic_chart1_contract.json").read_text())
        assert result["status"] == "contract_ready"
        assert written["summary"]["rows"] == 3057
        assert "Electronic Chart 1 Contract" in (tmp_dir / "electronic_chart1_contract.md").read_text()

    print("electronic Chart 1 contract: OK")


if __name__ == "__main__":
    main()
