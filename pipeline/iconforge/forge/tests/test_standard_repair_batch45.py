"""Smoke Standard Repair Batch 45.

Run:  python3 -m forge.tests.test_standard_repair_batch45
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch45


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch53.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch45.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 43
    assert not result["blockers"]
    assert {row["asset"] for row in result["symbols"]} == set(standard_repair_batch45.REPAIRS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}

    assert 'data-repair-batch="standard-repair-batch45"' in _svg("BOYBAR01", result)
    assert 'points="20,18 44,18 50,32 44,46 20,46 14,32"' in _svg("BOYBAR01", result)
    assert 'points="20,16 44,16 48,48 16,48"' in _svg("BOYCAN60", result)
    assert 'points="32,11 16,48 48,48"' in _svg("BOYCON60", result)
    assert 'fill="var(--red)"' in _svg("BOYCAN60", result)
    assert 'fill="var(--green)"' in _svg("BOYCAN61", result)
    assert 'fill="var(--yellow)"' in _svg("BOYCAN68", result)
    assert _svg("BOYCAN70", result).count('fill="var(--black)"') >= 2
    assert _svg("BOYCAN74", result).count('fill="var(--red)"') >= 3
    assert 'fill="var(--orange)"' in _svg("BOYCON77", result)
    assert 'fill="var(--blue)"' in _svg("BOYCON81", result)

    for asset in standard_repair_batch45.REPAIRS:
        svg = _svg(asset, result)
        assert "generated-owned-artwork" in svg

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 43
    assert (ROOT / "catalog" / "owned_repair_batch53.md").exists()
    print("standard repair batch 45: OK")


if __name__ == "__main__":
    main()
