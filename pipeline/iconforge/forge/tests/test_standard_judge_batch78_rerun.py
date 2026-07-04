"""Smoke Standard Judge Batch 078 rerun.

Run:  python3 -m forge.tests.test_standard_judge_batch78_rerun
"""
from __future__ import annotations

import json
from pathlib import Path



ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "standard_judge_batch_078_rerun.json"


def main():
    result = json.loads(REPORT.read_text())
    assert result["batch_id"] == "standard_judge_batch_078_rerun"
    assert result["summary"]["selected"] == 12
    assert result["summary"]["pass"] == 10
    assert result["summary"]["fail"] == 2
    assert result["summary"]["final_approved"] == 0
    assert set(result["summary"]["failed_assets"]) == {"SCALEB10", "SCALEB11"}
    assert all(not verdict["final_approved"] for verdict in result["verdicts"])
    failed = {verdict["symbol_id"]: verdict for verdict in result["verdicts"] if not verdict["pass"]}
    assert "segmented one-mile vertical scale bar" in failed["SCALEB10"]["required_change"]
    assert "segmented 10-mile vertical latitude scale" in failed["SCALEB11"]["required_change"]
    assert REPORT.exists()
    assert (ROOT / "catalog" / "standard_judge_batch_078_rerun.md").exists()
    print("standard judge batch 078 rerun: OK")


if __name__ == "__main__":
    main()
