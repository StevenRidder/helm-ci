"""Smoke the FORGE-44 Electronic Chart 1 authority corpus.

Run:
  python3 -m forge.tests.test_electronic_chart1_authority_corpus
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from .. import electronic_chart1_authority_corpus


def _first(payload: dict, row_key: str) -> dict:
    for row in payload["rows"]:
        if row["row_key"] == row_key:
            return row
    raise AssertionError(f"missing row: {row_key}")


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        result = electronic_chart1_authority_corpus.write_corpus(
            json_path=tmp_dir / "electronic_chart1_authority_corpus.json",
            markdown_path=tmp_dir / "electronic_chart1_authority_corpus.md",
        )
        payload = json.loads((tmp_dir / "electronic_chart1_authority_corpus.json").read_text())

        assert result["status"] == "electronic_chart1_authority_corpus_ready"
        assert payload["schema"] == "helm.forge.electronic_chart1_authority_corpus.v1"
        assert payload["status"] == "electronic_chart1_authority_corpus_ready"
        assert payload["policy"]["backend_generated"] is True
        assert payload["policy"]["browser_business_logic_allowed"] is False
        assert payload["policy"]["frontend_written_prose_allowed"] is False
        assert payload["policy"]["static_json_fallback_allowed"] is False
        assert payload["policy"]["llm_batch_allowed"] is True
        assert payload["policy"]["llm_page_load_generation_allowed"] is False
        assert payload["policy"]["runtime_promotion_allowed"] is False
        assert payload["policy"]["missing_source_language_must_be_explicit_gap"] is True

        global_language = payload["global_language"]
        assert "horizontal_bands" in global_language["colour_language"]
        assert "vertical_stripes" in global_language["colour_language"]
        assert "topmark" in global_language["shape_language"]
        assert "line_style" in global_language["shape_language"]
        assert "area_fill" in global_language["shape_language"]
        assert "conditional_rule" in global_language["shape_language"]
        assert "simplified_symbol" in global_language["shape_language"]

        summary = payload["summary"]
        assert summary["contract_rows"] == 3057
        assert summary["authority_rows"] == 3057
        assert summary["fixture_rows"] == 2523
        assert summary["opencpn_reference_rows"] == 2460
        assert summary["helm_s57_render_rows"] == 2374
        assert summary["helm_s101_trace_rows"] == 1564
        assert summary["helm_s101_fail_closed_rows"] == 959
        assert summary["runtime_eligible_rows"] == 0
        assert summary["status_counts"] == {
            "authority_text_manual_required": 511,
            "authority_text_pending_source": 1657,
            "authority_text_ready": 889,
        }
        assert summary["validation_counts"] == {"passed": 3057}
        assert summary["row_taxonomy_counts"] == {
            "area_fill": 100,
            "conditional_rule": 188,
            "line_style": 283,
            "non_reviewable_construct": 273,
            "placeholder_manual": 238,
            "point_symbol": 1850,
            "runtime_overlay": 16,
            "text_rule": 109,
        }
        assert summary["source_language_gap_counts"]["s101_feature_type:missing"] == 1395
        assert summary["source_language_gap_counts"]["helm_shape_family:missing"] == 1165
        assert summary["source_language_gap_counts"]["s52_instruction:missing"] == 52
        assert summary["source_language_gap_counts"]["s52_parse_status:partial"] == 7

        assert len(payload["rows"]) == 3057
        assert len({row["row_key"] for row in payload["rows"]}) == 3057
        assert all(row["validation"]["status"] == "passed" for row in payload["rows"])
        assert all(row["runtime_gate"]["runtime_eligible"] is False for row in payload["rows"])
        assert all(row["consumer_contract"]["browser_business_logic_allowed"] is False for row in payload["rows"])
        assert all(row["helm_interpretation"]["frontend_written_prose_allowed"] is False for row in payload["rows"])

        boycan60 = _first(payload, "BOYLAT_BOYCAN60_1907_30184_1907")
        assert boycan60["helm_interpretation"]["status"] == "authority_text_ready"
        assert boycan60["source_language_gaps"] == []
        assert boycan60["s101_authority"]["trace"]["classification"] == "rule_derived"
        assert boycan60["s101_authority"]["trace"]["rule_file"] == "PortrayalCatalog/Rules/SpecialPurposeGeneralBuoy.lua"
        assert boycan60["s101_authority"]["trace"]["attributes"]["buoyShape"] == "can"
        assert boycan60["helm_authority"]["recipe"]["shape_family"] == "buoy_can"
        assert "Buoy, lateral" in boycan60["helm_interpretation"]["text"]
        assert "SpecialPurposeGeneralBuoy.lua" in boycan60["helm_interpretation"]["text"]

        topshq28 = _first(payload, "TOPMAR_TOPSHQ28_2433_93904_2430")
        assert topshq28["helm_interpretation"]["status"] == "authority_text_ready"
        assert topshq28["s101_authority"]["trace"]["classification"] == "rule_derived"
        assert topshq28["s101_authority"]["trace"]["rule_file"] == "PortrayalCatalog/Rules/Daymark.lua"
        assert topshq28["s57_authority"]["attribute_tuple"]["topmark_shape_source_attribute"] == "TOPSHP"
        assert "topmark" in topshq28["helm_interpretation"]["text"]

        topmar = _first(payload, "DAYMAR_TOPMAR01_2118_93812_2119")
        assert topmar["helm_interpretation"]["status"] == "authority_text_pending_source"
        assert topmar["s101_authority"]["trace"]["classification"] == "catalogue_rule"
        assert topmar["s101_authority"]["trace"]["rule_file"] == "PortrayalCatalog/Rules/TOPMAR02.lua"
        assert "helm_s57_render:missing" in topmar["source_language_gaps"]
        assert "helm_recipe:missing" in topmar["helm_interpretation"]["known_gaps"]

        bridge = _first(payload, "BRIDGE_text-only_15_32051_15")
        assert bridge["helm_interpretation"]["status"] == "authority_text_pending_source"
        assert "s101_feature_type:missing" in bridge["source_language_gaps"]
        assert "s101_db_backing:missing" in bridge["source_language_gaps"]

        md = (tmp_dir / "electronic_chart1_authority_corpus.md").read_text()
        assert "Authority prose is generated from backend/export evidence" in md
        assert "authority_rows: `3057`" in md
        assert "runtime_eligible_rows: `0`" in md

    print("electronic Chart 1 authority corpus: OK")


if __name__ == "__main__":
    main()
