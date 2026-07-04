"""Smoke Standard Repair Batch 29.

Run:  python3 -m forge.tests.test_standard_repair_batch29
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch29


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch37.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch29.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 12
    assert not result["blockers"]

    assert {row["asset"] for row in result["symbols"]} == set(standard_repair_batch29.REPAIRS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}

    unknown = _svg("RCLDEF01", result)
    assert unknown.count(">?</text>") == 2
    assert "M32 8 L45 32 L32 56 L19 32 Z" in unknown

    assert "M32 8 L45 32 L32 56 L19 32 Z" in _svg("RDOCAL02", result)
    assert "M32 22 V42" in _svg("RDOCAL03", result)
    assert '<circle cx="32" cy="32" r="20"' in _svg("RDOSTA02", result)

    assert ">?</text>" in _svg("RECDEF51", result)
    assert "M22 27 L32 17 L42 27" in _svg("RECTRC55", result)
    assert '<circle cx="32" cy="32" r="4"' in _svg("RECTRC56", result)
    assert "M22 39 L32 27 L42 39" in _svg("RECTRC57", result)
    assert '<circle cx="32" cy="32" r="4"' in _svg("RECTRC58", result)

    for asset in ("RETRFL01", "RETRFL02"):
        svg = _svg(asset, result)
        assert "M22 10 V54" in svg
        assert "var(--magenta)" in svg

    transponder = _svg("RTPBCN02", result)
    assert '<circle cx="32" cy="32" r="21"' in transponder
    assert "stroke-dasharray" in transponder

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 12
    assert (ROOT / "catalog" / "owned_repair_batch37.md").exists()
    print("standard repair batch 29: OK")


if __name__ == "__main__":
    main()
