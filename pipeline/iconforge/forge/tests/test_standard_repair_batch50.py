"""Smoke Standard Repair Batch 50.

Run:  python3 -m forge.tests.test_standard_repair_batch50
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch50


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch58.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch50.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 11
    assert not result["blockers"]
    assert {row["asset"] for row in result["symbols"]} == set(standard_repair_batch50.REPAIRS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}
    assert {row["source_judge"] for row in result["symbols"]} == {"catalog/standard_judge_batch_057_rerun.json"}

    for asset in standard_repair_batch50.REPAIRS:
        svg = _svg(asset, result)
        assert "generated-owned-artwork" in svg
        assert 'data-repair-batch="standard-repair-batch50"' in svg
        assert 'width="26" height="26"' in svg
        assert "V56" in svg

    assert _svg("TOPSHP25", result).count('data-pattern="nested-square-board"') == 3
    assert 'fill="var(--white)"' in _svg("TOPSHP25", result)
    assert 'fill="var(--orange)"' in _svg("TOPSHP25", result)
    assert _svg("TOPSHP29", result).count('data-pattern="nested-square-board"') == 3
    assert 'fill="var(--green)"' in _svg("TOPSHP29", result)
    assert 'fill="var(--yellow)"' in _svg("TOPSHP30", result)
    assert 'fill="var(--white)"' in _svg("TOPSHP37", result)
    assert 'fill="var(--black)"' in _svg("TOPSHP40", result)
    assert 'fill="var(--white)"' in _svg("TOPSHP44", result)

    assert _svg("TOPSHP38", result).count('data-pattern="quadrant-square-board"') == 4
    assert _svg("TOPSHP41", result).count('data-pattern="horizontal-square-board"') == 3
    assert 'fill="var(--white)"' in _svg("TOPSHP41", result)
    assert _svg("TOPSHP43", result).count('data-pattern="compound-horizontal-square-board"') == 3
    assert _svg("TOPSHP43", result).count('data-pattern="nested-square-board"') == 2

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 11
    assert (ROOT / "catalog" / "owned_repair_batch58.md").exists()
    print("standard repair batch 50: OK")


if __name__ == "__main__":
    main()
