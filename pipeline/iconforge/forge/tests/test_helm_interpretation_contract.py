"""Smoke the FORGE-29 Helm interpretation contract.

Run:
  python3 -m forge.tests.test_helm_interpretation_contract
"""
from __future__ import annotations

from copy import deepcopy

from .. import helm_interpretation_contract, semantic_evidence_db


def _row(result: dict, symbol_id: str) -> dict:
    for row in result["rows"]:
        if row["symbol_id"] == symbol_id:
            return row
    raise AssertionError(f"missing symbol row {symbol_id}")


def _assert_text_has(row: dict, *needles: str) -> None:
    text = row["helm_interpretation"]["text"]
    for needle in needles:
        assert needle in text, needle


def main() -> None:
    semantic = semantic_evidence_db.build()
    contract = helm_interpretation_contract.build()

    assert contract["schema"] == "helm.forge.helm-interpretation-contract.v1"
    assert contract["status"] == "provisional_helm_interpretation_contract_ready"
    assert contract["versions"]["interpretation"] == helm_interpretation_contract.INTERPRETATION_VERSION
    assert contract["versions"]["prompt"] == helm_interpretation_contract.PROMPT_VERSION
    assert contract["versions"]["output_schema"] == helm_interpretation_contract.OUTPUT_SCHEMA_VERSION
    assert contract["coverage"]["rows"] == 824
    assert contract["coverage"]["status_counts"] == {
        "helm_interpretation_manual_required": 325,
        "helm_interpretation_pending_evidence": 44,
        "helm_interpretation_ready": 455,
    }
    assert contract["coverage"]["validation_counts"] == {"passed": 824}
    assert contract["consumer_contract"]["backend_db_source_of_truth"] is True
    assert contract["consumer_contract"]["browser_generation_allowed"] is False
    assert contract["consumer_contract"]["llm_page_load_generation_allowed"] is False
    assert contract["prompt_contract"]["generation_mode"] == "deterministic_backend_batch"
    assert contract["prompt_contract"]["llm_page_load_generation_allowed"] is False
    assert "text" in contract["output_schema"]["required_fields"]

    for row in semantic["rows"]:
        interpretation = row["helm_interpretation"]
        assert row["helm_interpretation_status"] == interpretation["status"]
        assert interpretation["version"] == helm_interpretation_contract.INTERPRETATION_VERSION
        assert interpretation["validation"]["status"] == "passed"
        assert interpretation["browser_generation_allowed"] is False
        assert interpretation["backend_resolved"] is True
        assert interpretation["runtime_export_allowed"] is False
        assert row["consumer_contract"]["browser_interpretation_generation_allowed"] is False
        assert row["runtime_gate_summary"]["helm_interpretation_status"] == interpretation["status"]
        assert row["runtime_gate_summary"]["helm_interpretation_ready"] == (
            interpretation["status"] == helm_interpretation_contract.READY
        )
        assert row["proof_page_payload"]["helm_interpretation"]["text"] == interpretation["text"]

    boycan60 = _row(semantic, "BOYCAN60")
    assert boycan60["helm_interpretation_status"] == "helm_interpretation_ready"
    _assert_text_has(
        boycan60,
        "BOYCAN60",
        "BOYSPP",
        "SpecialPurposeGeneralBuoy",
        "buoy_can",
        "red",
        "solid",
        "SY(BOYCAN60)",
        "Clean-room/render note",
    )

    boylat53 = _row(semantic, "BOYLAT53")
    assert boylat53["helm_interpretation_status"] == "helm_interpretation_manual_required"
    _assert_text_has(
        boylat53,
        "BOYLAT53",
        "LateralBuoy",
        "buoy_generic",
        "green, red, green",
        "horizontal_bands",
        "non-S-101 or inland-extension profile",
    )

    topshq28 = _row(semantic, "TOPSHQ28")
    assert topshq28["helm_interpretation_status"] == "helm_interpretation_ready"
    _assert_text_has(
        topshq28,
        "TOPSHQ28",
        "DAYMAR",
        "Daymark",
        "daymark_panel",
        "red, black, white",
        "vertical_stripes",
    )

    nmkinf02 = _row(semantic, "NMKINF02")
    assert nmkinf02["helm_interpretation_status"] == "helm_interpretation_manual_required"
    _assert_text_has(
        nmkinf02,
        "NMKINF02",
        "notice_mark",
        "non-S-101 or inland-extension profile",
        "white, black",
    )

    bcncon81 = _row(semantic, "BCNCON81")
    assert bcncon81["helm_interpretation_status"] == "helm_interpretation_pending_evidence"
    assert "helm_symbol_recipe:recipe_missing" in bcncon81["helm_interpretation"]["reason_codes"]
    _assert_text_has(bcncon81, "BCNCON81", "beacon_general", "blue, red, white, blue")

    ais = _row(semantic, "AISVES01")
    assert ais["helm_interpretation_status"] == "helm_interpretation_manual_required"
    _assert_text_has(ais, "AISVES01", "ais_target", "runtime/display construct")

    tampered = deepcopy(boycan60["helm_interpretation"])
    tampered["required_values"]["color_tokens"] = ["green"]
    verdict = helm_interpretation_contract.validate_interpretation(boycan60, tampered)
    assert verdict["status"] == "failed"
    assert "conflicting_required_value:color_tokens" in verdict["reason_codes"]

    tampered = deepcopy(boycan60["helm_interpretation"])
    tampered["text"] = tampered["text"].replace("buoy_can", "wrong_shape")
    verdict = helm_interpretation_contract.validate_interpretation(boycan60, tampered)
    assert verdict["status"] == "failed"
    assert "text_missing:shape_family:buoy_can" in verdict["reason_codes"]

    print("helm interpretation contract: OK")


if __name__ == "__main__":
    main()
