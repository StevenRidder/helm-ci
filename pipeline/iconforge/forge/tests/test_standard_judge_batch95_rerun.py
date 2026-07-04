"""Smoke Standard Judge Batch 095 rerun.

Run:  python3 -m forge.tests.test_standard_judge_batch95_rerun
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_judge_batch95_rerun


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "standard_judge_batch_095_rerun.json"


def main():
    result = standard_judge_batch95_rerun.build()
    assert result["batch_id"] == "standard_judge_batch_095_rerun"
    assert result["summary"]["selected"] == 4
    assert result["summary"]["pass"] == 4
    assert result["summary"]["fail"] == 0
    assert result["summary"]["final_approved"] == 0
    assert set(result["summary"]["passed_assets"]) == {
        "LIGHTS05",
        "OBSTRN04",
        "TOWERS74|;TX(OBJNAM",
        "WRECKS02",
    }
    assert all(verdict["pass"] for verdict in result["verdicts"])
    assert all(not verdict["final_approved"] for verdict in result["verdicts"])
    assert REPORT.exists()
    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["pass"] == 4
    assert (ROOT / "catalog" / "standard_judge_batch_095_rerun.md").exists()
    print("standard judge batch 095 rerun: OK")


if __name__ == "__main__":
    main()
