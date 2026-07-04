"""Smoke Standard Judge Batch 087 rerun.

Run:  python3 -m forge.tests.test_standard_judge_batch87_rerun
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_judge_batch87_rerun


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "standard_judge_batch_087_rerun.json"


def main():
    result = standard_judge_batch87_rerun.build()
    assert result["batch_id"] == "standard_judge_batch_087_rerun"
    assert result["summary"]["selected"] == 8
    assert result["summary"]["pass"] == 8
    assert result["summary"]["fail"] == 0
    assert result["summary"]["final_approved"] == 0
    assert result["summary"]["failed_assets"] == []
    assert set(result["summary"]["passed_assets"]) == {
        "TOPSHP47",
        "TOPSHP48",
        "TOPSHPI3",
        "TOPSHPJ1",
        "TOPSHPJ3",
        "TOPSHPP2",
        "TOPSHPR1",
        "TOPSHPS1",
    }
    assert all(not verdict["final_approved"] for verdict in result["verdicts"])
    assert REPORT.exists()
    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["pass"] == 8
    assert (ROOT / "catalog" / "standard_judge_batch_087_rerun.md").exists()
    print("standard judge batch 087 rerun: OK")


if __name__ == "__main__":
    main()
