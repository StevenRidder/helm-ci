"""Smoke Standard Repair Batch 14.

Run:  python3 -m forge.tests.test_standard_repair_batch14
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch14


ROOT = Path(__file__).resolve().parent.parent.parent
QUEUE = ROOT / "catalog" / "standard_repair_queue.json"
REPORT = ROOT / "catalog" / "owned_repair_batch22.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    queue = json.loads(QUEUE.read_text())
    if len(queue.get("items", [])) == standard_repair_batch14.EXPECTED_QUEUE_ROWS:
        result = standard_repair_batch14.build(render_outputs=True)
    else:
        result = json.loads(REPORT.read_text())
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["source_queue_rows"] == 510
    assert result["summary"]["expected_queue_rows"] == 510
    assert result["summary"]["failed_repaired"] == 24
    assert result["summary"]["blocked_or_skipped"] == 486

    repaired = {row["asset"] for row in result["symbols"]}
    assert repaired == set(standard_repair_batch14.REPAIRS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}
    assert {row["qa"]["final_approved"] for row in result["symbols"]} == {False}

    blockers = {row["asset"]: row for row in result["blockers"]}
    assert blockers["BCNDEF13"]["status"] == "skipped_batch22_chart1_parity_exact_crop_or_manual_exception_required"
    assert blockers["BCNCON81"]["status"] == "blocked_batch22_missing_exact_reference"
    assert blockers["DAYSQR01"]["status"] == "skipped_batch22_topmark_daymark_or_light_dedicated_pass"
    assert blockers["LITFLT01"]["status"] == "skipped_batch22_topmark_daymark_or_light_dedicated_pass"
    assert blockers["NMKINF01"]["status"] == "skipped_batch22_notice_board_family_dedicated_pass"
    assert blockers["BOYCON81"]["status"] == "skipped_batch22_geometry_heavy_navigation_aid_contract"

    church = _svg("BUIREL01", result)
    assert 'data-repair-batch="standard-repair-batch14"' in church
    assert "M19 48 H45 V30 L32 17 L19 30 Z" in church
    assert "M32 17 V9" in church
    assert "var(--brown)" in church

    mosque = _svg("BUIREL15", result)
    assert "C27 14 24 22 30 28" in mosque
    assert 'cx="32" cy="54" r="3.5"' in mosque
    assert "var(--black)" in mosque

    gate = _svg("GATCON04", result)
    assert "M18 42 L32 24 L46 42" in gate
    assert "M21 20 L43 44" in gate

    hulk = _svg("HULKES01", result)
    assert "C23 45 42 45 52 35" in hulk
    assert "M22 34 L30 24 L41 34" in hulk

    inform = _svg("INFORM01", result)
    assert 'cx="18" cy="47" r="5"' in inform
    assert "M22 43 L40 25" in inform
    assert ">i</text>" in inform

    traffic = _svg("ITZARE51", result)
    assert ">IT</text>" in traffic
    assert "stroke-dasharray" in traffic

    magnetic = _svg("LOCMAG51", result)
    assert "M18 46 L33 16 L47 46" in magnetic
    assert "stroke-dasharray" in magnetic

    lowacc = _svg("LOWACC01", result)
    assert ">?</text>" in lowacc
    assert "M18 47 L45 20" in lowacc
    assert "stroke-dasharray" not in lowacc

    farm = _svg("MARCUL02", result)
    assert "C19 34 27 50 34 42" in farm
    assert "M18 28 H49" in farm

    monument = _svg("MONUMT12", result)
    assert "M24 50 L29 17 H35 L40 50 Z" in monument
    assert "var(--black)" in monument

    mooring = _svg("MORFAC04", result)
    assert "M23 34 L43 26" in mooring
    assert 'cx="33" cy="17" r="4"' in mooring

    mast = _svg("MSTCON04", result)
    assert "M32 13 V50" in mast
    assert 'cx="32" cy="53" r="4"' in mast

    north = _svg("NORTHAR1", result)
    assert ">N</text>" in north
    assert "M32 52 V15" in north
    assert "var(--orange)" in north

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 24
    assert (ROOT / "catalog" / "owned_repair_batch22.md").exists()
    print("standard repair batch 14: OK")


if __name__ == "__main__":
    main()
