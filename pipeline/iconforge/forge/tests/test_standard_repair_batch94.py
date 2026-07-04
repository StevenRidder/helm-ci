"""Smoke Standard Repair Batch 94.

Run:  python3 -m forge.tests.test_standard_repair_batch94
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch94


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch94.json"


def _svg(asset: str, result: dict) -> str:
    row = next(row for row in result["symbols"] if row["asset"] == asset)
    return (ROOT / row["after_svg"]).read_text()


def main():
    result = standard_repair_batch94.build(render_outputs=False)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 35
    assert {row["asset"] for row in result["symbols"]} == set(standard_repair_batch94.TARGETS)
    assert all(row["qa"]["visual_parity"] == "repaired_pending_judge_rerun" for row in result["symbols"])
    assert all(row["source_judge"] == "catalog/standard_judge_batch_088_091_initial.json" for row in result["symbols"])
    assert "C27 27 38 27" in _svg("FSHHAV02", result)
    assert 'stroke="var(--magenta)"' in _svg("PIPARE51", result)
    assert ">R</text>" in _svg("RCRTCL11", result)
    assert 'stroke="var(--blue)"' in _svg("SCLBDY51", result)
    assert "var(--brown)" in _svg("VEGATN04", result)
    assert REPORT.exists()
    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 35
    assert (ROOT / "catalog" / "owned_repair_batch94.md").exists()
    print("standard repair batch 94: OK")


if __name__ == "__main__":
    main()
