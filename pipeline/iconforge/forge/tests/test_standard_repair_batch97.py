"""Smoke Standard Repair Batch 97.

Run:  python3 -m forge.tests.test_standard_repair_batch97
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch97


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch97.json"


def _svg(asset: str, result: dict) -> str:
    row = next(row for row in result["symbols"] if row["asset"] == asset)
    return (ROOT / row["after_svg"]).read_text()


def main():
    result = standard_repair_batch97.build(render_outputs=False)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 2
    assert {row["asset"] for row in result["symbols"]} == {"BCNCON81", "boyspp50"}
    assert all(row["qa"]["visual_parity"] == "repaired_pending_judge_rerun" for row in result["symbols"])
    assert all(row["source_judge"] == "catalog/standard_judge_batch_083_084_rerun.json" for row in result["symbols"])
    bcn = _svg("BCNCON81", result)
    assert bcn.count("var(--blue)") == 2
    assert "var(--red)" in bcn
    assert "var(--white)" in bcn
    boyspp = _svg("boyspp50", result)
    assert 'fill="var(--yellow)"' in boyspp
    assert "special_purpose_buoy_or_waterway_marker" in json.dumps(result)
    assert REPORT.exists()
    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 2
    assert (ROOT / "catalog" / "owned_repair_batch97.md").exists()
    print("standard repair batch 97: OK")


if __name__ == "__main__":
    main()
