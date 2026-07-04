"""Smoke Standard Repair Batch 9.

Run:  python -m forge.tests.test_standard_repair_batch9
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch9


ROOT = Path(__file__).resolve().parent.parent.parent
QUEUE = ROOT / "catalog" / "standard_repair_queue.json"
REPORT = ROOT / "catalog" / "owned_repair_batch17.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    queue = json.loads(QUEUE.read_text())
    queue_assets = [item["asset"] for item in queue.get("items", [])]
    if queue_assets == standard_repair_batch9.EXPECTED_QUEUE:
        result = standard_repair_batch9.build(render_outputs=True)
    else:
        result = json.loads(REPORT.read_text())
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["source_queue_rows"] == 133
    assert result["summary"]["expected_queue_rows"] == 133
    assert result["summary"]["failed_repaired"] == 26
    assert result["summary"]["blocked_or_skipped"] == 107

    repaired = {row["asset"] for row in result["symbols"]}
    assert repaired == set(standard_repair_batch9.REPAIRS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}
    assert {row["qa"]["final_approved"] for row in result["symbols"]} == {False}

    blockers = {row["asset"]: row for row in result["blockers"]}
    assert blockers["BCNCON81"]["status"] == "hard_blocked_missing_exact_reference"
    assert blockers["BOYLAT52"]["status"] == "blocked_missing_local_reference_render"
    assert blockers["DANGER53"]["status"] == "blocked_missing_reference_or_exact_crop"
    assert blockers["BOYSUP01"]["status"] == "skipped_batch17_geometry_heavy_or_exact_contract"
    assert blockers["NMKINF02"]["status"] == "skipped_batch17_notice_board_family_requires_dedicated_pass"

    buaare = _svg("BUAARE02", result)
    assert buaare.count("<circle") == 1
    assert "var(--brown)" in buaare
    assert "baseline" not in buaare

    buirel04 = _svg("BUIREL04", result)
    assert "L31 32 L41 47" in buirel04
    assert "var(--brown)" in buirel04
    assert "circle" not in buirel04

    buirel15 = _svg("BUIREL15", result)
    assert "C27 17" in buirel15
    assert "V50" in buirel15
    assert "var(--black)" in buirel15

    chimney = _svg("CHIMNY11", result)
    assert "M27 18 H38 L40 49 H25 Z" in chimney
    assert "var(--black)" in chimney

    cursor = _svg("CURSRB01", result)
    assert "M32 8 V23" in cursor
    assert "r=\"2.5\"" in cursor
    assert "r=\"10\"" not in cursor

    daysqr = _svg("DAYSQR01", result)
    assert "<rect" in daysqr
    assert "M32 37 V57" in daysqr
    assert "M23 25 H41" not in daysqr

    daytri = _svg("DAYTRI05", result)
    assert 'points="16,16 48,16 32,44"' in daytri

    dish = _svg("DSHAER01", result)
    assert "C25 16 40 15 49 22" in dish
    assert "var(--brown)" in dish

    locmag = _svg("LOCMAG51", result)
    assert 'stroke-dasharray="6 5"' in locmag
    assert "var(--magenta)" in locmag

    lowacc = _svg("LOWACC01", result)
    assert ">?</text>" in lowacc
    assert 'stroke-dasharray="5 5"' in lowacc

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 26
    assert (ROOT / "catalog" / "owned_repair_batch17.md").exists()
    print("standard repair batch 9: OK")


if __name__ == "__main__":
    main()
