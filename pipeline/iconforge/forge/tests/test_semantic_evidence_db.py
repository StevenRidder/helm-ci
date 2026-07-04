"""Smoke the FORGE-26 semantic evidence DB-view artifact.

Run:
  python3 -m forge.tests.test_semantic_evidence_db
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from .. import semantic_evidence_db


def _row(result: dict, symbol_id: str) -> dict:
    for row in result["rows"]:
        if row["symbol_id"] == symbol_id:
            return row
    raise AssertionError(f"missing symbol row {symbol_id}")


def _assert_fail_closed(row: dict) -> None:
    gate = row["runtime_gate_summary"]
    assert gate["runtime_eligible"] is False
    assert gate["status"] in {"pending", "blocked", "manual_review_required"}
    assert "runtime_not_eligible" in row["evidence_gap_reasons"]
    assert row["consumer_contract"]["browser_business_logic_allowed"] is False
    assert row["consumer_contract"]["backend_db_source_of_truth"] is True


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        out = tmp_dir / "semantic_evidence_db.json"
        md = tmp_dir / "semantic_evidence_db.md"
        result = semantic_evidence_db.build()

        assert result["schema"] == "helm.forge.semantic-evidence-db.v1"
        assert result["status"] == "provisional_semantic_evidence_db_ready"
        assert "does not yet claim full runtime-grade S-101 Lua" in result["strict_runtime_position"]
        assert result["consumer_contract"]["browser_business_logic_allowed"] is False
        assert result["consumer_contract"]["hidden_fallbacks_allowed"] is False

        coverage = result["coverage"]
        assert coverage["rows"] == 824
        assert coverage["source_rows"]["standard_source_table"] == 824
        assert coverage["source_rows"]["standards_s101_resolver"] == 824
        assert coverage["source_rows"]["standards_three_way_proof"] == 824
        assert coverage["source_rows"]["chartplotter_rule_input"] == 824
        assert coverage["all_required_api_fields_returned"] is True
        for field in semantic_evidence_db.REQUIRED_API_FIELDS:
            assert coverage["required_api_fields_returned"][field] == 824, field
        assert coverage["runtime_gate_counts"]["runtime_eligible"] == 0
        assert coverage["runtime_gate_counts"]["runtime_blocked_or_pending"] == 824
        assert coverage["gap_counts_by_reason"]["runtime_not_eligible"] == 824
        assert coverage["gap_counts_by_reason"]["helm_symbol_recipe_not_ready"] == 250
        assert coverage["gap_counts_by_reason"]["helm_interpretation_not_ready"] == 369
        assert "missing_s101_feature_type" not in coverage["gap_counts_by_reason"]
        assert coverage["s52_instruction_ast_status_counts"] == {
            "parsed": 776,
            "parsed_with_conditional_references": 48,
        }
        assert coverage["helm_symbol_recipe_status_counts"] == {
            "manual_exception_required": 206,
            "recipe_missing": 44,
            "recipe_ready": 574,
        }
        assert coverage["helm_interpretation_status_counts"] == {
            "helm_interpretation_manual_required": 325,
            "helm_interpretation_pending_evidence": 44,
            "helm_interpretation_ready": 455,
        }
        assert coverage["helm_interpretation_validation_counts"] == {
            "passed": 824,
        }
        assert coverage["s101_rule_contract_status_counts"] == {
            "catalogue_rule_reference_ready": 90,
            "direct_symbol_contract_ready": 244,
            "documented_deviation_review": 108,
            "non_s101_or_extension_profile_required": 123,
            "non_s101_runtime_construct": 44,
            "rule_contract_ready": 215,
        }
        serialized = json.dumps(result)
        for dirty in [
            "TOPSHP09;TE",
            "TOPSHP15;TE",
            "TOPSHP73;TE",
            "TOPSHP81;TE",
            "TOPSHP89;TE",
            "TOPSHPT8;TE",
            "TOWERS74|;TX",
            "QUAPOS01;TX(OBJNAM",
            "missing_s101_feature_type",
        ]:
            assert dirty not in serialized

        boycan60 = _row(result, "BOYCAN60")
        assert boycan60["canonical_row_key"] == "BOYSPP_BOYCAN60_1956"
        assert "SY(BOYCAN60)" in boycan60["s52_instruction"]
        assert boycan60["s52_instruction_ast_status"] == "parsed"
        assert boycan60["s52_instruction_ast"]["symbols"] == ["BOYCAN60"]
        assert boycan60["s101_feature_type"] == "SpecialPurposeGeneralBuoy"
        assert boycan60["s101_rule_file"] == "PortrayalCatalog/Rules/SpecialPurposeGeneralBuoy.lua"
        assert boycan60["s101_attributes"]["buoyShape"] == "can"
        assert boycan60["s101_attributes"]["colour"] == ["red"]
        assert boycan60["s101_rule_contract_status"] == "rule_contract_ready"
        assert boycan60["s101_rule_contract"]["filename_gap"]["interpretation"] == "expected_rule_derived_gap"
        assert boycan60["s101_rule_contract"]["filename_gap"]["is_error"] is False
        assert boycan60["helm_symbol_recipe_status"] == "recipe_ready"
        assert boycan60["helm_symbol_recipe"]["shape_family"] == "buoy_can"
        assert boycan60["helm_symbol_recipe"]["color_tokens"] == ["red"]
        assert boycan60["helm_symbol_recipe"]["pattern_token"] == "solid"
        assert boycan60["helm_symbol_recipe"]["browser_business_logic_allowed"] is False
        assert boycan60["helm_interpretation_status"] == "helm_interpretation_ready"
        assert boycan60["helm_interpretation"]["validation"]["status"] == "passed"
        assert "SpecialPurposeGeneralBuoy" in boycan60["helm_interpretation"]["text"]
        assert "buoy_can" in boycan60["helm_interpretation"]["text"]
        assert "red" in boycan60["helm_interpretation"]["text"]
        assert boycan60["proof_page_payload"]["helm_interpretation"]["text"] == boycan60["helm_interpretation"]["text"]
        assert boycan60["resolver_status"] == "resolved_rule"
        assert boycan60["s101_crosswalk_class"] == "s101_feature_equivalent"
        _assert_fail_closed(boycan60)

        boylat53 = _row(result, "BOYLAT53")
        assert "SY(BOYLAT53)" in boylat53["s52_instruction"]
        assert boylat53["s101_feature_type"] == "LateralBuoy"
        assert boylat53["s101_attributes"]["colour"] == ["green", "red", "green"]
        assert boylat53["s57_attribute_tuple"]["colour_sequence"] == ["green", "red", "green"]
        assert boylat53["helm_symbol_recipe"]["shape_family"] == "buoy_generic"
        assert boylat53["helm_symbol_recipe"]["color_tokens"] == ["green", "red", "green"]
        assert boylat53["helm_symbol_recipe"]["pattern_token"] == "horizontal_bands"
        assert boylat53["helm_interpretation_status"] == "helm_interpretation_manual_required"
        assert "LateralBuoy" in boylat53["helm_interpretation"]["text"]
        assert "green, red, green" in boylat53["helm_interpretation"]["text"]
        _assert_fail_closed(boylat53)

        topshq28 = _row(result, "TOPSHQ28")
        assert "SY(TOPSHQ28)" in topshq28["s52_instruction"]
        assert topshq28["s101_feature_type"] == "Daymark"
        assert topshq28["s101_rule_file"] == "PortrayalCatalog/Rules/Daymark.lua"
        assert topshq28["helm_symbol_recipe"]["shape_family"] == "daymark_panel"
        assert topshq28["helm_symbol_recipe"]["color_tokens"] == ["red", "black", "white"]
        assert topshq28["helm_symbol_recipe"]["pattern_token"] == "vertical_stripes"
        assert topshq28["s57_object"]["object_class"] == "DAYMAR"
        assert topshq28["helm_interpretation_status"] == "helm_interpretation_ready"
        assert "Daymark" in topshq28["helm_interpretation"]["text"]
        assert "daymark_panel" in topshq28["helm_interpretation"]["text"]
        if topshq28["s57_attribute_tuple"]["topmark_daymark_shape"] is not None:
            assert topshq28["s57_attribute_tuple"]["topmark_daymark_shape"] == "28"
        if "topmarkDaymarkShape" in topshq28["s101_attributes"]:
            assert topshq28["s101_attributes"]["topmarkDaymarkShape"] == "28"
        _assert_fail_closed(topshq28)

        topma114 = _row(result, "TOPMA114")
        assert topma114["s57_object"]["object_class"] == "TOPMAR"
        assert topma114["s101_crosswalk_class"] in {"s101_feature_equivalent", "s101_component_context_required"}
        assert topma114["s101_attributes"]["colour"] == ["red"]
        assert topma114["helm_symbol_recipe"]["shape_family"] == "topmark_standard"
        _assert_fail_closed(topma114)

        for symbol_id, feature in {
            "WRECKS01": "Wreck",
            "OBSTRN01": "Obstruction",
            "UWTROC04": "UnderwaterAwashRock",
        }.items():
            row = _row(result, symbol_id)
            assert row["s101_feature_type"] == feature
            assert row["s101_mapping_type"] == "direct_asset_match"
            assert row["resolver_status"] == "resolved_direct"
            assert row["s101_crosswalk_class"] == "s101_feature_equivalent"
            assert row["s101_rule_contract_status"] == "direct_symbol_contract_ready"
            assert row["helm_symbol_recipe"]["shape_family"] in {"wreck_symbol", "generic_chart_symbol", "rock_symbol"}
            _assert_fail_closed(row)

        for symbol_id in ["NMKINF02", "NMKREG01"]:
            row = _row(result, symbol_id)
            assert row["s57_object"]["object_class"] == "notmrk"
            assert row["s101_feature_type"] is None
            assert row["s101_rule_file"] is None
            assert row["s101_crosswalk_class"] == "non_s101_or_inland_extension"
            assert row["runtime_gate_summary"]["status"] in {"blocked", "manual_review_required"}
            assert "non_s101_or_inland_extension" in row["evidence_gap_reasons"]
            assert row["s101_rule_contract_status"] == "non_s101_or_extension_profile_required"
            assert row["helm_symbol_recipe"]["shape_family"] == "notice_mark"
            assert row["helm_interpretation_status"] == "helm_interpretation_manual_required"
            assert "non-S-101 or inland-extension profile" in row["helm_interpretation"]["text"]
            _assert_fail_closed(row)

        ais = _row(result, "AISVES01")
        assert ais["s101_crosswalk_class"] == "non_s101_runtime_construct"
        assert ais["s101_rule_contract_status"] == "non_s101_runtime_construct"
        assert ais["helm_symbol_recipe"]["shape_family"] == "ais_target"
        assert ais["helm_symbol_recipe_status"] == "manual_exception_required"
        assert ais["runtime_gate_summary"]["status"] in {"blocked", "manual_review_required"}
        assert "s52_display_construct_not_s57_feature" in ais["unresolved_reasons"]
        assert ais["helm_interpretation_status"] == "helm_interpretation_manual_required"
        assert "runtime/display construct" in ais["helm_interpretation"]["text"]
        _assert_fail_closed(ais)

        topshp09 = _row(result, "TOPSHP09")
        assert topshp09["s52_instruction"] == "SY(TOPSHP09);TE('%s','OBJNAM',2,1,2,'15110',-1,-1,CHBLK,21)"
        assert topshp09["s52_instruction_ast_status"] == "parsed"
        assert topshp09["s52_instruction_ast"]["symbols"] == ["TOPSHP09"]
        assert topshp09["s101_feature_type"] == "Daymark"
        assert topshp09["s101_rule_file"] == "PortrayalCatalog/Rules/Daymark.lua"
        assert topshp09["helm_symbol_recipe"]["shape_family"] == "daymark_panel"
        _assert_fail_closed(topshp09)

        quapos = _row(result, "QUAPOS01_TX_OBJNAM")
        assert quapos["s52_instruction"] == "SY(LNDARE01);CS(QUAPOS01);TX(OBJNAM,1,2,3,'15118',-1,-1,CHBLK,26)"
        assert quapos["s52_instruction_ast_status"] == "parsed_with_conditional_references"
        assert quapos["s52_instruction_ast"]["conditional_procedures"] == ["QUAPOS01"]
        assert quapos["s101_feature_type"] == "LandArea"
        assert quapos["helm_symbol_recipe"]["shape_family"] == "conditional_portrayal"
        assert quapos["helm_symbol_recipe_status"] == "manual_exception_required"
        _assert_fail_closed(quapos)

        arcsln01 = _row(result, "ARCSLN01")
        assert arcsln01["s101_feature_type"] == "ArchipelagicSeaLaneArea"
        assert arcsln01["s101_rule_file"] == "PortrayalCatalog/Rules/ArchipelagicSeaLaneArea.lua"
        assert arcsln01["s101_rule_contract_status"] == "documented_deviation_review"
        assert "missing_s101_feature_type" not in arcsln01["evidence_gap_reasons"]
        _assert_fail_closed(arcsln01)

        extension_or_component = _row(result, "BOYSPR65")
        assert extension_or_component["s101_crosswalk_class"] in {
            "non_s101_or_inland_extension",
            "s101_component_context_required",
        }
        assert extension_or_component["runtime_gate_summary"]["runtime_eligible"] is False
        assert extension_or_component["s101_attributes"]["colour"] == ["white", "red"]
        assert extension_or_component["helm_symbol_recipe"]["color_tokens"] == ["white", "red"]
        assert extension_or_component["helm_interpretation"]["validation"]["status"] == "passed"

        semantic_evidence_db._write(out, result)
        md.write_text(semantic_evidence_db._md(result))
        disk = json.loads(out.read_text())
        assert disk["coverage"]["rows"] == 824
        assert "Semantic Evidence DB View" in md.read_text()
        assert "browser and static proof pages display this payload only" in md.read_text()

    print("semantic evidence db: OK")


if __name__ == "__main__":
    main()
