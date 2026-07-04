"""Smoke the FORGE-40 electronic Chart 1 synthetic fixture generator.

Run:
  python3 -m forge.tests.test_electronic_chart1_fixtures
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from .. import electronic_chart1_fixtures


def _first(payload: dict, predicate) -> dict:
    for row in payload["fixtures"] + payload["hard_pile"]:
        if predicate(row):
            return row
    raise AssertionError("missing matching electronic Chart 1 fixture row")


def main() -> None:
    payload = electronic_chart1_fixtures.build_fixtures()
    summary = payload["summary"]

    assert payload["schema"] == "helm.forge.electronic_chart1_fixtures.v1"
    assert payload["status"] == "fixtures_ready"
    assert payload["policy"]["generated_from_db_rows_only"] is True
    assert payload["policy"]["browser_business_logic_allowed"] is False
    assert payload["policy"]["static_json_fallback_allowed"] is False
    assert payload["policy"]["runtime_promotion_allowed"] is False

    assert summary["source_rows"] == 3057
    assert summary["fixture_rows"] == 2523
    assert summary["hard_pile_rows"] == 534
    assert summary["accounted_rows"] == summary["source_rows"]
    assert summary["unaccounted_rows"] == 0
    assert summary["duplicate_row_keys"] == []
    assert summary["fixture_taxonomy_counts"] == {
        "area_fill": 100,
        "conditional_rule": 188,
        "line_style": 283,
        "point_symbol": 1843,
        "text_rule": 109,
    }
    assert summary["hard_pile_taxonomy_counts"] == {
        "non_reviewable_construct": 273,
        "placeholder_manual": 238,
        "point_symbol": 7,
        "runtime_overlay": 16,
    }

    keys = [row["row_key"] for row in payload["fixtures"]] + [row["row_key"] for row in payload["hard_pile"]]
    assert len(keys) == len(set(keys)) == 3057
    assert all(row["runtime_gate"]["fail_closed"] is True for row in payload["fixtures"])
    assert all(row["provenance"]["source_db_sha256"] == payload["source"]["contract_db_sha256"] for row in payload["fixtures"])
    assert all(row["provenance"]["browser_business_logic_allowed"] is False for row in payload["fixtures"])
    assert all(row["provenance"]["static_json_fallback_allowed"] is False for row in payload["fixtures"])

    boycan60 = _first(payload, lambda row: row["row_key"] == "BOYSPP_BOYCAN60_1956_30227_1956")
    assert boycan60["fixture_id"] == "ec1-fixture-echart1-1957"
    assert boycan60["row_taxonomy"] == "point_symbol"
    assert boycan60["synthetic_geometry"]["type"] == "Point"
    assert boycan60["geometry_role"] == "stable_symbol_anchor_point"
    assert boycan60["s57"]["object_class"] == "BOYSPP"
    assert boycan60["s101"]["feature_type"] == "BuoySpecialPurposeGeneral"
    assert boycan60["s101"]["rule_file"] == "PortrayalCatalog/Rules/SpecialPurposeGeneralBuoy.lua"
    assert boycan60["helm"]["expected_authority"]["colour"]["helm_colour_authority"]["colour_sequence"] == ["red"]
    assert boycan60["context"]["palette_modes"] == ["day", "dusk", "night"]
    assert boycan60["runtime_gate"]["runtime_eligible"] is False

    area = _first(payload, lambda row: row["row_taxonomy"] == "area_fill")
    assert area["synthetic_geometry"]["type"] == "Polygon"
    assert area["helm"]["expected_authority"]["pattern"]["s52_pattern_refs"]

    line = _first(payload, lambda row: row["row_taxonomy"] == "line_style")
    assert line["synthetic_geometry"]["type"] == "LineString"
    assert line["helm"]["expected_authority"]["pattern"]["s52_line_style_refs"]

    text = _first(payload, lambda row: row["row_taxonomy"] == "text_rule")
    assert text["synthetic_geometry"]["type"] == "Point"
    assert text["text"]["label_values"]

    conditional = _first(payload, lambda row: row["row_taxonomy"] == "conditional_rule")
    assert conditional["synthetic_geometry"]["type"] == "Polygon"
    assert conditional["s57"]["minimum_attributes"] or conditional["s52"]["instruction_evidence"]["conditional_refs"]

    overlay = _first(payload, lambda row: row["row_taxonomy"] == "runtime_overlay")
    assert "runtime_overlay_profile_required" in overlay["reason_codes"]

    manual = _first(payload, lambda row: row["row_taxonomy"] == "placeholder_manual")
    assert "manual_mapping_required" in manual["reason_codes"]

    non_reviewable = _first(payload, lambda row: row["row_taxonomy"] == "non_reviewable_construct")
    assert "presentation_library_construct_not_direct_chart1_symbol" in non_reviewable["reason_codes"]

    malformed_symbol = _first(
        payload,
        lambda row: row["row_taxonomy"] == "point_symbol"
        and "s52_instruction_ast:not_complete" in row.get("reason_codes", []),
    )
    assert malformed_symbol["runtime_gate"]["fail_closed"] is True

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        result = electronic_chart1_fixtures.write_fixtures(
            json_path=tmp_dir / "electronic_chart1_fixtures.json",
            markdown_path=tmp_dir / "electronic_chart1_fixtures.md",
        )
        written = json.loads((tmp_dir / "electronic_chart1_fixtures.json").read_text())
        assert result["status"] == "fixtures_ready"
        assert written["summary"]["accounted_rows"] == 3057
        assert "Electronic Chart 1 Synthetic Fixtures" in (tmp_dir / "electronic_chart1_fixtures.md").read_text()

    print("electronic Chart 1 fixtures: OK")


if __name__ == "__main__":
    main()
