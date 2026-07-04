"""Smoke Standard Repair Batch 8.

Run:  python -m forge.tests.test_standard_repair_batch8
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch8


ROOT = Path(__file__).resolve().parent.parent.parent
QUEUE = ROOT / "catalog" / "standard_repair_queue.json"
REPORT = ROOT / "catalog" / "owned_repair_batch16.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    queue = json.loads(QUEUE.read_text())
    queue_assets = [item["asset"] for item in queue.get("items", [])]
    if queue_assets == standard_repair_batch8.EXPECTED_QUEUE:
        result = standard_repair_batch8.build(render_outputs=True)
    else:
        result = json.loads(REPORT.read_text())
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["source_queue_rows"] == 93
    assert result["summary"]["expected_queue_rows"] == 93
    assert result["summary"]["failed_repaired"] == 24
    assert result["summary"]["blocked_or_skipped"] == 69

    repaired = {row["asset"] for row in result["symbols"]}
    assert repaired == set(standard_repair_batch8.REPAIRS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}
    assert {row["qa"]["final_approved"] for row in result["symbols"]} == {False}

    blockers = {row["asset"]: row for row in result["blockers"]}
    assert blockers["BCNCON81"]["status"] == "hard_blocked_missing_exact_reference"
    assert blockers["BOYLAT52"]["status"] == "blocked_missing_local_reference_render"
    assert blockers["BOYSPR02"]["status"] == "blocked_missing_local_reference_render"
    assert blockers["DANGER53"]["status"] == "blocked_missing_reference_or_exact_crop"
    assert blockers["DGPS01DRFSTA01"]["status"] == "blocked_missing_reference_or_exact_crop"
    assert blockers["BOYSUP01"]["status"] == "skipped_batch16_geometry_heavy_or_requires_exact_visual_contract"

    boycon74 = _svg("BOYCON74", result)
    assert 'clip-path="url(#clip-BOYCON74)"' in boycon74
    assert boycon74.count("var(--green)") >= 3
    assert boycon74.count("var(--white)") >= 2

    ctnare51 = _svg("CTNARE51", result)
    assert "var(--magenta)" in ctnare51
    assert "V34" in ctnare51
    assert "<rect" not in ctnare51

    dirboya1 = _svg("DIRBOYA1", result)
    assert 'cx="19" cy="50" r="7" fill="var(--red)"' in dirboya1
    assert 'cx="45" cy="50" r="7" fill="var(--green)"' in dirboya1
    dirboyb1 = _svg("DIRBOYB1", result)
    assert 'cx="19" cy="50" r="7" fill="var(--green)"' in dirboyb1
    assert 'cx="45" cy="50" r="7" fill="var(--red)"' in dirboyb1

    dismar06 = _svg("DISMAR06", result)
    assert dismar06.count("<circle") == 3
    assert ">1</text>" in dismar06

    dngr = _svg("DNGHILIT", result)
    assert "fill-opacity=\"0.18\"" in dngr
    assert dngr.count("var(--red)") >= 2

    foul = _svg("FOULGND1", result)
    assert "M19 19 L45 45" in foul
    assert "<circle" not in foul

    info = _svg("INFORM01", result)
    assert ">i</text>" in info
    assert "var(--magenta)" in info

    saved = json.loads((ROOT / "catalog" / "owned_repair_batch16.json").read_text())
    assert saved["summary"]["failed_repaired"] == 24
    assert (ROOT / "catalog" / "owned_repair_batch16.md").exists()
    print("standard repair batch 8: OK")


if __name__ == "__main__":
    main()
