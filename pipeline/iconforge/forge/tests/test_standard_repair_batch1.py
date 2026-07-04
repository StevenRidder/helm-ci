"""Smoke the first standard repair batch.

Run:  python -m forge.tests.test_standard_repair_batch1
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch1


ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    result = standard_repair_batch1.build(render_outputs=False)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 28
    by_asset = {row["asset"]: row for row in result["symbols"]}
    assert by_asset["BCNGEN65"]["after_svg"] == "assets/svg/owned_repair_batch9/BCNGEN65.svg"
    assert "green" in (ROOT / by_asset["BCNGEN65"]["after_svg"]).read_text()
    assert by_asset["BCNLAT15"]["qa"]["visual_parity"] == "repaired_pending_judge_rerun"
    assert "BCNCON81" not in by_asset

    saved = json.loads((ROOT / "catalog" / "owned_repair_batch9.json").read_text())
    assert saved["summary"]["failed_repaired"] == 28
    assert (ROOT / "catalog" / "owned_repair_batch9.md").exists()
    print("standard repair batch 1: OK")


if __name__ == "__main__":
    main()
