"""Smoke Standard Repair Batch 75.

Run:  python3 -m forge.tests.test_standard_repair_batch75
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch75


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch83.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch75.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == len(standard_repair_batch75.TARGETS)
    assert not result["blockers"]
    assert {row["asset"] for row in result["symbols"]} == set(standard_repair_batch75.TARGETS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}
    assert all(row["source_judge"] for row in result["symbols"])

    assert 'fill="var(--black)"' in _svg("BCNGEN68", result)
    assert 'fill="var(--yellow)"' in _svg("BCNGEN69", result)
    assert 'fill="var(--orange)"' in _svg("BCNGEN79", result)
    assert 'fill="var(--black)"' in _svg("BCNGEN80", result)
    assert 'Q32 49 27 45' in _svg("BCNSPR62", result)
    assert '<circle cx="32" cy="27"' in _svg("BOYISD12", result)
    assert '<circle cx="32" cy="38"' in _svg("BOYISD12", result)
    assert 'fill="var(--green)"' not in _svg("BOYMOR03", result)
    assert 'C27 34 37 34 38 38 Z' in _svg("BOYMOR11", result)
    assert '<circle cx="32" cy="32" r="5" fill="var(--red)"' in _svg("BOYSAW12", result)
    assert '<circle cx="32" cy="32" r="5" fill="var(--yellow)"' in _svg("BOYSPP11", result)
    assert 'M31 25 L39 39 H24 Z' in _svg("BOYSPP15", result)
    assert 'M25 30 L39 27 L36 39 L22 42 Z' in _svg("BOYSPP25", result)
    assert "generic_symbol" not in "".join(_svg(asset, result) for asset in standard_repair_batch75.TARGETS)

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == len(standard_repair_batch75.TARGETS)
    assert (ROOT / "catalog" / "owned_repair_batch83.md").exists()
    print("standard repair batch 75: OK")


if __name__ == "__main__":
    main()
