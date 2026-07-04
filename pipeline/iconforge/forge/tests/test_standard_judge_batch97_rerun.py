"""Smoke Standard Judge Batch 097 rerun.

Run:  python3 -m forge.tests.test_standard_judge_batch97_rerun
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_judge_batch97_rerun


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "standard_judge_batch_097_rerun.json"


def main():
    result = standard_judge_batch97_rerun.build()
    assert result["batch_id"] == "standard_judge_batch_097_rerun"
    assert result["summary"]["selected"] == 2
    assert result["summary"]["pass"] == 2
    assert result["summary"]["fail"] == 0
    assert result["summary"]["final_approved"] == 0
    assert set(result["summary"]["passed_assets"]) == {"BCNCON81", "boyspp50"}
    assert all(verdict["pass"] for verdict in result["verdicts"])
    assert all(not verdict["final_approved"] for verdict in result["verdicts"])
    assert all("symbol_specs:catalog/symbol_specs_batch96.json" in verdict["source_refs_used"] for verdict in result["verdicts"])
    assert REPORT.exists()
    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["pass"] == 2
    assert (ROOT / "catalog" / "standard_judge_batch_097_rerun.md").exists()
    print("standard judge batch 097 rerun: OK")


if __name__ == "__main__":
    main()
