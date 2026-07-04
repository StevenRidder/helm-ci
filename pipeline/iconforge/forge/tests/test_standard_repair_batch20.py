"""Smoke Standard Repair Batch 20.

Run:  python3 -m forge.tests.test_standard_repair_batch20
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch20


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch28.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch20.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 6
    assert not result["blockers"]

    repaired = {row["asset"] for row in result["symbols"]}
    assert repaired == set(standard_repair_batch20.REPAIRS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}
    assert {row["qa"]["final_approved"] for row in result["symbols"]} == {False}

    crossing = _svg("TSSCRS51", result)
    assert 'data-repair-batch="standard-repair-batch20"' in crossing
    assert '<circle cx="32" cy="32" r="17"' in crossing
    assert "M32 20 V36" in crossing
    assert "var(--magenta)" in crossing
    assert "<rect" not in crossing

    one_way = _svg("TSSLPT51", result)
    assert "M20 27 L32 9 L44 27 H38 V55 H26 V27 Z" in one_way
    assert "fill-opacity" in one_way

    roundabout = _svg("TSSRON51", result)
    assert "M21 15 H21 V29 H35 L27 21" in roundabout
    assert "C24 50 38 54 48 45" in roundabout

    undefined = _svg("TWRDEF51", result)
    assert undefined.count(">?</text>") == 2
    assert "M25 19 L32 9 L39 19" in undefined
    assert "M25 45 L32 55 L39 45" in undefined

    reciprocal = _svg("TWRTPT52", result)
    assert ">?</text>" not in reciprocal
    assert "M25 19 L32 9 L39 19" in reciprocal
    assert "M25 45 L32 55 L39 45" in reciprocal

    single = _svg("TWRTPT53", result)
    assert "M25 19 L32 9 L39 19" in single
    assert "M25 52 H39" in single
    assert "M25 45 L32 55 L39 45" not in single

    shapes = {asset: _svg(asset, result) for asset in repaired}
    assert len(set(shapes.values())) == len(shapes)

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 6
    assert (ROOT / "catalog" / "owned_repair_batch28.md").exists()
    print("standard repair batch 20: OK")


if __name__ == "__main__":
    main()
