"""Smoke Standard Judge Batch 092 rerun.

Run:  python3 -m forge.tests.test_standard_judge_batch92_rerun
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_judge_batch92_rerun


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "standard_judge_batch_092_rerun.json"


def main():
    result = standard_judge_batch92_rerun.build()
    assert result["batch_id"] == "standard_judge_batch_092_rerun"
    assert result["summary"]["selected"] == 20
    assert result["summary"]["pass"] == 4
    assert result["summary"]["fail"] == 16
    assert result["summary"]["final_approved"] == 0
    assert set(result["summary"]["passed_assets"]) == {
        "CLRLIN01",
        "ERBLNA01",
        "ERBLNB01",
        "FOULAR01",
    }
    assert "DQUALA11" in result["summary"]["failed_assets"]
    assert all(not verdict["final_approved"] for verdict in result["verdicts"])
    assert REPORT.exists()
    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["fail"] == 16
    assert (ROOT / "catalog" / "standard_judge_batch_092_rerun.md").exists()
    print("standard judge batch 092 rerun: OK")


if __name__ == "__main__":
    main()
