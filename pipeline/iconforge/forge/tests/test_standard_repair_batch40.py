"""Smoke Standard Repair Batch 40.

Run:  python3 -m forge.tests.test_standard_repair_batch40
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch40


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch48.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch40.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 20
    assert not result["blockers"]
    assert {row["asset"] for row in result["symbols"]} == set(standard_repair_batch40.REPAIRS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}

    assert 'data-repair-batch="standard-repair-batch40"' in _svg("TOPSHP22", result)
    assert '<rect x="19" y="12" width="26" height="40" fill="var(--red)"' in _svg("TOPSHP22", result)
    assert '<rect x="19" y="12" width="26" height="40" fill="var(--black)"' in _svg("TOPSHP23", result)
    assert '<rect x="19" y="12" width="26" height="40" fill="var(--green)"' in _svg("TOPSHP24", result)
    assert 'fill="var(--orange)"' in _svg("TOPSHP25", result)
    assert 'fill="var(--black)"' in _svg("TOPSHP28", result)
    assert _svg("TOPSHP29", result).count('fill="var(--red)"') >= 2
    assert 'fill="var(--yellow)"' in _svg("TOPSHP30", result)
    assert 'fill="var(--white)"' in _svg("TOPSHP34", result)
    assert 'fill="var(--orange)"' in _svg("TOPSHP38", result)
    assert 'y="25.3"' in _svg("TOPSHP43", result)
    assert 'fill="var(--yellow)"' in _svg("TOPSHP44", result)

    for asset in standard_repair_batch40.REPAIRS:
        svg = _svg(asset, result)
        assert "data-repair-batch=\"standard-repair-batch40\"" in svg
        assert "generated-owned-artwork" in svg

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 20
    assert (ROOT / "catalog" / "owned_repair_batch48.md").exists()
    print("standard repair batch 40: OK")


if __name__ == "__main__":
    main()
