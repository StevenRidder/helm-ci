"""Smoke Standard Repair Batch 67.

Run:  python3 -m forge.tests.test_standard_repair_batch67
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch67


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch75.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch67.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 4
    assert not result["blockers"]
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}

    assert {row["asset"] for row in result["symbols"]} == set(standard_repair_batch67.TARGETS)
    assert 'data-repair-batch="standard-repair-batch67"' in _svg("BOYBAR01", result)
    assert 'data-pattern="horizontal-barrel-band"' in _svg("BOYBAR01", result)
    assert 'Q20 24 26 22 H38 Q44 24 44 32' in _svg("BOYBAR60", result)
    assert 'fill="var(--red)"' in _svg("BOYBAR60", result)
    assert 'fill="var(--green)"' in _svg("BOYBAR61", result)
    assert 'fill="var(--yellow)"' in _svg("BOYBAR62", result)

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 4
    assert (ROOT / "catalog" / "owned_repair_batch75.md").exists()
    print("standard repair batch 67: OK")


if __name__ == "__main__":
    main()
