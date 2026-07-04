"""Smoke Standard Repair Batch 13.

Run:  python3 -m forge.tests.test_standard_repair_batch13
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch13


ROOT = Path(__file__).resolve().parent.parent.parent
QUEUE = ROOT / "catalog" / "standard_repair_queue.json"
REPORT = ROOT / "catalog" / "owned_repair_batch21.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    queue = json.loads(QUEUE.read_text())
    if len(queue.get("items", [])) == standard_repair_batch13.EXPECTED_QUEUE_ROWS:
        result = standard_repair_batch13.build(render_outputs=True)
    else:
        result = json.loads(REPORT.read_text())
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["source_queue_rows"] == 461
    assert result["summary"]["expected_queue_rows"] == 461
    assert result["summary"]["failed_repaired"] == 24
    assert result["summary"]["blocked_or_skipped"] == 437

    repaired = {row["asset"] for row in result["symbols"]}
    assert repaired == set(standard_repair_batch13.REPAIRS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}
    assert {row["qa"]["final_approved"] for row in result["symbols"]} == {False}

    blockers = {row["asset"]: row for row in result["blockers"]}
    assert blockers["BCNDEF13"]["status"] == "skipped_batch21_chart1_parity_exact_crop_or_manual_exception_required"
    assert blockers["BCNCON81"]["status"] == "blocked_missing_exact_reference"
    assert blockers["TOPMA100"]["status"] == "skipped_batch21_topmark_daymark_or_light_dedicated_pass"
    assert blockers["BOYCON81"]["status"] == "skipped_batch21_geometry_heavy_navigation_aid_contract"

    bridge = _svg("BRIDGE01", result)
    assert 'data-repair-batch="standard-repair-batch13"' in bridge
    assert 'cx="32" cy="32" r="17"' in bridge
    assert "var(--magenta)" in bridge

    water = _svg("BUNSTA02", result)
    assert "C21 14 43 14 43 19" in water
    assert "var(--blue)" in water

    ballast = _svg("BUNSTA03", result)
    assert "M20 21 L32 14 L45 21" in ballast
    assert "M26 25 V39" in ballast

    crane = _svg("CRANES01", result)
    assert "M29 20 L50 28" in crane
    assert "M48 28 V39" in crane
    assert "var(--brown)" in crane

    current = _svg("CURDEF01", result)
    assert ">?</text>" in current
    assert "M32 51 V17" in current

    dismar = _svg("DISMAR03", result)
    assert ">DM</text>" in dismar
    assert '<rect x="22" y="18" width="20" height="15"' in dismar

    dwr = _svg("DWRTPT51", result)
    assert ">DW</text>" in dwr
    assert "stroke-dasharray" in dwr

    essa = _svg("ESSARE01", result)
    assert ">ESSA</text>" in essa
    assert "<rect" not in essa

    fairway = _svg("FAIRWY52", result)
    assert "M24 20 L32 12 L40 20" in fairway
    assert "M24 44 L32 52 L40 44" in fairway
    assert "var(--magenta)" not in fairway

    flag = _svg("FLGSTF01", result)
    assert "C35 12 40 18 48 15" in flag
    assert 'cx="26" cy="53" r="5"' in flag

    hazard = _svg("FLTHAZ02", result)
    assert 'cx="32" cy="32" r="18"' in hazard
    assert "M21 32 H43" in hazard

    fog = _svg("FOGSIG01", result)
    assert "C26 30 38 30 44 44" in fog
    assert "var(--magenta)" in fog

    fort = _svg("FORSTC11", result)
    assert "M18 20 H46 V46 H18 Z" in fort
    assert "var(--black)" in fort

    foul = _svg("FOULGND1", result)
    assert "M22 17 L15 48" in foul
    assert "M17 28 H48" in foul

    ferry = _svg("FRYARE52", result)
    assert "stroke-dasharray" in ferry
    assert ">CF</text>" not in ferry

    stakes = _svg("FSHFAC02", result)
    assert "M18 47 L25 20" in stakes
    assert "M23 29 H49" in stakes

    fish = _svg("FSHGRD01", result)
    assert "C22 19 38 20 49 32" in fish
    assert ">FG</text>" not in fish

    haven = _svg("FSHHAV01", result)
    assert 'stroke-dasharray="4 4"' in haven
    assert ">FH</text>" not in haven

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 24
    assert (ROOT / "catalog" / "owned_repair_batch21.md").exists()
    print("standard repair batch 13: OK")


if __name__ == "__main__":
    main()
