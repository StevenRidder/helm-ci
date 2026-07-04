"""Smoke Standard Repair Batch 11.

Run:  python3 -m forge.tests.test_standard_repair_batch11
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch11


ROOT = Path(__file__).resolve().parent.parent.parent
QUEUE = ROOT / "catalog" / "standard_repair_queue.json"
REPORT = ROOT / "catalog" / "owned_repair_batch19.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    queue = json.loads(QUEUE.read_text())
    if len(queue.get("items", [])) == standard_repair_batch11.EXPECTED_QUEUE_ROWS:
        result = standard_repair_batch11.build(render_outputs=True)
    else:
        result = json.loads(REPORT.read_text())
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["source_queue_rows"] == 190
    assert result["summary"]["expected_queue_rows"] == 190
    assert result["summary"]["failed_repaired"] == 26
    assert result["summary"]["blocked_or_skipped"] == 164

    repaired = {row["asset"] for row in result["symbols"]}
    assert repaired == set(standard_repair_batch11.REPAIRS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}
    assert {row["qa"]["final_approved"] for row in result["symbols"]} == {False}

    blockers = {row["asset"]: row for row in result["blockers"]}
    assert blockers["BCNCON81"]["status"] == "blocked_missing_exact_reference"
    assert blockers["BOYLAT52"]["status"] == "blocked_missing_or_unverified_reference_render"
    assert blockers["BOYSPR02"]["status"] == "blocked_missing_or_unverified_reference_render"
    assert blockers["NMKINF01"]["status"] == "skipped_batch19_notice_board_family_dedicated_pass"

    boysup = _svg("BOYSUP03", result)
    assert "M18 30 L24 16 H40 L46 30 L42 45 H22 Z" in boysup
    assert "M32 6 V20" in boysup
    assert "var(--red)" in boysup and "var(--black)" in boysup

    christian = _svg("BUIREL01", result)
    assert "M32 13 V47" in christian
    assert "M23 24 H41" in christian
    assert "V29 L32 20" not in christian

    non_christian = _svg("BUIREL14", result)
    assert '<rect x="18" y="24" width="28" height="17"' in non_christian
    assert "M18 24 L46 41" in non_christian
    assert "var(--black)" in non_christian

    mosque = _svg("BUIREL15", result)
    assert "C27 13 25 23 31 28" in mosque
    assert 'cx="32" cy="52" r="4"' in mosque

    chimney = _svg("CHIMNY01", result)
    assert "C34 8 45 11 42 21" in chimney
    assert 'cx="32" cy="55" r="4"' in chimney
    assert "var(--brown)" in chimney

    cursor = _svg("CURSRB01", result)
    assert 'cx="32" cy="32"' not in cursor
    assert "M32 8 V23" in cursor

    customs = _svg("CUSTOM01", result)
    assert '<rect x="16" y="26" width="32" height="12"' in customs
    assert "A14 14" not in customs

    daysqr = _svg("DAYSQR01", result)
    assert 'fill="var(--yellow)"' in daysqr
    assert 'cx="32" cy="56" r="4"' in daysqr

    daytri = _svg("DAYTRI05", result)
    assert 'points="16,17 48,17 32,45"' in daytri

    essa = _svg("ESSARE01", result)
    assert ">PSSA</text>" in essa
    assert "stroke-dasharray" in essa

    hilltop = _svg("HILTOP11", result)
    assert "M13 32 H24" in hilltop
    assert "M45 45 L37 37" in hilltop

    magnetic = _svg("MAGVAR51", result)
    assert ">V</text>" in magnetic
    assert "stroke-dasharray" in magnetic

    lowacc = _svg("LOWACC01", result)
    assert ">?</text>" in lowacc
    assert "M39 19 L23 47" in lowacc

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 26
    assert (ROOT / "catalog" / "owned_repair_batch19.md").exists()
    print("standard repair batch 11: OK")


if __name__ == "__main__":
    main()
