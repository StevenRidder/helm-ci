"""Smoke Standard Repair Batch 32.

Run:  python3 -m forge.tests.test_standard_repair_batch32
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch32


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch40.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch32.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 5
    assert not result["blockers"]
    assert {row["asset"] for row in result["symbols"]} == set(standard_repair_batch32.REPAIRS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}

    unknown = _svg("RCLDEF01", result)
    assert "M21 22 L32 10 L43 22" in unknown
    assert "M21 42 L32 54 L43 42" in unknown
    assert unknown.count(">?</text>") == 2
    assert "L45 32" not in unknown

    one_way = _svg("RDOCAL02", result)
    assert "M21 22 L32 10 L43 22" in one_way
    assert "M21 42 L32 54 L43 42" not in one_way

    two_way = _svg("RDOCAL03", result)
    assert "M21 22 L32 10 L43 22" in two_way
    assert "M21 42 L32 54 L43 42" in two_way
    assert "M32 22 V42" not in two_way

    assert "M32 7 V57" in _svg("RECTRC56", result)
    assert '<circle cx="32" cy="32" r="4"' not in _svg("RECTRC56", result)
    assert "M22 42 L32 53 L42 42" in _svg("RECTRC56", result)
    assert "M32 7 V57" in _svg("RECTRC58", result)
    assert '<circle cx="32" cy="32" r="4"' not in _svg("RECTRC58", result)
    assert "M22 38 L32 25 L42 38" in _svg("RECTRC58", result)

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 5
    assert (ROOT / "catalog" / "owned_repair_batch40.md").exists()
    print("standard repair batch 32: OK")


if __name__ == "__main__":
    main()
