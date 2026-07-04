"""Smoke Standard Judge Batch 052 rerun.

Run:  python3 -m forge.tests.test_standard_judge_batch52_rerun
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_judge_batch52_rerun


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "standard_judge_batch_052_rerun.json"


def main():
    result = standard_judge_batch52_rerun.build()
    assert result["batch_id"] == "standard_judge_batch_052_rerun"
    assert result["summary"]["selected"] == 9
    assert result["summary"]["pass"] == 9
    assert result["summary"]["fail"] == 0
    assert result["summary"]["final_approved"] == 0
    assert result["summary"]["failed_assets"] == []
    assert "TOPSHPT8;TE('%s'" in result["summary"]["passed_assets"]
    assert all(not verdict["final_approved"] for verdict in result["verdicts"])
    assert REPORT.exists()
    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["pass"] == 9
    assert (ROOT / "catalog" / "standard_judge_batch_052_rerun.md").exists()
    print("standard judge batch 052 rerun: OK")


if __name__ == "__main__":
    main()
