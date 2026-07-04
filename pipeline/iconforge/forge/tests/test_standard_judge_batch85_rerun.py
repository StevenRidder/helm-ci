"""Smoke Standard Judge Batch 085 rerun.

Run:  python3 -m forge.tests.test_standard_judge_batch85_rerun
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_judge_batch85_rerun


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "standard_judge_batch_085_rerun.json"


def main():
    result = standard_judge_batch85_rerun.build()
    assert result["batch_id"] == "standard_judge_batch_085_rerun"
    assert result["summary"]["selected"] == 2
    assert result["summary"]["pass"] == 2
    assert result["summary"]["fail"] == 0
    assert result["summary"]["final_approved"] == 0
    assert set(result["summary"]["passed_assets"]) == {"VECWTR01", "VECWTR21"}
    assert all(not verdict["final_approved"] for verdict in result["verdicts"])
    assert REPORT.exists()
    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["pass"] == 2
    assert (ROOT / "catalog" / "standard_judge_batch_085_rerun.md").exists()
    print("standard judge batch 085 rerun: OK")


if __name__ == "__main__":
    main()
