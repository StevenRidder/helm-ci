"""Smoke Standard Repair Batch 87.

Run:  python3 -m forge.tests.test_standard_repair_batch87
"""
from __future__ import annotations

from pathlib import Path

from .. import standard_repair_batch87


ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    result = standard_repair_batch87.build(render_outputs=False)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 8
    assert {row["asset"] for row in result["symbols"]} == {
        "TOPSHP47",
        "TOPSHP48",
        "TOPSHPI3",
        "TOPSHPJ1",
        "TOPSHPJ3",
        "TOPSHPP2",
        "TOPSHPR1",
        "TOPSHPS1",
    }
    for row in result["symbols"]:
        assert row["qa"]["visual_parity"] == "repaired_pending_judge_rerun"
        assert row["source_judge"].startswith("catalog/standard_judge_batch_")
        assert (ROOT / row["after_svg"]).exists()
    assert (ROOT / "catalog" / "owned_repair_batch87.json").exists()
    assert (ROOT / "catalog" / "owned_repair_batch87.md").exists()
    print("standard repair batch 87: OK")


if __name__ == "__main__":
    main()
