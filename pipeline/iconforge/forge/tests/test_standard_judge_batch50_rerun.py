"""Smoke Standard Judge Batch 050 rerun.

Run:  python3 -m forge.tests.test_standard_judge_batch50_rerun
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_judge_batch50_rerun


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "standard_judge_batch_050_rerun.json"


def main():
    result = standard_judge_batch50_rerun.build()
    assert result["batch_id"] == "standard_judge_batch_050_rerun"
    assert result["summary"]["selected"] == 27
    assert result["summary"]["pass"] == 27
    assert result["summary"]["fail"] == 0
    assert result["summary"]["final_approved"] == 0
    assert "TOPSHP76" in result["summary"]["passed_assets"]
    assert "TOPSHPA3" in result["summary"]["passed_assets"]
    assert all(verdict["pass"] for verdict in result["verdicts"])
    assert all(not verdict["final_approved"] for verdict in result["verdicts"])
    assert all(
        "catalog/owned_repair_batch50.json" in " ".join(verdict["source_refs_used"])
        for verdict in result["verdicts"]
    )
    assert REPORT.exists()
    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["pass"] == 27
    assert (ROOT / "catalog" / "standard_judge_batch_050_rerun.md").exists()
    print("standard judge batch 050 rerun: OK")


if __name__ == "__main__":
    main()
