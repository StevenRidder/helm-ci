"""Smoke Standard Repair Batch 21.

Run:  python3 -m forge.tests.test_standard_repair_batch21
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch21


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch29.json"


def main():
    result = standard_repair_batch21.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 1
    assert not result["blockers"]

    row = result["symbols"][0]
    assert row["asset"] == "WRECKS01"
    assert row["source_judge"] == "catalog/standard_judge_batch_026_027_rerun.json"
    assert row["qa"]["visual_parity"] == "repaired_pending_judge_rerun"
    assert row["qa"]["final_approved"] is False
    assert len(row["after_renders"]) == 3

    svg = (ROOT / row["after_svg"]).read_text()
    assert 'data-repair-batch="standard-repair-batch21"' in svg
    assert "M13 43 H51" in svg
    assert "M39 20 L33 43" in svg
    assert "M18 31 L31 43 H18 Z" in svg
    assert "var(--black)" in svg
    assert "var(--blue)" not in svg
    assert "var(--gray)" not in svg
    assert "var(--white)" not in svg
    assert "<circle" not in svg

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 1
    assert (ROOT / "catalog" / "owned_repair_batch29.md").exists()
    print("standard repair batch 21: OK")


if __name__ == "__main__":
    main()
