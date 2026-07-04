"""Smoke Standard Repair Batch 5.

Run:  python -m forge.tests.test_standard_repair_batch5
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch5


ROOT = Path(__file__).resolve().parent.parent.parent


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch5.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["source_queue_rows"] == 35
    assert result["summary"]["expected_queue_rows"] == 35
    assert result["summary"]["failed_repaired"] == 29
    assert result["summary"]["blocked_or_skipped"] == 6

    repaired = {row["asset"] for row in result["symbols"]}
    assert "BOYSPH66" in repaired
    assert "BOYSPR72" in repaired
    assert "BOYSUP65" in repaired
    assert "BRIDGE01" in repaired
    assert "BUIREL05" in repaired
    assert "BUNSTA01" in repaired
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}

    blockers = {row["asset"]: row for row in result["blockers"]}
    assert blockers["BCNCON81"]["status"] == "hard_blocked_missing_exact_reference"
    assert blockers["BOYLAT52"]["status"] == "blocked_missing_opencpn_day_render"
    assert blockers["BOYLAT53"]["status"] == "blocked_missing_opencpn_day_render"
    assert blockers["BOYSPH79"]["status"] == "blocked_missing_opencpn_day_render"
    assert blockers["BOYSPR02"]["status"] == "blocked_missing_opencpn_or_s101_reference"
    assert blockers["BOYSPR03"]["status"] == "blocked_missing_opencpn_or_s101_reference"

    boysph66 = _svg("BOYSPH66", result)
    assert boysph66.count("var(--red)") >= 2
    assert "var(--green)" in boysph66
    assert "var(--blue)" not in boysph66

    boysph65 = _svg("BOYSPH65", result)
    assert 'x="0"' in boysph65
    assert 'width="32"' in boysph65
    assert "var(--red)" in boysph65
    assert "var(--white)" in boysph65

    boyspr72 = _svg("BOYSPR72", result)
    assert boyspr72.count("var(--black)") >= 3
    assert "var(--red)" in boyspr72

    boysup02 = _svg("BOYSUP02", result)
    assert "var(--blue)" not in boysup02
    assert "var(--black)" in boysup02

    bridge = _svg("BRIDGE01", result)
    assert "<circle" in bridge
    assert "var(--magenta)" in bridge
    assert "L52 32 L32 52" not in bridge

    buirel05 = _svg("BUIREL05", result)
    assert "Q46 8 51 16" in buirel05
    assert "L52 32 L32 52" not in buirel05

    bunsta01 = _svg("BUNSTA01", result)
    assert "V46 Q49 50 45 50" in bunsta01
    assert "L52 32 L32 52" not in bunsta01

    saved = json.loads((ROOT / "catalog" / "owned_repair_batch13.json").read_text())
    assert saved["summary"]["failed_repaired"] == 29
    assert (ROOT / "catalog" / "owned_repair_batch13.md").exists()
    print("standard repair batch 5: OK")


if __name__ == "__main__":
    main()
