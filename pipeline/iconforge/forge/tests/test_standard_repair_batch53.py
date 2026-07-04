"""Smoke Standard Repair Batch 53.

Run:  python3 -m forge.tests.test_standard_repair_batch53
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch53


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch61.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch53.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 3
    assert not result["blockers"]
    assert {row["asset"] for row in result["symbols"]} == {"TOWERS55", "TOWERS94", "TOWERS97"}
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["source_judge"] for row in result["symbols"]} == {"catalog/standard_judge_batch_059_rerun.json"}

    for asset in ("TOWERS55", "TOWERS94", "TOWERS97"):
        svg = _svg(asset, result)
        assert "generated-owned-artwork" in svg
        assert 'data-repair-batch="standard-repair-batch53"' in svg
        assert 'data-pattern="bounded-diagonal-tower"' in svg
        assert "transform=" not in svg
        assert 'points="25,12 39,12 49,52 15,52"' in svg

    assert 'fill="var(--yellow)"' in _svg("TOWERS55", result)
    assert 'fill="var(--black)"' in _svg("TOWERS55", result)
    assert 'fill="var(--white)"' in _svg("TOWERS94", result)
    assert 'fill="var(--white)"' in _svg("TOWERS97", result)

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 3
    assert (ROOT / "catalog" / "owned_repair_batch61.md").exists()
    print("standard repair batch 53: OK")


if __name__ == "__main__":
    main()
