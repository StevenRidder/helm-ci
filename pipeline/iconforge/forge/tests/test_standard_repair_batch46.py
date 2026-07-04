"""Smoke Standard Repair Batch 46.

Run:  python3 -m forge.tests.test_standard_repair_batch46
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch46


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch54.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch46.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 71
    assert not result["blockers"]
    assert {row["asset"] for row in result["symbols"]} == set(standard_repair_batch46.REPAIRS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}

    assert 'data-repair-batch="standard-repair-batch46"' in _svg("BOYCAN72", result)
    assert 'points="20,16 44,16 48,48 16,48"' in _svg("BOYCAN72", result)
    assert 'points="32,11 16,48 48,48"' in _svg("BOYCON67", result)
    assert 'points="24,12 40,12 46,48 18,48"' in _svg("BOYPIL60", result)
    assert '<circle cx="32" cy="32" r="18"' in _svg("BOYSPH60", result)
    assert 'points="28,10 36,10 40,52 24,52"' in _svg("BOYSPR60", result)
    assert 'points="18,18 46,18 52,40 42,52 22,52 12,40"' in _svg("BOYSUP62", result)
    assert 'fill="var(--red)"' in _svg("BOYLAT14", result)
    assert 'fill="var(--green)"' in _svg("BOYLAT13", result)
    assert 'fill="var(--black)"' in _svg("BOYPIL68", result)
    assert 'fill="var(--yellow)"' in _svg("BOYPIL68", result)
    assert 'fill="var(--orange)"' in _svg("BOYPIL81", result)
    assert 'fill="var(--gray)"' in _svg("BOYSUP02", result) or 'fill="var(--black)"' in _svg("BOYSUP02", result)

    for asset in standard_repair_batch46.REPAIRS:
        svg = _svg(asset, result)
        assert "generated-owned-artwork" in svg

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 71
    assert (ROOT / "catalog" / "owned_repair_batch54.md").exists()
    print("standard repair batch 46: OK")


if __name__ == "__main__":
    main()
