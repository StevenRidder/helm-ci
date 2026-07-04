"""Smoke the FORGE-27 S-52/S-101 rule-contract artifact.

Run:
  python3 -m forge.tests.test_s52_s101_rule_contract
"""
from __future__ import annotations

from copy import deepcopy

from .. import s52_s101_rule_contract, semantic_evidence_db


def _row(result: dict, symbol_id: str) -> dict:
    for row in result["rows"]:
        if row["symbol_id"] == symbol_id:
            return row
    raise AssertionError(f"missing symbol row {symbol_id}")


def main() -> None:
    semantic = semantic_evidence_db.build()
    contract = s52_s101_rule_contract.build()

    assert contract["schema"] == "helm.forge.s52-s101-rule-contract.v1"
    assert contract["status"] == "provisional_rule_contract_ready"
    assert contract["coverage"]["rows"] == 824
    assert contract["coverage"]["runtime_contract_ready"] == 0
    assert contract["coverage"]["runtime_contract_blocked_or_pending"] == 824
    assert contract["consumer_contract"]["runtime_export_allowed"] is False
    assert contract["coverage"]["s52_instruction_ast_status_counts"] == {
        "parsed": 776,
        "parsed_with_conditional_references": 48,
    }
    assert contract["coverage"]["s101_rule_contract_status_counts"] == {
        "catalogue_rule_reference_ready": 90,
        "direct_symbol_contract_ready": 244,
        "documented_deviation_review": 108,
        "non_s101_or_extension_profile_required": 123,
        "non_s101_runtime_construct": 44,
        "rule_contract_ready": 215,
    }
    assert "malformed" not in contract["coverage"]["s52_instruction_ast_status_counts"]
    assert "missing_s101_feature_type" not in contract["coverage"]["s101_rule_contract_status_counts"]
    assert contract["coverage"]["s52_command_counts"]["TX"] == 82

    for row in semantic["rows"]:
        assert row["s52_instruction_ast_status"]
        assert row["s101_rule_contract_status"]
        assert row["s52_instruction_ast"]["status"] == row["s52_instruction_ast_status"]
        assert row["s101_rule_contract"]["status"] == row["s101_rule_contract_status"]
        assert row["runtime_gate_summary"]["runtime_eligible"] is False
        assert row["runtime_gate_summary"]["s101_rule_contract_runtime_ready"] is False

    boycan60 = _row(semantic, "BOYCAN60")
    assert boycan60["s52_instruction_ast_status"] == "parsed"
    assert boycan60["s52_instruction_ast"]["symbols"] == ["BOYCAN60"]
    assert boycan60["s101_rule_contract_status"] == "rule_contract_ready"
    assert boycan60["s101_rule_contract"]["feature_type"] == "SpecialPurposeGeneralBuoy"
    assert boycan60["s101_rule_contract"]["rule_file"] == "PortrayalCatalog/Rules/SpecialPurposeGeneralBuoy.lua"
    assert boycan60["s101_rule_contract"]["attributes"]["buoyShape"] == "can"
    assert boycan60["s101_rule_contract"]["filename_gap"] == {
        "direct_symbol_missing": True,
        "interpretation": "expected_rule_derived_gap",
        "is_error": False,
    }

    cblsub06 = _row(semantic, "CBLSUB06")
    assert cblsub06["s101_rule_contract_status"] == "catalogue_rule_reference_ready"
    assert cblsub06["s101_rule_contract"]["filename_gap"]["interpretation"] == "catalogue_rule_reference_gap"
    assert cblsub06["s101_rule_contract"]["filename_gap"]["is_error"] is False
    assert cblsub06["s101_feature_type"] == "CableSubmarine"

    topshq28 = _row(semantic, "TOPSHQ28")
    assert topshq28["s52_instruction_ast"]["symbols"] == ["TOPSHQ28"]
    assert topshq28["s101_rule_contract_status"] == "rule_contract_ready"
    assert topshq28["s101_rule_contract"]["rule_file"] == "PortrayalCatalog/Rules/Daymark.lua"

    conditional = next(
        row for row in semantic["rows"]
        if "RESTRN01" in row["s52_instruction_ast"].get("conditional_procedures", [])
    )
    assert conditional["s52_instruction_ast_status"] == "parsed_with_conditional_references"
    assert conditional["s52_instruction_ast"]["conditional_procedures"] == ["RESTRN01"]
    assert conditional["s52_instruction_ast"]["commands"][0]["command"] in {"SY", "AP", "CS", "LS"}

    topshp09 = _row(semantic, "TOPSHP09")
    assert topshp09["s52_instruction"] == "SY(TOPSHP09);TE('%s','OBJNAM',2,1,2,'15110',-1,-1,CHBLK,21)"
    assert topshp09["s52_instruction_ast_status"] == "parsed"
    assert topshp09["s52_instruction_ast"]["symbols"] == ["TOPSHP09"]
    assert topshp09["s52_instruction_ast"]["text_commands"][0]["format"] == "'%s'"
    assert topshp09["s52_instruction_ast"]["text_commands"][0]["colour_token"] == "CHBLK"
    assert topshp09["s52_instruction_ast"]["text_commands"][0]["display_priority"] == "21"

    towers74 = _row(semantic, "TOWERS74")
    assert towers74["s52_instruction"] == "SY(TOWERS74);TX(OBJNAM,3,2,2,'15110',1,-1,CHBLK,26)"
    assert towers74["s52_instruction_ast_status"] == "parsed"
    assert towers74["s52_instruction_ast"]["text_commands"][0] == {
        "colour_token": "CHBLK",
        "display_priority": "26",
        "format": None,
        "text_source": "OBJNAM",
    }

    arcsln01 = _row(semantic, "ARCSLN01")
    assert arcsln01["s101_rule_contract_status"] == "documented_deviation_review"
    assert arcsln01["s101_feature_type"] == "ArchipelagicSeaLaneArea"
    assert arcsln01["s101_rule_file"] == "PortrayalCatalog/Rules/ArchipelagicSeaLaneArea.lua"

    assert _row(semantic, "WRECKS01")["s101_rule_contract_status"] == "direct_symbol_contract_ready"
    assert _row(semantic, "NMKINF02")["s101_rule_contract_status"] == "non_s101_or_extension_profile_required"
    assert _row(semantic, "AISVES01")["s101_rule_contract_status"] == "non_s101_runtime_construct"
    assert _row(semantic, "LOWACC41")["s101_rule_contract_status"] == "non_s101_runtime_construct"
    assert _row(semantic, "TIDINF51")["s101_rule_contract_status"] == "non_s101_runtime_construct"

    unsupported_command = s52_s101_rule_contract.parse_s52_instruction("ZZ(FOO)")
    assert unsupported_command["status"] == "unsupported_command"
    assert unsupported_command["unsupported_commands"] == ["ZZ"]

    unsupported_conditional = s52_s101_rule_contract.parse_s52_instruction("CS(UNKNOWN99)")
    assert unsupported_conditional["status"] == "unsupported_conditional_procedure"
    assert unsupported_conditional["unsupported_conditional_procedures"] == ["UNKNOWN99"]

    malformed_instruction = s52_s101_rule_contract.parse_s52_instruction("SY(BAD")
    assert malformed_instruction["status"] == "malformed"

    direct_tx = s52_s101_rule_contract.parse_s52_instruction("TX(OBJNAM,2,1,2,'14106',-1,-1,CHBLK,21)")
    assert direct_tx["text_commands"][0] == {
        "colour_token": "CHBLK",
        "display_priority": "21",
        "format": None,
        "text_source": "OBJNAM",
    }

    missing_rule = deepcopy(boycan60)
    missing_rule["s101_rule_file"] = None
    missing_rule_contract = s52_s101_rule_contract.s101_rule_contract_for_row(missing_rule)
    assert missing_rule_contract["status"] == "missing_s101_rule_file"

    malformed_attrs = deepcopy(boycan60)
    malformed_attrs["s101_attributes"]["colour"] = "red"
    malformed_attr_contract = s52_s101_rule_contract.s101_rule_contract_for_row(malformed_attrs)
    assert malformed_attr_contract["status"] == "malformed_attribute_tuple"
    assert "s101_colour_not_list" in malformed_attr_contract["attribute_validation"]["errors"]

    print("S-52/S-101 rule contract: OK")


if __name__ == "__main__":
    main()
