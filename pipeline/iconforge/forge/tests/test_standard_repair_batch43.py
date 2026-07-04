"""Smoke Standard Repair Batch 43.

Run:  python3 -m forge.tests.test_standard_repair_batch43
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch43


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch51.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch43.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 20
    assert not result["blockers"]
    assert {row["asset"] for row in result["symbols"]} == set(standard_repair_batch43.REPAIRS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}

    assert 'data-repair-batch="standard-repair-batch43"' in _svg("TOPSHPA4", result)
    assert 'points="24,10 52,18 40,54 12,46"' in _svg("TOPSHPA4", result)
    assert 'fill="var(--black)"' in _svg("TOPSHPA5", result)
    assert 'fill="var(--green)"' in _svg("TOPSHPA8", result)
    assert 'y="32.0"' in _svg("TOPSHPA9", result)
    assert '<circle cx="32" cy="32" r="20"' in _svg("TOPSHPD1", result)
    assert '<circle cx="32" cy="32" r="5"' in _svg("TOPSHPD5", result)
    assert 'fill="var(--black)"' in _svg("TOPSHPD5", result)
    assert "M18 18 L46 46" in _svg("TOPSHPI1", result)
    assert "M18 46 L46 18" in _svg("TOPSHPI3", result)
    assert "M20 48 L44 16" in _svg("TOPSHPJ1", result)
    assert 'stroke="var(--black)"' in _svg("TOPSHPR1", result)
    assert 'stroke="var(--red)"' in _svg("TOPSHPS1", result)
    assert 'fill="var(--red)"' in _svg("TOPSHPT1", result)

    for asset in standard_repair_batch43.REPAIRS:
        svg = _svg(asset, result)
        assert "data-repair-batch=\"standard-repair-batch43\"" in svg
        assert "generated-owned-artwork" in svg

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 20
    assert (ROOT / "catalog" / "owned_repair_batch51.md").exists()
    print("standard repair batch 43: OK")


if __name__ == "__main__":
    main()
