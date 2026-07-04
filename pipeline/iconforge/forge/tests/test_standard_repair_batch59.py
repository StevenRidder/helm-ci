"""Smoke Standard Repair Batch 59.

Run:  python3 -m forge.tests.test_standard_repair_batch59
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch59


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch67.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch59.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 14
    assert not result["blockers"]
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}

    for row in result["symbols"]:
        svg = _svg(row["asset"], result)
        assert 'data-repair-batch="standard-repair-batch59"' in svg
        assert "generated-owned-artwork" in svg
        assert row["chart1_parity_gate"]

    assert '<circle cx="32" cy="32" r="18"' in _svg("BOYSPH60", result)
    assert 'fill="var(--red)"' in _svg("BOYSPH60", result)
    assert 'fill="var(--yellow)"' in _svg("BOYSPH62", result)
    assert _svg("BOYSPH65", result).count('data-pattern="vertical-sphere-band"') == 2
    assert _svg("BOYSPH66", result).count('data-pattern="horizontal-sphere-band"') == 3
    assert _svg("BOYSPH70", result).count('fill="var(--black)"') >= 2
    assert _svg("BOYSPH70", result).count('fill="var(--yellow)"') == 1
    assert 'points="32,11 16,48 48,48"' in _svg("BOYSPH79", result)
    assert 'data-pattern="horizontal-cone-band"' in _svg("BOYSPH79", result)

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 14
    assert (ROOT / "catalog" / "owned_repair_batch67.md").exists()
    print("standard repair batch 59: OK")


if __name__ == "__main__":
    main()
