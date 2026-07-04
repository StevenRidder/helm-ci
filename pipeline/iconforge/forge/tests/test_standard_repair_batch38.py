"""Smoke Standard Repair Batch 38.

Run:  python3 -m forge.tests.test_standard_repair_batch38
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch38


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch46.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch38.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 20
    assert not result["blockers"]
    assert {row["asset"] for row in result["symbols"]} == set(standard_repair_batch38.REPAIRS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}

    assert 'points="18,22 46,22 32,52"' in _svg("TOPMA100", result)
    assert 'points="32,12 18,42 46,42"' in _svg("TOPMA102", result)
    assert 'fill="var(--red)"' in _svg("TOPMA106", result)
    assert 'stroke="var(--red)"' in _svg("TOPMA107", result)
    assert 'stroke="var(--green)"' in _svg("TOPMA109", result)
    assert "M32 13 V51" in _svg("TOPMA111", result)
    assert "M19 19 L45 45" in _svg("TOPMA113", result)
    assert '<rect x="18" y="14" width="28" height="36" fill="var(--red)"' in _svg("TOPMA114", result)
    assert '<rect x="18" y="14" width="28" height="36" fill="var(--green)"' in _svg("TOPMA115", result)
    assert 'fill="var(--red)"' in _svg("TOPMA116", result)
    assert '<circle cx="32" cy="32" r="16"' in _svg("TOPMA117", result)
    assert '<circle cx="32" cy="32" r="16"' in _svg("TOPMAR01", result)
    assert "M20 29 L32 51 L44 29" in _svg("TOPMAR87", result)
    assert "M20 35 L32 13 L44 35" in _svg("TOPMAR88", result)
    assert "M22 30 L32 50 L42 30" in _svg("TOPMAR90", result)
    assert "M22 34 L32 14 L42 34" in _svg("TOPMAR93", result)
    assert 'fill="var(--orange)"' in _svg("TOPMAR98", result)
    assert 'fill="var(--yellow)"' in _svg("TOPMAR99", result)

    for asset in standard_repair_batch38.REPAIRS:
        svg = _svg(asset, result)
        assert "data-repair-batch=\"standard-repair-batch38\"" in svg
        assert "generated-owned-artwork" in svg

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 20
    assert (ROOT / "catalog" / "owned_repair_batch46.md").exists()
    print("standard repair batch 38: OK")


if __name__ == "__main__":
    main()
