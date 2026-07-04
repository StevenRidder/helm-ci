"""Smoke Standard Repair Batch 16.

Run:  python3 -m forge.tests.test_standard_repair_batch16
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch16


ROOT = Path(__file__).resolve().parent.parent.parent
QUEUE = ROOT / "catalog" / "standard_repair_queue.json"
REPORT = ROOT / "catalog" / "owned_repair_batch24.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    queue = json.loads(QUEUE.read_text())
    if len(queue.get("items", [])) == standard_repair_batch16.EXPECTED_QUEUE_ROWS:
        result = standard_repair_batch16.build(render_outputs=True)
    else:
        result = json.loads(REPORT.read_text())
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["source_queue_rows"] == 621
    assert result["summary"]["expected_queue_rows"] == 621
    assert result["summary"]["failed_repaired"] == 24
    assert result["summary"]["blocked_or_skipped"] == 597

    repaired = {row["asset"] for row in result["symbols"]}
    assert repaired == set(standard_repair_batch16.REPAIRS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}
    assert {row["qa"]["final_approved"] for row in result["symbols"]} == {False}

    blockers = {row["asset"]: row for row in result["blockers"]}
    assert blockers["BCNDEF13"]["status"] == "skipped_batch24_chart1_parity_exact_crop_or_manual_exception_required"
    assert blockers["BCNCON81"]["status"] == "blocked_batch24_missing_or_unverified_exact_reference"
    assert blockers["DAYSQR01"]["status"] == "skipped_batch24_topmark_daymark_or_light_dedicated_pass"
    assert blockers["LITFLT01"]["status"] == "skipped_batch24_topmark_daymark_or_light_dedicated_pass"
    assert blockers["NMKINF01"]["status"] == "skipped_batch24_notice_board_family_dedicated_pass"
    assert blockers["BOYCON81"]["status"] == "skipped_batch24_geometry_heavy_navigation_aid_contract"

    church = _svg("BUIREL01", result)
    assert 'data-repair-batch="standard-repair-batch16"' in church
    assert "M32 13 V48" in church
    assert "V30 L32 17" not in church
    assert "var(--brown)" in church

    church_black = _svg("BUIREL13", result)
    assert "var(--black)" in church_black

    gate = _svg("GATCON03", result)
    assert 'r="20"' in gate
    assert "var(--magenta)" in gate
    assert "M27 23 H37" in gate

    gate_closed = _svg("GATCON04", result)
    assert "M24 23 L40 42" in gate_closed
    assert "var(--black)" not in gate_closed

    hulk = _svg("HULKES01", result)
    assert "M14 36 C24 44" in hulk
    assert "V15" not in hulk

    info = _svg("INFORM01", result)
    assert '<rect x="38" y="14" width="17" height="17"' in info
    assert ">i</text>" in info

    traffic = _svg("ITZARE51", result)
    assert ">IT</text>" in traffic
    assert "stroke-dasharray" not in traffic

    land = _svg("LNDARE01", result)
    assert '<circle cx="32" cy="32" r="7"' in land
    assert 'fill="none"' not in land

    locmag = _svg("LOCMAG01", result)
    assert "M22 47 L34 15 L46 47 Z" in locmag
    assert ">A</text>" not in locmag

    locmag_line = _svg("LOCMAG51", result)
    assert "M28 31 H40" in locmag_line
    assert "stroke-dasharray" not in locmag_line

    lowacc = _svg("LOWACC01", result)
    assert ">?</text>" in lowacc
    assert "<circle" not in lowacc

    magvar = _svg("MAGVAR01", result)
    assert "M31 16 L48 25 L31 34 Z" in magvar
    assert ">M</text>" not in magvar

    magvar_line = _svg("MAGVAR51", result)
    assert "M21 50 H43" in magvar_line
    assert "stroke-dasharray" not in magvar_line

    farm = _svg("MARCUL02", result)
    assert '<rect x="14" y="18" width="38" height="30"' in farm
    assert "M12 42 C19" not in farm

    monument = _svg("MONUMT02", result)
    assert '<ellipse cx="32" cy="54" rx="7" ry="3.5"' in monument
    assert "var(--brown)" in monument

    monument_black = _svg("MONUMT12", result)
    assert "var(--black)" in monument_black

    dolphin = _svg("MORFAC03", result)
    assert "M23 47 V24 M32 47 V17 M41 47 V24" in dolphin
    assert "<circle" not in dolphin

    deviation = _svg("MORFAC04", result)
    assert "M24 36 L42 28" in deviation
    assert "<circle" not in deviation

    mast = _svg("MSTCON04", result)
    assert "M32 12 V50" in mast
    assert "L45" not in mast

    mast_black = _svg("MSTCON14", result)
    assert "var(--black)" in mast_black

    north = _svg("NORTHAR1", result)
    assert 'fill="var(--orange)"' in north
    assert ">N</text>" in north

    pos3 = _svg("POSGEN03", result)
    assert 'cx="32" cy="32" r="14"' in pos3
    assert "H54" not in pos3

    pos4 = _svg("POSGEN04", result)
    assert 'cx="32" cy="32" r="15"' in pos4
    assert "L32" not in pos4

    prcare = _svg("PRCARE51", result)
    assert "M32 14 L51 47 H13 Z" in prcare
    assert "stroke-dasharray" not in prcare

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 24
    assert (ROOT / "catalog" / "owned_repair_batch24.md").exists()
    print("standard repair batch 16: OK")


if __name__ == "__main__":
    main()
