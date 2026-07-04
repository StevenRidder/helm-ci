"""Smoke Standard Repair Batch 86.

Run:  python3 -m forge.tests.test_standard_repair_batch86
"""
from __future__ import annotations

from pathlib import Path

from .. import standard_repair_batch86


ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    result = standard_repair_batch86.build(render_outputs=False)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 7
    assert {row["asset"] for row in result["symbols"]} == {
        "NMKINF38",
        "NMKINF53",
        "SCALEB10",
        "SCALEB11",
        "TOPMAR90",
        "TOPMAR93",
        "WATTUR02",
    }
    for row in result["symbols"]:
        assert row["qa"]["visual_parity"] == "repaired_pending_judge_rerun"
        assert row["source_judge"].startswith("catalog/standard_judge_batch_")
        assert (ROOT / row["after_svg"]).exists()
    assert (ROOT / "catalog" / "owned_repair_batch86.json").exists()
    assert (ROOT / "catalog" / "owned_repair_batch86.md").exists()
    print("standard repair batch 86: OK")


if __name__ == "__main__":
    main()
