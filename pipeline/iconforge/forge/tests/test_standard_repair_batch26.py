"""Smoke Standard Repair Batch 26.

Run:  python3 -m forge.tests.test_standard_repair_batch26
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch26


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch34.json"


def main():
    result = standard_repair_batch26.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 1
    assert not result["blockers"]

    row = result["symbols"][0]
    assert row["asset"] == "BCNGEN64"
    assert row["source_judge"] == "catalog/standard_judge_batch_007_009_beacon_rerun.json"
    assert row["qa"]["visual_parity"] == "repaired_pending_judge_rerun"
    assert len(row["after_renders"]) == 3

    svg = (ROOT / row["after_svg"]).read_text()
    assert 'data-repair-batch="standard-repair-batch26"' in svg
    assert svg.count('fill="var(--red)"') == 2
    assert svg.count('fill="var(--white)"') == 3
    assert 'y="12"' in svg
    assert 'y="20.75"' in svg
    assert 'y="29.5"' in svg
    assert 'y="38.25"' in svg
    assert "var(--green)" not in svg
    assert "var(--yellow)" not in svg

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 1
    assert (ROOT / "catalog" / "owned_repair_batch34.md").exists()
    print("standard repair batch 26: OK")


if __name__ == "__main__":
    main()
