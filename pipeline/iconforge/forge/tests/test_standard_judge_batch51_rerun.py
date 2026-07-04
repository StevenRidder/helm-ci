"""Smoke Standard Judge Batch 051 rerun.

Run:  python3 -m forge.tests.test_standard_judge_batch51_rerun
"""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "standard_judge_batch_051_rerun.json"


def main():
    result = json.loads(REPORT.read_text())
    assert result["batch_id"] == "standard_judge_batch_051_rerun"
    assert result["summary"]["selected"] == 20
    assert result["summary"]["pass"] == 14
    assert result["summary"]["fail"] == 6
    assert result["summary"]["final_approved"] == 0
    assert set(result["summary"]["failed_assets"]) == {
        "TOPSHPI3",
        "TOPSHPJ1",
        "TOPSHPJ3",
        "TOPSHPP2",
        "TOPSHPR1",
        "TOPSHPS1",
    }
    assert all(not verdict["final_approved"] for verdict in result["verdicts"])
    failed = {verdict["symbol_id"]: verdict for verdict in result["verdicts"] if not verdict["pass"]}
    assert "plain black X" in failed["TOPSHPI3"]["observed"]
    assert "simple yellow slash" in failed["TOPSHPJ1"]["observed"]
    assert "target/ring" in failed["TOPSHPS1"]["observed"]
    assert REPORT.exists()
    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["pass"] == 14
    assert (ROOT / "catalog" / "standard_judge_batch_051_rerun.md").exists()
    print("standard judge batch 051 rerun: OK")


if __name__ == "__main__":
    main()
