"""Smoke Standard Repair Batch 23.

Run:  python3 -m forge.tests.test_standard_repair_batch23
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch23


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch31.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch23.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 6
    assert not result["blockers"]

    repaired = {row["asset"] for row in result["symbols"]}
    assert repaired == set(standard_repair_batch23.REPAIRS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}
    assert {row["qa"]["final_approved"] for row in result["symbols"]} == {False}
    assert {row["source_judge"] for row in result["symbols"]} == {"catalog/standard_judge_batch_024_025_rerun.json"}

    hulk = _svg("HULKES01", result)
    assert "var(--brown)" in hulk
    assert "M25 30 C31 28" in hulk
    assert "V44" not in hulk

    land = _svg("LNDARE01", result)
    assert '<circle cx="32" cy="32" r="2.3"' in land
    assert land.count("<circle") == 1
    assert "<path" not in land

    locmag_point = _svg("LOCMAG01", result)
    assert "var(--magenta)" in locmag_point
    assert "M35 20 V44" in locmag_point
    assert "M35 25 L27 34 L35 39" in locmag_point
    assert ">A</text>" not in locmag_point
    assert "H44" not in locmag_point

    locmag_area = _svg("LOCMAG51", result)
    assert 'opacity="0.48"' in locmag_area
    assert "M35 25 L27 34 L35 39" in locmag_area

    magvar_point = _svg("MAGVAR01", result)
    assert "M35 25 L28 36 L35 40 Z" in magvar_point
    assert "H44" not in magvar_point

    magvar_area = _svg("MAGVAR51", result)
    assert 'opacity="0.48"' in magvar_area
    assert "M35 25 L28 36 L35 40 Z" in magvar_area

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 6
    assert (ROOT / "catalog" / "owned_repair_batch31.md").exists()
    print("standard repair batch 23: OK")


if __name__ == "__main__":
    main()
