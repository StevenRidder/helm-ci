"""Smoke Standard Repair Batch 52.

Run:  python3 -m forge.tests.test_standard_repair_batch52
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch52


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch60.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch52.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 24
    assert not result["blockers"]
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}
    assert sum(1 for row in result["symbols"] if row["asset"].startswith("BCNTOW")) == 15
    assert sum(1 for row in result["symbols"] if row["asset"].startswith("BCNSTK")) == 9

    tower = _svg("BCNTOW60", result)
    assert 'data-repair-batch="standard-repair-batch52"' in tower
    assert 'points="25,12 39,12 49,52 15,52"' in tower
    assert 'fill="var(--red)"' in tower

    stake = _svg("BCNSTK60", result)
    assert 'data-repair-batch="standard-repair-batch52"' in stake
    assert 'x="28" y="12" width="8" height="40"' in stake
    assert 'data-pattern="solid-stake"' in stake
    assert 'fill="var(--red)"' in stake

    assert _svg("BCNTOW64", result).count('data-pattern="horizontal-tower"') == 2
    assert _svg("BCNTOW85", result).count('data-pattern="vertical-tower"') == 2
    assert _svg("BCNSTK78", result).count('data-pattern="horizontal-stake"') == 2

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 24
    assert (ROOT / "catalog" / "owned_repair_batch60.md").exists()
    print("standard repair batch 52: OK")


if __name__ == "__main__":
    main()
