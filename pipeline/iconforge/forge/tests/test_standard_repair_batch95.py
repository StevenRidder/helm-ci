"""Smoke Standard Repair Batch 95.

Run:  python3 -m forge.tests.test_standard_repair_batch95
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch95


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch95.json"


def _svg(asset: str, result: dict) -> str:
    row = next(row for row in result["symbols"] if row["asset"] == asset)
    return (ROOT / row["after_svg"]).read_text()


def main():
    result = standard_repair_batch95.build(render_outputs=False)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 4
    assert {row["asset"] for row in result["symbols"]} == set(standard_repair_batch95.TARGETS)
    assert all(row["qa"]["visual_parity"] == "repaired_pending_judge_rerun" for row in result["symbols"])
    assert 'fill="var(--magenta)"' in _svg("LIGHTS05", result)
    assert ">Obstn</text>" in _svg("OBSTRN04", result)
    assert 'fill="var(--yellow)"' in _svg("TOWERS74|;TX(OBJNAM", result)
    assert ">Wk</text>" in _svg("WRECKS02", result)
    assert REPORT.exists()
    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 4
    assert (ROOT / "catalog" / "owned_repair_batch95.md").exists()
    print("standard repair batch 95: OK")


if __name__ == "__main__":
    main()
