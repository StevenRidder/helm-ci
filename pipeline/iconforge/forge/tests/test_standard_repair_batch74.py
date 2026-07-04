"""Smoke Standard Repair Batch 74.

Run:  python3 -m forge.tests.test_standard_repair_batch74
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch74


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch82.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch74.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == len(standard_repair_batch74.TARGETS)
    assert not result["blockers"]
    assert {row["asset"] for row in result["symbols"]} == set(standard_repair_batch74.TARGETS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}
    assert all(row["source_judge"] for row in result["symbols"])

    assert 'M28 22 L36 25 L28 29 Z' in _svg("SSENTR01", result)
    assert '<circle cx="28" cy="28" r="2.2"' in _svg("SSLOCK01", result)
    assert 'M32.5 23 L38 32 H27 Z' in _svg("SSWARS01", result)
    assert 'stroke="var(--blue)" stroke-width="2.6"' in _svg("BUNSTA02", result)
    assert 'fill="var(--yellow)"' in _svg("ZZZZZZ01", result)
    assert 'fill="var(--red)"' in _svg("ZZZZZZ01", result)
    assert "generic_symbol" not in "".join(_svg(asset, result) for asset in standard_repair_batch74.TARGETS)

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == len(standard_repair_batch74.TARGETS)
    assert (ROOT / "catalog" / "owned_repair_batch82.md").exists()
    print("standard repair batch 74: OK")


if __name__ == "__main__":
    main()
