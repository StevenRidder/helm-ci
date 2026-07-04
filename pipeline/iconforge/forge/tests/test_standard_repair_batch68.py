"""Smoke Standard Repair Batch 68.

Run:  python3 -m forge.tests.test_standard_repair_batch68
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch68


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch76.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch68.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 4
    assert not result["blockers"]
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}

    assert {row["asset"] for row in result["symbols"]} == set(standard_repair_batch68.TARGETS)
    assert 'data-repair-batch="standard-repair-batch68"' in _svg("BOYBAR01", result)
    assert 'd="M18 17 H47 C55 17 59 25 59 33 C59 41 55 49 47 49 H18' in _svg("BOYBAR01", result)
    assert 'fill="var(--white)" stroke="none"' in _svg("BOYBAR01", result)
    assert 'd="M18 17 C27 17 30 49 18 49 C9 49 6 17 18 17"' in _svg("BOYBAR01", result)
    assert 'C18 38 19 35 24 35 C29 35 30 38 35 38' in _svg("BOYBAR01", result)
    assert 'stroke-width="2.6"' in _svg("BOYBAR01", result)
    assert _svg("BOYBAR01", result).count("<path") == 4
    assert 'V17' not in _svg("BOYBAR01", result)
    assert 'V55' not in _svg("BOYBAR01", result)
    assert 'fill="var(--white)"' in _svg("BOYBAR01", result)
    assert 'fill="var(--red)"' in _svg("BOYBAR60", result)
    assert 'fill="var(--green)"' in _svg("BOYBAR61", result)
    assert 'fill="var(--yellow)"' in _svg("BOYBAR62", result)

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 4
    assert (ROOT / "catalog" / "owned_repair_batch76.md").exists()
    print("standard repair batch 68: OK")


if __name__ == "__main__":
    main()
