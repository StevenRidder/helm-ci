"""Smoke Standard Judge Batch 086 rerun.

Run:  python3 -m forge.tests.test_standard_judge_batch86_rerun
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_judge_batch86_rerun


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "standard_judge_batch_086_rerun.json"


def main():
    result = standard_judge_batch86_rerun.build()
    assert result["batch_id"] == "standard_judge_batch_086_rerun"
    assert result["summary"]["selected"] == 7
    assert result["summary"]["pass"] == 7
    assert result["summary"]["fail"] == 0
    assert result["summary"]["final_approved"] == 0
    assert result["summary"]["failed_assets"] == []
    assert set(result["summary"]["passed_assets"]) == {
        "NMKINF38",
        "NMKINF53",
        "SCALEB10",
        "SCALEB11",
        "TOPMAR90",
        "TOPMAR93",
        "WATTUR02",
    }
    assert all(not verdict["final_approved"] for verdict in result["verdicts"])
    assert REPORT.exists()
    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["pass"] == 7
    assert (ROOT / "catalog" / "standard_judge_batch_086_rerun.md").exists()
    print("standard judge batch 086 rerun: OK")


if __name__ == "__main__":
    main()
