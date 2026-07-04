"""Smoke Standard Generate Batch 91.

Run:  python3 -m forge.tests.test_standard_generate_batch91
"""
from __future__ import annotations

from pathlib import Path

from .. import standard_generate_batch91


ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    result = standard_generate_batch91.build(render_outputs=False)
    assert result["status"] == "semantic_hard_pile_generated_pending_judge_or_reference_gap_review"
    assert result["summary"]["generated"] == 24
    assert result["summary"]["reference_backed_pending_judge"] == 5
    assert result["summary"]["reference_gap_pending_source_review"] == 19
    assert result["summary"]["final_approved"] == 0
    assert {row["asset"] for row in result["symbols"]} == set(standard_generate_batch91.TARGETS)
    by_asset = {row["asset"]: row for row in result["symbols"]}
    assert by_asset["CLRLIN01"]["qa"]["visual_parity"] == "pending_llm_judge"
    assert by_asset["CLRLIN01"]["visual_examples"]["opencpn_render"]
    assert by_asset["ARCSLN01"]["qa"]["visual_parity"] == "pending_reference_gap_judge"
    assert not any(by_asset["ARCSLN01"]["visual_examples"].values())
    assert "M15 32 H49" in (ROOT / by_asset["WRECKS02"]["after_svg"]).read_text()
    for row in result["symbols"]:
        assert row["qa"]["final_approved"] is False
        assert (ROOT / row["after_svg"]).exists()
    assert (ROOT / "catalog" / "owned_repair_batch91.json").exists()
    assert (ROOT / "catalog" / "owned_repair_batch91.md").exists()
    print("standard generate batch 91: OK")


if __name__ == "__main__":
    main()
