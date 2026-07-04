"""Smoke Standard Repair Batch 3.

Run:  python -m forge.tests.test_standard_repair_batch3
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch3


ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    result = standard_repair_batch3.build(render_outputs=False)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["source_queue_rows"] == 35
    assert result["summary"]["failed_repaired"] == 34
    assert result["summary"]["blocked_or_skipped"] == 1

    by_asset = {row["asset"]: row for row in result["symbols"]}
    assert "BCNCON81" not in by_asset
    assert result["blockers"] == [
        {
            "asset": "BCNCON81",
            "required_change": result["blockers"][0]["required_change"],
            "safety_reason_codes": result["blockers"][0]["safety_reason_codes"],
            "status": "hard_blocked_missing_exact_reference",
        }
    ]

    boycan79 = (ROOT / by_asset["BOYCAN79"]["after_svg"]).read_text()
    assert by_asset["BOYCAN79"]["source_judge"] == "catalog/standard_shape_judge_batch_004_rerun.json"
    assert by_asset["BOYCAN79"]["qa"]["visual_parity"] == "repaired_pending_shape_rerun"
    assert "var(--orange)" in boycan79
    assert "var(--yellow)" not in boycan79

    boycon71 = (ROOT / by_asset["BOYCON71"]["after_svg"]).read_text()
    assert by_asset["BOYCON71"]["source_judge"] == "catalog/standard_judge_batch_005.json"
    assert by_asset["BOYCON71"]["qa"]["visual_parity"] == "repaired_pending_judge_rerun"
    assert boycon71.count("var(--black)") >= 3
    assert "var(--yellow)" in boycon71

    boycon78 = (ROOT / by_asset["BOYCON78"]["after_svg"]).read_text()
    assert 'width="32"' in boycon78
    assert "var(--red)" in boycon78
    assert "var(--white)" in boycon78

    boypil78 = (ROOT / by_asset["BOYPIL78"]["after_svg"]).read_text()
    assert boypil78.count("var(--red)") >= 4
    assert boypil78.count("var(--white)") >= 4

    saved = json.loads((ROOT / "catalog" / "owned_repair_batch11.json").read_text())
    assert saved["summary"]["failed_repaired"] == 34
    assert (ROOT / "catalog" / "owned_repair_batch11.md").exists()
    print("standard repair batch 3: OK")


if __name__ == "__main__":
    main()
