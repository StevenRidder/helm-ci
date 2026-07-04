"""Smoke the S-101 / Aqua Map / OpenCPN candidate pile.

Run:  python -m forge.tests.test_triad_reference_candidate_pack
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import triad_reference_candidate_pack


ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    result = triad_reference_candidate_pack.build(render_outputs=False)
    summary = result["summary"]

    assert result["status"] == "candidate_pile_pending_llm_judge"
    assert summary["triad_rows"] == 824
    assert summary["generated_candidate_svgs"] == 824
    assert summary["reference_backed_judge_queue_rows"] == 783
    assert summary["hard_pile_no_svg_candidate"] == 0
    assert summary["s101_rows"] >= 244
    assert summary["aquamap_rows"] >= 60
    assert summary["opencpn_rows"] == 777
    assert summary["reference_gap_candidate_rows"] == 41
    assert summary["rendered_candidate_pngs"] == 0
    assert len(result["judge_queue"]) == 783
    assert len(result["hard_pile"]) == 0

    by_asset = {row["id"]: row for row in result["rows"]}
    smcfac02 = by_asset["SMCFAC02"]
    assert smcfac02["triad_coverage"] == {
        "any": True,
        "aquamap": True,
        "opencpn": True,
        "s101": True,
    }
    assert smcfac02["asset"]["canonical"] == "assets/svg/triad_generated/SMCFAC02.svg"
    assert smcfac02["qa"]["visual_parity"] in {
        "pending_llm_judge",
        "pending_visual_model_and_human_review",
        "repaired_pending_judge_rerun",
    }
    assert smcfac02["qa"]["final_approved"] is False

    judge = next(item for item in result["judge_queue"] if item["asset"] == "SMCFAC02")
    assert judge["candidate_svg"] == "assets/svg/triad_generated/SMCFAC02.svg"
    assert {ref["group"] for ref in judge["reference_candidates"]} >= {"s101", "aquamap", "opencpn"}
    assert judge["judge_contract"]["on_fail"].startswith("enqueue renderer repair")

    achare02 = by_asset["ACHARE02"]
    assert achare02["asset"]["canonical"] == "assets/svg/triad_generated/ACHARE02.svg"
    repaired = ROOT / "assets" / "svg" / "owned_repair_batch8" / "ACHARE02.svg"
    assert repaired.exists()
    assert (ROOT / "assets" / "svg" / "triad_generated" / "ACHARE02.svg").read_text() == (
        repaired
    ).read_text()
    assert "repaired_pending_judge_rerun" == achare02["qa"]["visual_parity"]
    assert achare02["qa"]["semantic_pass"] is False

    cblsub06 = by_asset["CBLSUB06"]
    assert cblsub06["asset"]["canonical"] == "assets/svg/triad_generated/CBLSUB06.svg"
    assert cblsub06["qa"]["visual_parity"] == "repaired_pending_judge_rerun"
    assert cblsub06["asset"]["source_batch"] == "catalog/owned_repair_batch93.json"

    fshhav02 = by_asset["FSHHAV02"]
    assert fshhav02["asset"]["canonical"] == "assets/svg/triad_generated/FSHHAV02.svg"
    assert fshhav02["qa"]["visual_parity"] == "repaired_pending_judge_rerun"
    assert fshhav02["asset"]["source_batch"] == "catalog/owned_repair_batch94.json"

    rcrtcl14 = by_asset["RCRTCL14"]
    assert rcrtcl14["asset"]["canonical"] == "assets/svg/triad_generated/RCRTCL14.svg"
    assert rcrtcl14["qa"]["visual_parity"] == "repaired_pending_judge_rerun"
    assert rcrtcl14["asset"]["source_batch"] == "catalog/owned_repair_batch94.json"

    clrlin01 = by_asset["CLRLIN01"]
    assert clrlin01["asset"]["canonical"] == "assets/svg/triad_generated/CLRLIN01.svg"
    assert clrlin01["qa"]["visual_parity"] == "repaired_pending_judge_rerun"
    assert clrlin01["asset"]["source_batch"] == "catalog/owned_repair_batch92.json"

    dquala11 = by_asset["DQUALA11"]
    assert dquala11["asset"]["canonical"] == "assets/svg/triad_generated/DQUALA11.svg"
    assert dquala11["qa"]["visual_parity"] == "repaired_pending_judge_rerun"
    assert dquala11["asset"]["source_batch"] == "catalog/owned_repair_batch93.json"

    bcncon81 = by_asset["BCNCON81"]
    assert bcncon81["asset"]["canonical"] == "assets/svg/triad_generated/BCNCON81.svg"
    assert bcncon81["qa"]["visual_parity"] == "repaired_pending_judge_rerun"
    assert bcncon81["asset"]["source_batch"] == "catalog/owned_repair_batch97.json"

    boyspp50 = by_asset["boyspp50"]
    assert boyspp50["asset"]["canonical"] == "assets/svg/triad_generated/boyspp50.svg"
    assert boyspp50["qa"]["visual_parity"] == "repaired_pending_judge_rerun"
    assert boyspp50["asset"]["source_batch"] == "catalog/owned_repair_batch97.json"

    arcsln01 = by_asset["ARCSLN01"]
    assert arcsln01["asset"]["canonical"] == "assets/svg/triad_generated/ARCSLN01.svg"
    assert arcsln01["qa"]["visual_parity"] == "pending_reference_gap_judge"
    assert arcsln01["asset"]["source_batch"] == "catalog/owned_repair_batch91.json"

    saved = json.loads((ROOT / "catalog" / "triad_reference_candidate_pack.json").read_text())
    assert saved["summary"]["generated_candidate_svgs"] == 824
    assert (ROOT / "catalog" / "triad_reference_candidate_table.csv").exists()
    assert (ROOT / "out" / "triad_reference_candidate_pack" / "judge_queue.json").exists()
    print("triad reference candidate pack: OK")


if __name__ == "__main__":
    main()
