"""Smoke Standard Repair Batch 7.

Run:  python -m forge.tests.test_standard_repair_batch7
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch7


ROOT = Path(__file__).resolve().parent.parent.parent
QUEUE = ROOT / "catalog" / "standard_repair_queue.json"
REPORT = ROOT / "catalog" / "owned_repair_batch15.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    queue = json.loads(QUEUE.read_text())
    queue_assets = [item["asset"] for item in queue.get("items", [])]
    if queue_assets == standard_repair_batch7.EXPECTED_QUEUE:
        result = standard_repair_batch7.build(render_outputs=True)
    else:
        result = json.loads(REPORT.read_text())
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["source_queue_rows"] == 75
    assert result["summary"]["expected_queue_rows"] == 75
    assert result["summary"]["failed_repaired"] == 35
    assert result["summary"]["blocked_or_skipped"] == 40

    repaired = {row["asset"] for row in result["symbols"]}
    assert repaired == set(standard_repair_batch7.REPAIRS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["source_judge"] for row in result["symbols"]} == {
        "catalog/standard_judge_batch_007.json",
        "catalog/standard_judge_batch_013_rerun.json",
    }

    blockers = {row["asset"]: row for row in result["blockers"]}
    assert blockers["BCNCON81"]["status"] == "hard_blocked_missing_exact_reference"
    assert blockers["BOYLAT52"]["status"] == "blocked_missing_local_reference_render"
    assert blockers["BOYSPR02"]["status"] == "blocked_missing_local_reference_render"
    assert blockers["DANGER53"]["status"] == "blocked_missing_reference_or_exact_crop"
    assert blockers["DGPS01DRFSTA01"]["status"] == "blocked_missing_reference_or_exact_crop"

    boyspr70 = _svg("BOYSPR70", result)
    assert boyspr70.count("var(--black)") >= 3
    assert "var(--yellow)" in boyspr70
    assert 'clip-path="url(#clip-BOYSPR70)"' in boyspr70
    assert "M13 21.3333 H51" not in boyspr70

    brthno01 = _svg("BRTHNO01", result)
    assert "var(--magenta)" in brthno01
    assert "<text" not in brthno01

    buarel02 = _svg("BUAARE02", result)
    assert buarel02.count("var(--brown)") >= 4
    assert "<rect" not in buarel02

    buirel05 = _svg("BUIREL05", result)
    assert "var(--brown)" in buirel05
    assert "M25 43 C26 31" in buirel05

    bunsta03 = _svg("BUNSTA03", result)
    assert bunsta03.count("var(--black)") >= 6
    assert "L32 18 L45 26" in bunsta03

    chinfo08 = _svg("CHINFO08", result)
    assert "var(--orange)" in chinfo08
    assert ">i</text>" in chinfo08

    cursrb01 = _svg("CURSRB01", result)
    assert "var(--orange)" in cursrb01
    assert "M32 9 V22" in cursrb01
    assert "M32 10 V54" not in cursrb01

    custom01 = _svg("CUSTOM01", result)
    assert "var(--red)" in custom01
    assert "var(--white)" in custom01

    danger52 = _svg("DANGER52", result)
    assert danger52.count("<circle") == 9
    assert 'cx="32" cy="32" r="5"' in danger52

    daytri01 = _svg("DAYTRI01", result)
    assert 'points="32,12 48,40 16,40"' in daytri01
    daytri05 = _svg("DAYTRI05", result)
    assert 'points="16,16 48,16 32,44"' in daytri05

    saved = json.loads((ROOT / "catalog" / "owned_repair_batch15.json").read_text())
    assert saved["summary"]["failed_repaired"] == 35
    assert (ROOT / "catalog" / "owned_repair_batch15.md").exists()
    print("standard repair batch 7: OK")


if __name__ == "__main__":
    main()
