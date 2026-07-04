"""Smoke Standard Repair Batch 66.

Run:  python3 -m forge.tests.test_standard_repair_batch66
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch66


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch74.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch66.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 5
    assert not result["blockers"]
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}

    assert {row["asset"] for row in result["symbols"]} == set(standard_repair_batch66.TARGETS)
    assert 'data-repair-batch="standard-repair-batch66"' in _svg("TERMNL01", result)
    assert 'M18 34 H46 L40 40 H24 Z' in _svg("TERMNL01", result)
    assert 'fill="var(--green)"' in _svg("TERMNL03", result)
    assert 'M20 42 L29 25 L34 42 Z' in _svg("TERMNL04", result)
    assert '>che</text>' in _svg("TERMNL07", result)
    assert 'M36 23 L43 29 V36' in _svg("TERMNL12", result)

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 5
    assert (ROOT / "catalog" / "owned_repair_batch74.md").exists()
    print("standard repair batch 66: OK")


if __name__ == "__main__":
    main()
