"""Smoke Standard Judge Batch 094 rerun.

Run:  python3 -m forge.tests.test_standard_judge_batch94_rerun
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_judge_batch94_rerun


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "standard_judge_batch_094_rerun.json"


def main():
    result = standard_judge_batch94_rerun.build()
    assert result["batch_id"] == "standard_judge_batch_094_rerun"
    assert result["summary"]["selected"] == 35
    assert result["summary"]["pass"] == 35
    assert result["summary"]["fail"] == 0
    assert result["summary"]["final_approved"] == 0
    assert "FSHHAV02" in result["summary"]["passed_assets"]
    assert "VEGATN04" in result["summary"]["passed_assets"]
    assert all(verdict["pass"] for verdict in result["verdicts"])
    assert all(not verdict["final_approved"] for verdict in result["verdicts"])
    assert all(verdict["output_candidate_status"] == "judge_pass_pending_final_approval" for verdict in result["verdicts"])
    assert REPORT.exists()
    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["pass"] == 35
    assert (ROOT / "catalog" / "standard_judge_batch_094_rerun.md").exists()
    print("standard judge batch 094 rerun: OK")


if __name__ == "__main__":
    main()
