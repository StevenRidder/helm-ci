"""Smoke Standard Repair Batch 65.

Run:  python3 -m forge.tests.test_standard_repair_batch65
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch65


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch73.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch65.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 6
    assert not result["blockers"]
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}

    assert {row["asset"] for row in result["symbols"]} == set(standard_repair_batch65.TARGETS)
    assert 'data-repair-batch="standard-repair-batch65"' in _svg("BOYSUP01", result)
    assert 'points="20,28 44,28 49,41 40,51 24,51 15,41"' in _svg("BOYSUP01", result)
    assert 'fill="var(--black)"' in _svg("BOYSUP02", result)
    assert 'M32 23 V15' in _svg("BOYSUP03", result)
    assert 'fill="var(--yellow)"' in _svg("BOYSUP62", result)
    assert 'data-pattern="vertical-super-buoy-band"' in _svg("BOYSUP65", result)
    assert 'data-pattern="horizontal-super-buoy-band"' in _svg("BOYSUP66", result)

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 6
    assert (ROOT / "catalog" / "owned_repair_batch73.md").exists()
    print("standard repair batch 65: OK")


if __name__ == "__main__":
    main()
