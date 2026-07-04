"""Smoke Standard Judge Batch 039 rerun.

Run:  python3 -m forge.tests.test_standard_judge_batch39_rerun
"""
from __future__ import annotations

import json
from pathlib import Path



ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "standard_judge_batch_039_rerun.json"


def main():
    result = json.loads(REPORT.read_text())
    assert result["batch_id"] == "standard_judge_batch_039_rerun"
    assert result["summary"]["selected"] == 16
    assert result["summary"]["pass"] == 14
    assert result["summary"]["fail"] == 2
    assert result["summary"]["final_approved"] == 0
    assert set(result["summary"]["failed_assets"]) == {
        "NMKINF38",
        "NMKINF53",
    }
    assert all(not verdict["final_approved"] for verdict in result["verdicts"])
    failed = {verdict["symbol_id"]: verdict for verdict in result["verdicts"] if not verdict["pass"]}
    assert "single diagonal white slash" in failed["NMKINF38"]["required_change"]
    assert "three vertical white bars" in failed["NMKINF53"]["required_change"]
    assert REPORT.exists()
    assert (ROOT / "catalog" / "standard_judge_batch_039_rerun.md").exists()
    print("standard judge batch 039 rerun: OK")


if __name__ == "__main__":
    main()
