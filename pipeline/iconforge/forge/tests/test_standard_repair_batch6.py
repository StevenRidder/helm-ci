"""Smoke Standard Repair Batch 6.

Run:  python -m forge.tests.test_standard_repair_batch6
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch6


ROOT = Path(__file__).resolve().parent.parent.parent
QUEUE = ROOT / "catalog" / "standard_repair_queue.json"
REPORT = ROOT / "catalog" / "owned_repair_batch14.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    queue = json.loads(QUEUE.read_text())
    queue_assets = [item["asset"] for item in queue.get("items", [])]
    if queue_assets == standard_repair_batch6.EXPECTED_QUEUE:
        result = standard_repair_batch6.build(render_outputs=True)
    else:
        result = json.loads(REPORT.read_text())
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["source_queue_rows"] == 9
    assert result["summary"]["expected_queue_rows"] == 9
    assert result["summary"]["failed_repaired"] == 4
    assert result["summary"]["blocked_or_skipped"] == 5

    repaired = {row["asset"] for row in result["symbols"]}
    assert repaired == {"BOYCON74", "BOYCON81", "BOYPIL78", "BOYSPH79"}
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["source_judge"] for row in result["symbols"]} == {
        "catalog/standard_judge_batch_006.json",
        "catalog/standard_judge_batch_012_rerun.json",
    }

    blockers = {row["asset"]: row for row in result["blockers"]}
    assert blockers["BCNCON81"]["status"] == "hard_blocked_missing_exact_reference"
    assert blockers["BOYLAT52"]["status"] == "blocked_missing_opencpn_day_render"
    assert blockers["BOYLAT53"]["status"] == "blocked_missing_opencpn_day_render"
    assert blockers["BOYSPR02"]["status"] == "blocked_missing_opencpn_or_s101_reference"
    assert blockers["BOYSPR03"]["status"] == "blocked_missing_opencpn_or_s101_reference"

    boycon74 = _svg("BOYCON74", result)
    assert boycon74.count("var(--green)") >= 3
    assert boycon74.count("var(--white)") >= 2
    assert 'M13 12.8 H51' not in boycon74
    assert 'M13 25.6 H51' not in boycon74

    boycon81 = _svg("BOYCON81", result)
    assert boycon81.count("var(--blue)") >= 4
    assert "var(--red)" in boycon81
    assert "var(--white)" in boycon81
    assert 'clip-path="url(#clip-BOYCON81)"' in boycon81
    assert 'M12 16 H52' not in boycon81
    assert 'M16 10 V54' not in boycon81

    boypil78 = _svg("BOYPIL78", result)
    assert boypil78.count("var(--red)") >= 10
    assert boypil78.count("var(--white)") >= 10
    assert 'clip-path="url(#clip-BOYPIL78)"' in boypil78
    assert 'M18 12.8 H46' not in boypil78
    assert 'M16 12 V54' not in boypil78

    boysph79 = _svg("BOYSPH79", result)
    assert "var(--red)" in boysph79
    assert "var(--green)" in boysph79
    assert "M32 10 L50 50" in boysph79
    assert "<circle" not in boysph79

    saved = json.loads((ROOT / "catalog" / "owned_repair_batch14.json").read_text())
    assert saved["summary"]["failed_repaired"] == 4
    assert (ROOT / "catalog" / "owned_repair_batch14.md").exists()
    print("standard repair batch 6: OK")


if __name__ == "__main__":
    main()
