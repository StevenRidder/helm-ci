"""Smoke Standard Judge Batch 088-091 initial.

Run:  python3 -m forge.tests.test_standard_judge_batch88_91_initial
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_judge_batch88_91_initial


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "standard_judge_batch_088_091_initial.json"


def main():
    result = standard_judge_batch88_91_initial.build()
    assert result["batch_id"] == "standard_judge_batch_088_091_initial"
    assert result["summary"]["selected"] == 58
    assert result["summary"]["pass"] == 0
    assert result["summary"]["fail"] == 58
    assert result["summary"]["final_approved"] == 0
    assert set(result["summary"]["source_batches"]) == {
        "catalog/owned_repair_batch88.json",
        "catalog/owned_repair_batch89.json",
        "catalog/owned_repair_batch90.json",
        "catalog/owned_repair_batch91.json",
    }
    failed = set(result["summary"]["failed_assets"])
    assert {"CBLSUB06", "LIGHTS05", "RCRTCL14", "WRECKS02"} <= failed
    assert "ARCSLN01" not in failed
    assert all(not verdict["pass"] for verdict in result["verdicts"])
    assert all(not verdict["final_approved"] for verdict in result["verdicts"])
    assert all("reference_witness_not_followed" in verdict["safety_reason_codes"] for verdict in result["verdicts"])
    assert REPORT.exists()
    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["fail"] == 58
    assert (ROOT / "catalog" / "standard_judge_batch_088_091_initial.md").exists()
    print("standard judge batch 088-091 initial: OK")


if __name__ == "__main__":
    main()
