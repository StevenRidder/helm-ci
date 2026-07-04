"""Smoke Standard Repair Batch 2.

Run:  python -m forge.tests.test_standard_repair_batch2
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch2


ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    result = standard_repair_batch2.build(render_outputs=False)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 20
    by_asset = {row["asset"]: row for row in result["symbols"]}
    assert by_asset["BOYCAN72"]["after_svg"] == "assets/svg/owned_repair_batch10/BOYCAN72.svg"
    assert "red" in (ROOT / by_asset["BOYCAN72"]["after_svg"]).read_text()
    assert "green" in (ROOT / by_asset["BOYCON67"]["after_svg"]).read_text()
    assert by_asset["BLKADJ01"]["qa"]["final_approved"] is False
    saved = json.loads((ROOT / "catalog" / "owned_repair_batch10.json").read_text())
    assert saved["summary"]["failed_repaired"] == 20
    assert (ROOT / "catalog" / "owned_repair_batch10.md").exists()
    print("standard repair batch 2: OK")


if __name__ == "__main__":
    main()
