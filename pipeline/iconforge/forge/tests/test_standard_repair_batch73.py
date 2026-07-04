"""Smoke Standard Repair Batch 73.

Run:  python3 -m forge.tests.test_standard_repair_batch73
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch73


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch81.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch73.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == len(standard_repair_batch73.TARGETS)
    assert not result["blockers"]
    assert {row["asset"] for row in result["symbols"]} == set(standard_repair_batch73.TARGETS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}
    assert all(row["source_judge"] for row in result["symbols"])

    assert 'stroke="var(--brown)" stroke-width="2"' in _svg("WIMCON01", result)
    assert 'stroke="var(--black)" stroke-width="2"' in _svg("WIMCON11", result)
    assert '<circle cx="32" cy="32" r="10"' in _svg("WNDFRM51", result)
    assert 'stroke="var(--brown)" stroke-width="2"' in _svg("WNDFRM51", result)
    assert 'stroke="var(--black)" stroke-width="2"' in _svg("WNDFRM61", result)
    assert 'M26 26 L38 38 M38 26 L26 38' in _svg("WNDMIL02", result)
    assert 'stroke="var(--black)" stroke-width="1.8"' in _svg("WNDMIL12", result)
    assert "generic_symbol" not in "".join(_svg(asset, result) for asset in standard_repair_batch73.TARGETS)

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == len(standard_repair_batch73.TARGETS)
    assert (ROOT / "catalog" / "owned_repair_batch81.md").exists()
    print("standard repair batch 73: OK")


if __name__ == "__main__":
    main()
