"""Smoke Standard Repair Batch 85.

Run:  python3 -m forge.tests.test_standard_repair_batch85
"""
from __future__ import annotations

from pathlib import Path

from .. import standard_repair_batch85


ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    result = standard_repair_batch85.build(render_outputs=False)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 2
    assert result["source_judge"] == "catalog/standard_judge_batch_080_rerun.json"
    assets = {row["asset"] for row in result["symbols"]}
    assert assets == {"VECWTR01", "VECWTR21"}
    for row in result["symbols"]:
        assert row["qa"]["visual_parity"] == "repaired_pending_judge_rerun"
        assert row["source_judge"] == "catalog/standard_judge_batch_080_rerun.json"
        assert (ROOT / row["after_svg"]).exists()
    assert (ROOT / "catalog" / "owned_repair_batch85.json").exists()
    assert (ROOT / "catalog" / "owned_repair_batch85.md").exists()
    print("standard repair batch 85: OK")


if __name__ == "__main__":
    main()
