"""Smoke the DB-backed Icon Forge review API.

Run:  python3 -m forge.tests.test_db_review_api
"""
from __future__ import annotations

from .. import db_review_api


def main() -> None:
    payload = db_review_api.build_review_payload(limit=25)
    assert payload["schema"] == "helm.iconforge.db_review_api.v1"
    assert payload["summary"]["total_candidates"] == 3057
    assert payload["summary"]["runtime_eligible"] == 0
    assert payload["summary"]["runtime_portrayal_rows"] == 0
    assert payload["pagination"]["returned"] == 25
    assert len(payload["source"]["db_sha256"]) == 64

    focused = db_review_api.build_review_payload(symbol_ids=["BOYPIL60", "BOYLAT25", "BCNLAT15", "TOPSHQ28", "ACHRES71"])
    rows = {row["symbol_id"]: row for row in focused["rows"]}
    for symbol_id in ["BOYPIL60", "BOYLAT25", "BCNLAT15", "TOPSHQ28", "ACHRES71"]:
        assert symbol_id in rows
        row = rows[symbol_id]
        assert row["opencpn"]["instruction"]
        assert row["s57"]["description"]
        assert row["s52"]["ast_status"] in {"parsed", "complete"}
        assert row["s101"]["mapping_type"]
        assert row["helm"]["interpretation_status"]
        assert row["helm"]["recipe_status"]
        assert row["qa"]["gates"]
        assert row["qa"]["runtime_eligible"] is False
        assert row["qa"]["style_contract"]["schema"] == "helm.iconforge.style_contract_gate.v1"
        assert row["qa"]["style_contract"]["gate_status"] in {"pass", "pending", "failed"}
        assert row["qa"]["colour_authority"]["schema"] == "helm.iconforge.colour_authority_contract.v1"
        assert row["qa"]["colour_authority"]["gate_status"] in {"pass", "blocked", "pending"}
        assert row["qa"]["authority_trace"]["schema"] == "helm.iconforge.authority_trace_gate.v1"
        assert row["qa"]["authority_trace"]["gate_status"] == "blocked"
        assert row["qa"]["authority_trace"]["runtime_blocker"] is True
        assert row["qa"]["authority_trace"]["blocker_summary"]["runtime_blocker"] is True
        assert row["qa"]["authority_trace"]["gap_classifications"]
        assert all(item["blocker_category"] for item in row["qa"]["authority_trace"]["gap_classifications"])
        assert row["qa"]["authority_trace"]["s52_lookup"]["instruction"]
        assert row["qa"]["authority_trace"]["s57_dictionary_decode"]["source"]
        assert row["qa"]["authority_trace"]["s101_mapping"]["source_boundary"]
        assert row["approval"]["controls"]["save_signoff"] == "/api/save-signoff"

    assert rows["BOYPIL60"]["s101"]["feature_type"] == "LateralBuoy"
    assert rows["BOYPIL60"]["s101"]["attributes"]["colour"] == ["red"]
    assert rows["BOYPIL60"]["qa"]["style_contract"]["status"] in {"style_pass", "style_review"}
    assert rows["BOYPIL60"]["qa"]["colour_authority"]["feature_colour_sequence"] == ["red"]
    assert rows["BOYPIL60"]["qa"]["colour_authority"]["visual_colour_sequence"] == ["red"]
    assert rows["BOYLAT25"]["qa"]["colour_authority"]["feature_colour_sequence"] == ["red", "green"]
    assert rows["BOYLAT25"]["qa"]["colour_authority"]["visual_colour_sequence"] == ["red", "green"]
    assert rows["BOYLAT25"]["qa"]["colour_authority"]["status"] == "aligned"
    assert rows["BOYLAT25"]["qa"]["authority_trace"]["s101_mapping"]["feature_type"] == "LateralBuoy"
    assert "authority_trace:runtime_candidate_not_eligible" in rows["BOYLAT25"]["qa"]["authority_trace"]["reason_codes"]
    assert rows["BOYLAT25"]["qa"]["authority_trace"]["blocker_summary"]["blocker_category_counts"]["runtime_eligibility_blocker"] == 1
    assert any(
        item["blocker_category"] == "s101_feature_catalogue_source_missing"
        for item in rows["BOYLAT25"]["qa"]["authority_trace"]["gap_classifications"]
    )
    assert rows["BCNLAT15"]["qa"]["colour_authority"]["status"] == "feature_colour_dropped"
    assert rows["BCNLAT15"]["qa"]["colour_authority"]["gate_status"] == "blocked"
    assert rows["BCNLAT15"]["qa"]["colour_authority"]["runtime_blocker"] is True
    assert rows["BCNLAT15"]["qa"]["colour_authority"]["missing_feature_colours"] == ["green"]
    assert rows["BCNLAT15"]["qa"]["colour_authority"]["extra_visual_colours"] == ["white"]
    assert rows["TOPSHQ28"]["s101"]["feature_type"] == "Daymark"
    assert rows["TOPSHQ28"]["s101"]["attributes"]["topmarkDaymarkShape"] == "28"
    assert rows["ACHRES71"]["helm"]["recipe_status"] == "manual_exception_required"

    helm_image = db_review_api.image_path_for("BOYPIL60", "helm")
    s101_image = db_review_api.image_path_for("BOYPIL60", "s101")
    assert helm_image and helm_image.exists()
    assert s101_image and s101_image.exists()

    unknown = db_review_api._colour_authority_gate("TEST01", {
        "schema": "helm.iconforge.colour_authority_contract.v1",
        "status": "future_status",
        "gate_status": "surprise",
        "runtime_blocker": False,
        "reason_codes": [],
    })
    assert unknown["gate_status"] == "blocked"
    assert unknown["runtime_blocker"] is True
    assert "colour_authority:unknown_status:future_status" in unknown["reason_codes"]
    assert "colour_authority:unknown_gate_status:surprise" in unknown["reason_codes"]

    print("db review api: OK")


if __name__ == "__main__":
    main()
