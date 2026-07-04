"""Smoke Standard Judge Batch 083/084 rerun.

Run:  python3 -m forge.tests.test_standard_judge_batch83_84_rerun
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_judge_batch83_84_rerun


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "standard_judge_batch_083_084_rerun.json"


def main():
    result = standard_judge_batch83_84_rerun.build()
    assert result["batch_id"] == "standard_judge_batch_083_084_rerun"
    assert result["summary"]["selected"] == 21
    assert result["summary"]["pass"] == 17
    assert result["summary"]["fail"] == 4
    assert result["summary"]["final_approved"] == 0
    assert set(result["summary"]["failed_assets"]) == {
        "BCNCON81",
        "TOWERS74|;TX(OBJNAM",
        "VEHTRF01",
        "boyspp50",
    }
    assert all(not verdict["final_approved"] for verdict in result["verdicts"])
    assert all(
        "catalog/owned_repair_batch83.json" in " ".join(verdict["source_refs_used"])
        or "catalog/owned_repair_batch84.json" in " ".join(verdict["source_refs_used"])
        for verdict in result["verdicts"]
    )
    assert all(
        any(str(ref).startswith("chart1_crop:") for ref in verdict["source_refs_used"])
        for verdict in result["verdicts"]
        if verdict["pass"]
    )
    assert REPORT.exists()
    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["pass"] == 17
    assert (ROOT / "catalog" / "standard_judge_batch_083_084_rerun.md").exists()
    print("standard judge batch 083/084 rerun: OK")


if __name__ == "__main__":
    main()
