"""Smoke Standard Judge Batch 093 rerun.

Run:  python3 -m forge.tests.test_standard_judge_batch93_rerun
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_judge_batch93_rerun


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "standard_judge_batch_093_rerun.json"


def main():
    result = standard_judge_batch93_rerun.build()
    assert result["batch_id"] == "standard_judge_batch_093_rerun"
    assert result["summary"]["selected"] == 16
    assert result["summary"]["pass"] == 16
    assert result["summary"]["fail"] == 0
    assert result["summary"]["final_approved"] == 0
    assert "CBLSUB06" in result["summary"]["passed_assets"]
    assert "DQUALA11" in result["summary"]["passed_assets"]
    assert all(verdict["pass"] for verdict in result["verdicts"])
    assert all(not verdict["final_approved"] for verdict in result["verdicts"])
    assert all(verdict["output_candidate_status"] == "judge_pass_pending_final_approval" for verdict in result["verdicts"])
    assert REPORT.exists()
    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["pass"] == 16
    assert (ROOT / "catalog" / "standard_judge_batch_093_rerun.md").exists()
    print("standard judge batch 093 rerun: OK")


if __name__ == "__main__":
    main()
