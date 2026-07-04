"""Smoke the normalized source table.

Run:  python -m forge.tests.test_standard_source_table
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_source_table


ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    result = standard_source_table.build()
    summary = result["summary"]

    assert result["status"] == "normalized_source_table_routing_enforced"
    assert summary["rows"] == 824
    assert summary["judge_queue_rows"] == 798
    assert summary["repair_queue_rows"] == 0
    assert summary["routed_queue_rows"] == 26
    assert summary["opencpn_rows"] == 777
    assert summary["s101_rows"] >= 244
    assert summary["aquamap_rows"] >= 100
    assert summary["opencpn_definitions_total"] >= 824
    assert summary["opencpn_lookup_links_total"] >= 700

    by_asset = {row["asset"]: row for row in result["rows"]}
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
    ]:
        assert dirty not in serialized

    achare02 = by_asset["ACHARE02"]
    assert achare02["source_table_id"] == "opencpn-s52:ACHARE02"
    assert achare02["opencpn_s52_spine"]["definitions"][0]["bitmap"]["graphics_location"]
    assert achare02["opencpn_s52_spine"]["definitions"][0]["color_ref"]
    assert achare02["opencpn_s52_spine"]["lookup_count"] >= 1
    assert achare02["s57_structure"]["s52_instruction"]
    assert achare02["reference_providers"]["s101"]
    assert achare02["reference_providers"]["aquamap"]
    assert achare02["reference_providers"]["opencpn_render"]
    assert achare02["helm_candidate"]["canonical_svg"] == "assets/svg/triad_generated/ACHARE02.svg"
    assert achare02["semantic_brief"]["required_shape"]
    assert achare02["semantic_brief"]["brief"].startswith("ACHARE02 is")
    assert achare02["helm_candidate"]["candidate_status"] in {
        "judge_pass_pending_final_approval",
        "judge_fail_repair_queue",
        "repaired_pending_judge_rerun",
        "repaired_pending_shape_rerun",
        "shape_fail_repair_queue",
        "shape_pass_pending_visual_rerun",
        "chart1_parity_witness_needed",
        "witness_needed_official_symbol",
        "manual_policy_exception",
        "style_primitive_registry",
        "portrayal_rule_registry",
    }

    boycan72 = by_asset["BOYCAN72"]
    assert "can/cylindrical" in boycan72["semantic_brief"]["required_shape"]
    assert boycan72["semantic_brief"]["required_colours"] == ["red", "green", "red"]
    assert "horizontal bands" in boycan72["semantic_brief"]["colour_pattern"]

    boycon67 = by_asset["BOYCON67"]
    assert "conical/nun" in boycon67["semantic_brief"]["required_shape"]
    assert "Conical/nun buoy rows" in " ".join(boycon67["semantic_brief"]["safety_invariants"])

    danger53 = by_asset["DANGER53"]
    assert danger53["helm_candidate"]["candidate_status"] == "witness_needed_official_symbol"
    assert danger53["helm_candidate"]["pre_routing_candidate_status"] == "judge_fail_repair_queue"
    assert danger53["batch98_routing"]["routing_bucket"] == "witness_needed_official_symbol"
    assert danger53["repair_queue_item"] is None

    cblsub06 = by_asset["CBLSUB06"]
    assert cblsub06["helm_candidate"]["candidate_status"] == "judge_pass_pending_final_approval"
    assert cblsub06["helm_candidate"]["source_batch"] == "catalog/owned_repair_batch93.json"
    assert cblsub06["repair_queue_item"] is None

    fshhav02 = by_asset["FSHHAV02"]
    assert fshhav02["helm_candidate"]["candidate_status"] == "judge_pass_pending_final_approval"
    assert fshhav02["helm_candidate"]["source_batch"] == "catalog/owned_repair_batch94.json"
    assert fshhav02["repair_queue_item"] is None

    rcrtcl14 = by_asset["RCRTCL14"]
    assert rcrtcl14["helm_candidate"]["candidate_status"] == "judge_pass_pending_final_approval"
    assert rcrtcl14["helm_candidate"]["source_batch"] == "catalog/owned_repair_batch94.json"
    assert rcrtcl14["repair_queue_item"] is None

    clrlin01 = by_asset["CLRLIN01"]
    assert clrlin01["helm_candidate"]["candidate_status"] == "judge_pass_pending_final_approval"
    assert clrlin01["helm_candidate"]["source_batch"] == "catalog/owned_repair_batch92.json"
    assert clrlin01["reference_providers"]["opencpn_render"]
    assert clrlin01["repair_queue_item"] is None

    dquala11 = by_asset["DQUALA11"]
    assert dquala11["helm_candidate"]["candidate_status"] == "judge_pass_pending_final_approval"
    assert dquala11["helm_candidate"]["source_batch"] == "catalog/owned_repair_batch93.json"
    assert dquala11["repair_queue_item"] is None

    arcsln01 = by_asset["ARCSLN01"]
    assert arcsln01["helm_candidate"]["candidate_status"] == "style_primitive_registry"
    assert arcsln01["helm_candidate"]["pre_routing_candidate_status"] == "pending_judge"
    assert arcsln01["helm_candidate"]["source_batch"] == "catalog/owned_repair_batch91.json"
    assert not any(arcsln01["reference_providers"].values())
    assert arcsln01["batch98_routing"]["routing_bucket"] == "style_primitive_registry"
    assert arcsln01["repair_queue_item"] is None

    for asset in ("TOPSHP09", "TOPSHP33"):
        row = by_asset[asset]
        assert row["helm_candidate"]["candidate_status"] == "judge_pass_pending_final_approval"
        assert row["helm_candidate"]["source_batch"] == "catalog/owned_repair_batch84.json"
        assert row["repair_queue_item"] is None

    topshp09 = by_asset["TOPSHP09"]
    assert topshp09["source_table_id"] == "opencpn-s52:TOPSHP09"
    assert topshp09["s57_structure"]["s52_instruction"] == "SY(TOPSHP09);TE('%s','OBJNAM',2,1,2,'15110',-1,-1,CHBLK,21)"
    assert topshp09["opencpn_s52_spine"]["lookup_count"] == 1
    assert topshp09["opencpn_s52_spine"]["lookups"][0]["instruction"] == topshp09["s57_structure"]["s52_instruction"]

    for asset in ("VEHTRF01",):
        row = by_asset[asset]
        assert row["helm_candidate"]["candidate_status"] == "witness_needed_official_symbol"
        assert row["helm_candidate"]["pre_routing_candidate_status"] == "judge_fail_repair_queue"
        assert row["helm_candidate"]["source_batch"] == "catalog/owned_repair_batch84.json"
        assert row["batch98_routing"]["routing_bucket"] == "witness_needed_official_symbol"
        assert row["repair_queue_item"] is None

    for asset in ("BCNCON81", "boyspp50"):
        row = by_asset[asset]
        assert row["helm_candidate"]["candidate_status"] == "chart1_parity_witness_needed"
        assert row["helm_candidate"]["pre_routing_candidate_status"] == "chart1_fail_repair_queue"
        assert row["helm_candidate"]["source_batch"] == "catalog/owned_repair_batch97.json"
        assert row["chart1_parity_gate"]["status"] == "blocked_by_chart1_parity_gate"
        assert row["batch98_routing"]["routing_bucket"] == "chart1_parity_witness_needed"
        assert row["repair_queue_item"] is None

    towers74 = by_asset["TOWERS74"]
    assert towers74["helm_candidate"]["candidate_status"] == "judge_pass_pending_final_approval"
    assert towers74["helm_candidate"]["source_batch"] == "catalog/owned_repair_batch95.json"
    assert towers74["s57_structure"]["s52_instruction"] == "SY(TOWERS74);TX(OBJNAM,3,2,2,'15110',1,-1,CHBLK,26)"
    assert towers74["opencpn_s52_spine"]["lookup_count"] == 1
    assert towers74["repair_queue_item"] is None

    quapos = by_asset["QUAPOS01_TX_OBJNAM"]
    assert quapos["s57_structure"]["s52_instruction"] == "SY(LNDARE01);CS(QUAPOS01);TX(OBJNAM,1,2,3,'15118',-1,-1,CHBLK,26)"
    assert quapos["opencpn_s52_spine"]["lookup_count"] == 2

    for asset in ("BCNGEN68", "BCNGEN79", "BOYMOR03", "BOYSPP15"):
        row = by_asset[asset]
        assert row["helm_candidate"]["candidate_status"] == "judge_pass_pending_final_approval"
        assert row["helm_candidate"]["source_batch"] == "catalog/owned_repair_batch83.json"
        assert row["repair_queue_item"] is None

    for asset in ("BOYLAT26", "BOYLAT27"):
        row = by_asset[asset]
        assert row["helm_candidate"]["candidate_status"] == "judge_pass_pending_final_approval"
        assert row["helm_candidate"]["source_batch"] == "catalog/owned_repair_batch68.json"
        assert row["chart1_parity_gate"] is None
        assert row["repair_queue_item"] is None

    for asset in ("BOYSPR02", "BOYSPR69"):
        row = by_asset[asset]
        assert row["helm_candidate"]["candidate_status"] == "judge_pass_pending_final_approval"
        assert row["helm_candidate"]["source_batch"] == "catalog/owned_repair_batch69.json"
        assert row["chart1_parity_gate"] is None
        assert row["repair_queue_item"] is None

    for asset in ("TOPSHP00", "TOPSHP21"):
        row = by_asset[asset]
        assert row["helm_candidate"]["candidate_status"] == "judge_pass_pending_final_approval"
        assert row["helm_candidate"]["source_batch"] == "catalog/owned_repair_batch70.json"
        assert row["repair_queue_item"] is None

    for asset in ("TOPMA100", "TOPMA117"):
        row = by_asset[asset]
        assert row["helm_candidate"]["candidate_status"] == "judge_pass_pending_final_approval"
        assert row["helm_candidate"]["source_batch"] == "catalog/owned_repair_batch71.json"
        assert row["repair_queue_item"] is None

    for asset in ("TOPMAR87", "TOPMAR88"):
        row = by_asset[asset]
        assert row["helm_candidate"]["candidate_status"] == "judge_pass_pending_final_approval"
        assert row["helm_candidate"]["source_batch"] == "catalog/owned_repair_batch72.json"
        assert row["repair_queue_item"] is None

    for asset in ("BOYSUP01", "BOYSUP66"):
        row = by_asset[asset]
        assert row["helm_candidate"]["candidate_status"] == "judge_pass_pending_final_approval"
        assert row["helm_candidate"]["source_batch"] == "catalog/owned_repair_batch73.json"
        assert row["repair_queue_item"] is None

    for asset in ("TERMNL01", "TERMNL12"):
        row = by_asset[asset]
        assert row["helm_candidate"]["candidate_status"] == "judge_pass_pending_final_approval"
        assert row["helm_candidate"]["source_batch"] == "catalog/owned_repair_batch74.json"
        assert row["repair_queue_item"] is None

    for asset in ("BOYBAR01", "BOYBAR62"):
        row = by_asset[asset]
        assert row["helm_candidate"]["candidate_status"] == "judge_pass_pending_final_approval"
        assert row["helm_candidate"]["source_batch"] == "catalog/owned_repair_batch76.json"
        assert row["repair_queue_item"] is None

    queue_item = next(item for item in result["judge_queue"] if item["asset"] == "ACHARE02")
    assert queue_item["opencpn_s52_spine"]["definitions"]
    assert queue_item["reference_providers"]["opencpn_render"]
    assert queue_item["semantic_brief"]["required_shape"]
    assert queue_item["judge_contract"]["semantic_gate"].startswith("first confirm")
    assert queue_item["judge_contract"]["on_fail"].startswith("write critique")

    shape_item = next(item for item in result["semantic_shape_judge_queue"] if item["asset"] == "BOYCAN72")
    assert shape_item["status"] == "queued_for_shape_semantic_judge"
    assert "can/cylindrical" in shape_item["semantic_brief"]["required_shape"]
    assert shape_item["judge_contract"]["approval"].startswith("candidate uses the correct")

    saved = json.loads((ROOT / "catalog" / "standard_source_table.json").read_text())
    assert saved["summary"]["rows"] == 824
    assert saved["summary"]["candidate_status_counts"] == {
        "judge_pass_pending_final_approval": 798,
        "chart1_parity_witness_needed": 2,
        "manual_policy_exception": 2,
        "portrayal_rule_registry": 15,
        "style_primitive_registry": 4,
        "witness_needed_official_symbol": 3,
    }
    assert saved["summary"]["routing_bucket_counts"] == {
        "chart1_parity_witness_needed": 2,
        "manual_policy_exception": 2,
        "portrayal_rule_registry": 15,
        "style_primitive_registry": 4,
        "witness_needed_official_symbol": 3,
    }
    assert (ROOT / "catalog" / "standard_source_table.csv").exists()
    assert (ROOT / "out" / "standard_source_table" / "judge_queue.json").exists()
    assert (ROOT / "catalog" / "standard_semantic_shape_judge_queue.json").exists()
    assert (ROOT / "catalog" / "standard_routed_queue.json").exists()
    print("standard source table: OK")


if __name__ == "__main__":
    main()
