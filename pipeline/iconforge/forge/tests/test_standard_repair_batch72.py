"""Smoke Standard Repair Batch 72.

Run:  python3 -m forge.tests.test_standard_repair_batch72
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch72


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch80.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch72.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == len(standard_repair_batch72.TARGETS)
    assert not result["blockers"]
    assert {row["asset"] for row in result["symbols"]} == set(standard_repair_batch72.TARGETS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}
    assert all(row["source_judge"] for row in result["symbols"])

    assert ">F</text>" in _svg("UNITFTH1", result)
    assert ">M</text>" in _svg("UNITMTR1", result)
    assert 'stroke="var(--orange)"' not in _svg("VECGND01", result)
    assert 'stroke="var(--black)" stroke-width="2.4"' in _svg("VECGND01", result)
    assert 'stroke="var(--green)" stroke-width="2.4"' in _svg("VECGND21", result)
    assert 'stroke="var(--black)" stroke-width="2.4"' in _svg("VECWTR01", result)
    assert 'stroke="var(--green)" stroke-width="2.4"' in _svg("VECWTR21", result)
    assert '<rect x="29" y="21" width="6" height="22"' in _svg("VTCLMK01", result)
    assert 'M32 30 V39' in _svg("VTCLMK01", result)
    assert "generic_symbol" not in "".join(_svg(asset, result) for asset in standard_repair_batch72.TARGETS)

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == len(standard_repair_batch72.TARGETS)
    assert (ROOT / "catalog" / "owned_repair_batch80.md").exists()
    print("standard repair batch 72: OK")


if __name__ == "__main__":
    main()
