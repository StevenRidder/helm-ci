"""Smoke Standard Repair Batch 15.

Run:  python3 -m forge.tests.test_standard_repair_batch15
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch15


ROOT = Path(__file__).resolve().parent.parent.parent
QUEUE = ROOT / "catalog" / "standard_repair_queue.json"
REPORT = ROOT / "catalog" / "owned_repair_batch23.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    queue = json.loads(QUEUE.read_text())
    if len(queue.get("items", [])) == standard_repair_batch15.EXPECTED_QUEUE_ROWS:
        result = standard_repair_batch15.build(render_outputs=True)
    else:
        result = json.loads(REPORT.read_text())
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["source_queue_rows"] == 557
    assert result["summary"]["expected_queue_rows"] == 557
    assert result["summary"]["failed_repaired"] == 24
    assert result["summary"]["blocked_or_skipped"] == 533

    repaired = {row["asset"] for row in result["symbols"]}
    assert repaired == set(standard_repair_batch15.REPAIRS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}
    assert {row["qa"]["final_approved"] for row in result["symbols"]} == {False}

    blockers = {row["asset"]: row for row in result["blockers"]}
    assert blockers["BCNDEF13"]["status"] == "skipped_batch23_chart1_parity_exact_crop_or_manual_exception_required"
    assert blockers["BCNCON81"]["status"] == "blocked_batch23_missing_exact_reference"
    assert blockers["DAYSQR01"]["status"] == "skipped_batch23_topmark_daymark_or_light_dedicated_pass"
    assert blockers["LITFLT01"]["status"] == "skipped_batch23_topmark_daymark_or_light_dedicated_pass"
    assert blockers["NMKINF01"]["status"] == "skipped_batch23_notice_board_family_dedicated_pass"
    assert blockers["BOYCON81"]["status"] == "skipped_batch23_geometry_heavy_navigation_aid_contract"

    bridge = _svg("BRIDGE01", result)
    assert 'data-repair-batch="standard-repair-batch15"' in bridge
    assert 'cx="32" cy="32" r="17"' in bridge
    assert "L44 20" not in bridge

    crane = _svg("CRANES01", result)
    assert "M18 50 V22 H48 V50" in crane
    assert "M34 22 V39" in crane
    assert "var(--brown)" in crane

    current = _svg("CURDEF01", result)
    assert "var(--gray)" in current
    assert ">?</text>" in current
    assert "M23 34 H41" not in current

    route = _svg("DWRTPT51", result)
    assert ">DW</text>" in route
    assert "stroke-dasharray" not in route

    essa = _svg("ESSARE01", result)
    assert ">ESSA</text>" in essa
    assert "<path" not in essa

    fairway = _svg("FAIRWY52", result)
    assert "M26 50 H38 V25 H46 L32 11" in fairway
    assert "M26 14 H38 V39 H46 L32 53" in fairway

    flood = _svg("FLDSTR01", result)
    assert "var(--gray)" in flood
    assert flood.count("<path") == 2

    flag = _svg("FLGSTF01", result)
    assert "H48 V30 H27 Z" in flag
    assert "<circle" not in flag

    hazard = _svg("FLTHAZ02", result)
    assert 'cx="32" cy="28" r="16"' in hazard
    assert "C25 41 39 41 45 47" in hazard

    fog = _svg("FOGSIG01", result)
    assert fog.count("<path") == 3
    assert "var(--magenta)" in fog

    fort = _svg("FORSTC01", result)
    assert "M18 18 H46 V46 H18 Z" in fort
    assert "V15" not in fort

    ferry = _svg("FRYARE51", result)
    assert 'stroke-dasharray="7 5"' in ferry
    assert "C22 34" not in ferry

    cable = _svg("FRYARE52", result)
    assert 'stroke-dasharray="7 5"' not in cable
    assert "M12 23 H52" in cable

    stakes = _svg("FSHFAC02", result)
    assert '<rect x="16" y="20" width="34" height="28"' in stakes
    assert "M20 44 L46 24" in stakes

    pattern = _svg("FSHFAC03", result)
    assert "M12 43 H54" in pattern
    assert "M17 43 V21" in pattern

    haven = _svg("FSHHAV01", result)
    assert "<ellipse" in haven
    assert 'stroke-dasharray="1 5"' in haven

    harbour = _svg("HRBFAC09", result)
    assert ">F</text>" in harbour
    assert "C25 24 37 24 46 33" in harbour

    obstruction = _svg("OBSTRN03", result)
    assert 'fill-opacity="0.18"' in obstruction
    assert 'stroke-dasharray="1 5"' in obstruction

    platform = _svg("OFSPLF01", result)
    assert '<rect x="19" y="19" width="26" height="26"' in platform
    assert 'cx="32" cy="32" r="4"' in platform

    pilot = _svg("PILBOP02", result)
    assert 'cx="32" cy="32" r="18"' in pilot
    assert "M32 17 L47 32 L32 47 L17 32 Z" in pilot
    assert ">P</text>" not in pilot

    pile = _svg("PILPNT02", result)
    assert "M25 46 H39 L36 20 H28 Z" in pile
    assert "<ellipse" in pile

    pos = _svg("POSGEN01", result)
    assert 'cx="32" cy="32" r="13"' in pos
    assert "var(--brown)" in pos

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 24
    assert (ROOT / "catalog" / "owned_repair_batch23.md").exists()
    print("standard repair batch 15: OK")


if __name__ == "__main__":
    main()
