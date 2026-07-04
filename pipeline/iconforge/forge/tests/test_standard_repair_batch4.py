"""Smoke Standard Repair Batch 4.

Run:  python -m forge.tests.test_standard_repair_batch4
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch4


ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    result = standard_repair_batch4.build(render_outputs=False)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["source_queue_rows"] == 12
    assert result["summary"]["expected_queue_rows"] == 12
    assert result["summary"]["failed_repaired"] == 9
    assert result["summary"]["blocked_or_skipped"] == 3

    by_asset = {row["asset"]: row for row in result["symbols"]}
    assert set(by_asset) == {
        "BOYCAN81",
        "BOYCON74",
        "BOYCON81",
        "BOYINB01",
        "BOYISD12",
        "BOYMOR01",
        "BOYMOR11",
        "BOYPIL78",
        "BOYSAW12",
    }
    blockers = {row["asset"]: row for row in result["blockers"]}
    assert blockers["BCNCON81"]["status"] == "hard_blocked_missing_exact_reference"
    assert blockers["BOYLAT52"]["status"] == "blocked_missing_opencpn_day_render"
    assert blockers["BOYLAT53"]["status"] == "blocked_missing_opencpn_day_render"

    boycan81 = (ROOT / by_asset["BOYCAN81"]["after_svg"]).read_text()
    assert "var(--orange)" in boycan81
    assert "var(--white)" in boycan81
    assert "var(--yellow)" not in boycan81

    boycon74 = (ROOT / by_asset["BOYCON74"]["after_svg"]).read_text()
    assert boycon74.count("var(--green)") >= 3
    assert boycon74.count("var(--white)") >= 2

    boycon81 = (ROOT / by_asset["BOYCON81"]["after_svg"]).read_text()
    assert boycon81.count("var(--blue)") >= 4
    assert "opacity=\"0.48\"" in boycon81

    boyinb01 = (ROOT / by_asset["BOYINB01"]["after_svg"]).read_text()
    assert "<rect" not in boyinb01
    assert boyinb01.count("<circle") == 2
    assert "L22 24 H42 L49 47" in boyinb01

    boyisd12 = (ROOT / by_asset["BOYISD12"]["after_svg"]).read_text()
    assert boyisd12.count("var(--red)") == 2
    assert "<clipPath" not in boyisd12

    boymor11 = (ROOT / by_asset["BOYMOR11"]["after_svg"]).read_text()
    assert "M13 49 L19 29 H45 L51 49 Z" in boymor11
    assert 'fill="var(--black)"' in boymor11

    boypil78 = (ROOT / by_asset["BOYPIL78"]["after_svg"]).read_text()
    assert boypil78.count("var(--red)") >= 10
    assert boypil78.count("var(--white)") >= 10

    boysaw12 = (ROOT / by_asset["BOYSAW12"]["after_svg"]).read_text()
    assert boysaw12.count("<circle") == 2
    assert "var(--red)" in boysaw12

    saved = json.loads((ROOT / "catalog" / "owned_repair_batch12.json").read_text())
    assert saved["summary"]["failed_repaired"] == 9
    assert (ROOT / "catalog" / "owned_repair_batch12.md").exists()
    print("standard repair batch 4: OK")


if __name__ == "__main__":
    main()
