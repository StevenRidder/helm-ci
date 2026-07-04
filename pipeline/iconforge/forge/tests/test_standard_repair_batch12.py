"""Smoke Standard Repair Batch 12.

Run:  python3 -m forge.tests.test_standard_repair_batch12
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch12


ROOT = Path(__file__).resolve().parent.parent.parent
QUEUE = ROOT / "catalog" / "standard_repair_queue.json"
REPORT = ROOT / "catalog" / "owned_repair_batch20.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    queue = json.loads(QUEUE.read_text())
    if len(queue.get("items", [])) == standard_repair_batch12.EXPECTED_QUEUE_ROWS:
        result = standard_repair_batch12.build(render_outputs=True)
    else:
        result = json.loads(REPORT.read_text())
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["source_queue_rows"] == 252
    assert result["summary"]["expected_queue_rows"] == 252
    assert result["summary"]["failed_repaired"] == 30
    assert result["summary"]["blocked_or_skipped"] == 222

    repaired = {row["asset"] for row in result["symbols"]}
    assert repaired == set(standard_repair_batch12.REPAIRS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}
    assert {row["qa"]["final_approved"] for row in result["symbols"]} == {False}

    blockers = {row["asset"]: row for row in result["blockers"]}
    assert blockers["BCNCON81"]["status"] == "blocked_missing_exact_reference"
    assert blockers["BOYLAT52"]["status"] == "blocked_missing_or_unverified_reference_render"
    assert blockers["NMKINF01"]["status"] == "skipped_batch20_notice_board_family_dedicated_pass"
    assert blockers["TIDCUR03"]["status"] == "skipped_batch20_tide_current_dedicated_pass"
    assert blockers["TOPMA100"]["status"] == "skipped_batch20_topmark_light_dedicated_pass"

    sounding = _svg("SOUNDG02", result)
    assert ">12</text>" in sounding
    assert ">3</text>" in sounding

    scale10 = _svg("SCALEB10", result)
    assert "M32 11 V53" in scale10
    assert ">1M</text>" in scale10

    scale11 = _svg("SCALEB11", result)
    assert "M11 34 H53" in scale11
    assert ">10M</text>" in scale11

    tank = _svg("TNKFRM11", result)
    assert 'cx="24" cy="27" r="9"' in tank
    assert 'cx="40" cy="27" r="9"' in tank
    assert 'var(--black)' in tank

    timber = _svg("TMBYRD01", result)
    assert '<rect x="17" y="18" width="30" height="28"' in timber
    assert "M17 27 H47" in timber
    assert "var(--brown)" in timber

    swept = _svg("SWPARE51", result)
    assert "C12 25 12 39 21 48" in swept
    assert "stroke-dasharray" in swept

    waves = _svg("SNDWAV02", result)
    assert "C18 20 25 36 32 28" in waves

    radio = _svg("RDOCAL03", result)
    assert "M22 24 L13 32 L22 40" not in radio
    assert "M28 24 L19 32 L28 40" in radio
    assert ">R</text>" in radio

    reflector = _svg("RADRFL03", result)
    assert "M24 24 L40 32 L24 40 Z" in reflector
    assert "C49 27 49 37 42 42" in reflector

    retro = _svg("RETRFL01", result)
    assert "M20 20 L44 32 L20 44 Z" in retro
    assert "var(--magenta)" in retro

    refpnt = _svg("REFPNT02", result)
    assert "M32 13 V51" in refpnt
    assert "var(--orange)" in refpnt

    track = _svg("RECTRC56", result)
    assert "M22 24 L13 32 L22 40" in track
    assert 'cx="32" cy="32" r="4"' in track

    unknown = _svg("RECDEF51", result)
    assert ">?</text>" in unknown
    assert "stroke-dasharray" in unknown

    scanner = _svg("RASCAN11", result)
    assert "C27 22 37 22 44 28" in scanner
    assert "var(--black)" in scanner

    quarry = _svg("QUARRY01", result)
    assert "M20 44 L44 20" in quarry
    assert "var(--brown)" in quarry

    approx = _svg("QUAPOS01", result)
    assert ">PA</text>" in approx
    assert "stroke-dasharray" in approx

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 30
    assert (ROOT / "catalog" / "owned_repair_batch20.md").exists()
    print("standard repair batch 12: OK")


if __name__ == "__main__":
    main()
