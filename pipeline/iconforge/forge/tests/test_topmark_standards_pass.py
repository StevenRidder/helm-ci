"""Smoke the topmark standards pass.

Run:  python3 -m forge.tests.test_topmark_standards_pass
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import topmark_standards_pass


ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    result = topmark_standards_pass.build()
    summary = result["summary"]
    assert result["status"] == "topmark_standards_pass_written"
    assert summary["standard_shape_refs"] == 33
    assert summary["s101_topmark_svg_entries"] == 32
    assert summary["s101_topmark_svg_sources_found"] == 32
    assert summary["s101_topmark_png_rendered"] == 32
    assert summary["topmark_rows_needing_special_pass"] >= 30
    assert summary["resolved_exact_or_inferred_shape_rows"] > 0
    assert summary["ambiguous_or_unresolved_rows"] > 0
    assert summary["candidate_png_rendered_rows"] > 0

    shape_by_id = {shape["shape_id"]: shape for shape in result["standard_shapes"]}
    assert shape_by_id["TOPSHP01"]["shape_name"] == "cone, point up"
    assert shape_by_id["TOPSHP10"]["shape_name"] == "two cones, point to point"
    assert shape_by_id["TOPSHP11"]["shape_name"] == "two cones, base to base"
    assert shape_by_id["TOPSHP33"]["s101_topmarkDaymarkShape"] == "other/manual"
    assert result["s101_topmar02_mapping"]["floating_symbol_to_shape_codes"]["TOPMAR02"] == [1, 24, 29]
    assert result["s101_topmar02_mapping"]["rigid_symbol_to_shape_codes"]["TOPMAR88"] == [15]
    assert {row["id"] for row in result["s101_topmark_witnesses"]} >= {"TOPMAR02", "TOPMAR87", "TOPMAR88", "TMARDEF1"}

    by_asset = {row["asset"]: row for row in result["queue"]}
    assert by_asset["TOPSHP01"]["expected_shape"]["shape_id"] == "TOPSHP23"
    assert by_asset["TOPSHP33"]["expected_shape"]["shape_id"] == "TOPSHP19"
    assert by_asset["TOPSHPS1"]["expected_shape"]["shape_id"] == "TOPSHP33"
    assert by_asset["TOPMA100"]["expected_shape"]["shape_id"] == "TOPSHP25"
    assert by_asset["TOPMA113"]["expected_shape"]["shape_id"] == "TOPSHP07"
    assert by_asset["TOPMAR87"]["expected_shape"]["shape_id"] == "TOPSHP15"
    assert by_asset["TOPMAR87"]["s101_witnesses"][0]["id"] == "TOPMAR88"
    assert by_asset["TOPMAR87"]["s101_witnesses"][0]["role"] == "s101_TOPMAR02_rigid_rule_output"
    assert any(witness["id"] == "TOPMAR87" for witness in by_asset["TOPMAR87"]["s101_witnesses"])
    assert by_asset["TOPMAR01"]["expected_shape"]["basis"] == "s57_structure_conditions_TOPSHP"
    assert any(witness["id"] == "TOPMAR30" for witness in by_asset["TOPMAR01"]["s101_witnesses"])

    assert (ROOT / "catalog" / "topmark_standards_pass.json").exists()
    assert (ROOT / "catalog" / "topmark_standards_pass.csv").exists()
    assert (ROOT / "catalog" / "topmark_standards_pass.md").exists()
    assert (ROOT / "out" / "topmark_standards_pass" / "index.html").exists()
    assert (ROOT / "out" / "topmark_standards_pass" / "standard_svg" / "TOPSHP01.svg").exists()
    assert (ROOT / "out" / "topmark_standards_pass" / "topmark_standard_reference_sheet.png").exists()
    saved = json.loads((ROOT / "catalog" / "topmark_standards_pass.json").read_text())
    assert saved["summary"]["standard_shape_refs"] == 33
    assert saved["summary"]["s101_topmark_svg_entries"] == 32
    assert saved["standard_reference_sheet"] == "out/topmark_standards_pass/topmark_standard_reference_sheet.png"
    print("topmark standards pass: OK")


if __name__ == "__main__":
    main()
