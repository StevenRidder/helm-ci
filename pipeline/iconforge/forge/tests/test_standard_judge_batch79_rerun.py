"""Smoke Standard Judge Batch 079 rerun.

Run:  python3 -m forge.tests.test_standard_judge_batch79_rerun
"""
from __future__ import annotations

import json
from pathlib import Path



ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "standard_judge_batch_079_rerun.json"


def main():
    result = json.loads(REPORT.read_text())
    assert result["batch_id"] == "standard_judge_batch_079_rerun"
    assert result["summary"]["selected"] == 15
    assert result["summary"]["pass"] == 14
    assert result["summary"]["fail"] == 1
    assert result["summary"]["final_approved"] == 0
    assert result["summary"]["failed_assets"] == ["WATTUR02"]
    assert all(not verdict["final_approved"] for verdict in result["verdicts"])
    failed = next(verdict for verdict in result["verdicts"] if not verdict["pass"])
    assert "three-wave" in failed["required_change"]
    assert "wrong_wave_count" in failed["safety_reason_codes"]
    assert REPORT.exists()
    assert (ROOT / "catalog" / "standard_judge_batch_079_rerun.md").exists()
    print("standard judge batch 079 rerun: OK")


if __name__ == "__main__":
    main()
