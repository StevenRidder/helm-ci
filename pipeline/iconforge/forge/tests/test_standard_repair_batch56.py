"""Smoke Standard Repair Batch 56.

Run:  python3 -m forge.tests.test_standard_repair_batch56
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch56


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch64.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch56.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 21
    assert not result["blockers"]
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["source_judge"] for row in result["symbols"]} == {"catalog/standard_judge_batch_015.json"}

    for asset in (row["asset"] for row in result["symbols"]):
        svg = _svg(asset, result)
        assert 'data-repair-batch="standard-repair-batch56"' in svg
        assert "generated-owned-artwork" in svg
        assert 'stroke="var(--black)"' in svg

    assert '<rect x="26" y="16" width="12" height="32"' in _svg("TOPSHQ06", result)
    assert "L32 26 L40 18" in _svg("TOPSHQ07", result)
    assert "H48 V37 H37" in _svg("TOPSHQ08", result)
    assert "35,17 29,17" in _svg("TOPSHQ15", result)
    assert "46,18 46,28 36,28 36,50" in _svg("TOPSHQ28", result)
    assert "32,15 48,46 16,46" in _svg("TOPSHQ24", result)
    assert "16,18 48,18 32,48" in _svg("TOPSHQ25", result)
    assert '<circle cx="32" cy="22" r="8"' in _svg("TOPSHQ18", result)
    assert '<circle cx="32" cy="21" r="12"' in _svg("TOPSHQ31", result)
    assert "fill=\"var(--green)\"" in _svg("TOPSHQ24", result)
    assert "fill=\"var(--white)\"" in _svg("TOPSHQ17", result)

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 21
    assert (ROOT / "catalog" / "owned_repair_batch64.md").exists()
    print("standard repair batch 56: OK")


if __name__ == "__main__":
    main()
