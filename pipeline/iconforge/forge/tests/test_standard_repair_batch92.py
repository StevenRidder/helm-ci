"""Smoke Standard Repair Batch 92.

Run:  python3 -m forge.tests.test_standard_repair_batch92
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch92


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch92.json"


def _svg(asset: str, result: dict) -> str:
    row = next(row for row in result["symbols"] if row["asset"] == asset)
    return (ROOT / row["after_svg"]).read_text()


def main():
    result = standard_repair_batch92.build(render_outputs=False)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 20
    assert {row["asset"] for row in result["symbols"]} == set(standard_repair_batch92.TARGETS)
    assert all(row["qa"]["visual_parity"] == "repaired_pending_judge_rerun" for row in result["symbols"])
    assert all(row["source_judge"] == "catalog/standard_judge_batch_088_091_initial.json" for row in result["symbols"])
    assert "C17 27 22 39" in _svg("CBLSUB06", result)
    assert 'fill="var(--orange)"' in _svg("CLRLIN01", result)
    assert _svg("CROSSX02", result).count("M") >= 9
    assert "stroke-dasharray" in _svg("DWLDEF01", result)
    assert "DW" in _svg("DWRTCL05", result)
    assert 'stroke-dasharray="12 5 2 5"' in _svg("ERBLNB01", result)
    assert REPORT.exists()
    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 20
    assert (ROOT / "catalog" / "owned_repair_batch92.md").exists()
    print("standard repair batch 92: OK")


if __name__ == "__main__":
    main()
