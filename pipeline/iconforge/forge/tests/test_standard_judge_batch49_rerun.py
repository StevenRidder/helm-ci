"""Smoke Standard Judge Batch 049 rerun.

Run:  python3 -m forge.tests.test_standard_judge_batch49_rerun
"""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "standard_judge_batch_049_rerun.json"


def main():
    result = json.loads(REPORT.read_text())
    assert result["batch_id"] == "standard_judge_batch_049_rerun"
    assert result["summary"]["selected"] == 20
    assert result["summary"]["pass"] == 18
    assert result["summary"]["fail"] == 2
    assert result["summary"]["final_approved"] == 0
    assert set(result["summary"]["failed_assets"]) == {"TOPSHP47", "TOPSHP48"}
    assert all(not verdict["final_approved"] for verdict in result["verdicts"])
    failed = {verdict["symbol_id"]: verdict for verdict in result["verdicts"] if not verdict["pass"]}
    assert failed["TOPSHP47"]["required_change"].startswith("Redraw TOPSHP47 as a compact square")
    assert failed["TOPSHP48"]["required_change"].startswith("Redraw TOPSHP48 as a compact square")
    assert all(
        "catalog/owned_repair_batch49.json" in " ".join(verdict["source_refs_used"])
        for verdict in result["verdicts"]
    )
    assert (ROOT / "catalog" / "standard_judge_batch_049_rerun.md").exists()
    print("standard judge batch 049 rerun: OK")


if __name__ == "__main__":
    main()
