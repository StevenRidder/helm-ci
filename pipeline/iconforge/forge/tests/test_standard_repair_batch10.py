"""Smoke Standard Repair Batch 10.

Run:  python -m forge.tests.test_standard_repair_batch10
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch10


ROOT = Path(__file__).resolve().parent.parent.parent
QUEUE = ROOT / "catalog" / "standard_repair_queue.json"
REPORT = ROOT / "catalog" / "owned_repair_batch18.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    queue = json.loads(QUEUE.read_text())
    queue_assets = [item["asset"] for item in queue.get("items", [])]
    if queue_assets == standard_repair_batch10.EXPECTED_QUEUE:
        result = standard_repair_batch10.build(render_outputs=True)
    else:
        result = json.loads(REPORT.read_text())
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["source_queue_rows"] == 163
    assert result["summary"]["expected_queue_rows"] == 163
    assert result["summary"]["failed_repaired"] == 43
    assert result["summary"]["blocked_or_skipped"] == 120

    repaired = {row["asset"] for row in result["symbols"]}
    assert repaired == set(standard_repair_batch10.REPAIRS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}
    assert {row["qa"]["final_approved"] for row in result["symbols"]} == {False}

    blockers = {row["asset"]: row for row in result["blockers"]}
    assert blockers["BCNCON81"]["status"] == "hard_blocked_missing_exact_reference"
    assert blockers["BOYLAT52"]["status"] == "blocked_missing_local_reference_render"
    assert blockers["BOYSUP01"]["status"] == "skipped_batch18_geometry_heavy_or_exact_contract"
    assert blockers["NMKINF02"]["status"] == "skipped_batch18_notice_board_family_dedicated_pass"
    assert blockers["NOTMRK01"]["status"] == "skipped_batch18_notice_board_geometry_or_marker_contract"

    bridge = _svg("BRIDGE01", result)
    assert "M21 43 L43 21" in bridge
    assert "crosshair" not in bridge
    assert "var(--magenta)" in bridge

    current = _svg("CURDEF01", result)
    assert current.count(">?</text>") == 2
    assert "var(--blue)" in current

    fairway = _svg("FAIRWY52", result)
    assert "M22 43 L32 54 L42 43" in fairway
    assert "var(--magenta)" in fairway

    crane = _svg("CRANES01", result)
    assert "M24 50 V21 H36" in crane
    assert "C45 36 44 42 39 43" in crane

    daysqr = _svg("DAYSQR21", result)
    assert "<rect" in daysqr
    assert 'cx="32" cy="56" r="4"' in daysqr

    fogsig = _svg("FOGSIG01", result)
    assert "C22 24 42 24 42 37" in fogsig
    assert "M18 18 C24 11" in fogsig

    obstruction = _svg("OBSTRN03", result)
    assert "var(--green)" in obstruction
    assert "fill-opacity=\"0.22\"" in obstruction

    notice = _svg("NOTBRD11", result)
    assert "<rect" in notice
    assert "M32 35 V53" in notice
    assert "var(--black)" in notice

    posgen = _svg("POSGEN04", result)
    assert "M22 42 L32 18 L42 42 Z" in posgen

    prdins = _svg("PRDINS02", result)
    assert "M18 48 L46 20" in prdins
    assert "var(--brown)" in prdins

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 43
    assert (ROOT / "catalog" / "owned_repair_batch18.md").exists()
    print("standard repair batch 10: OK")


if __name__ == "__main__":
    main()
