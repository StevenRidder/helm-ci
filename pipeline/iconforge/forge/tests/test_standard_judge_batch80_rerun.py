"""Smoke Standard Judge Batch 080 rerun.

Run:  python3 -m forge.tests.test_standard_judge_batch80_rerun
"""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "standard_judge_batch_080_rerun.json"


def main():
    result = json.loads(REPORT.read_text())
    assert result["batch_id"] == "standard_judge_batch_080_rerun"
    assert result["summary"]["selected"] == 7
    assert result["summary"]["pass"] == 5
    assert result["summary"]["fail"] == 2
    assert result["summary"]["final_approved"] == 0
    assert set(result["summary"]["failed_assets"]) == {"VECWTR01", "VECWTR21"}
    failed = {verdict["symbol_id"]: verdict for verdict in result["verdicts"] if not verdict["pass"]}
    assert "single-chevron" in failed["VECWTR01"]["required_change"]
    assert "double-chevron" in failed["VECWTR21"]["observed"]
    assert all(not verdict["final_approved"] for verdict in result["verdicts"])
    assert REPORT.exists()
    assert (ROOT / "catalog" / "standard_judge_batch_080_rerun.md").exists()
    print("standard judge batch 080 rerun: OK")


if __name__ == "__main__":
    main()
