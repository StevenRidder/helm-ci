"""Smoke Standard Judge Batch 076/082 rerun.

Run:  python3 -m forge.tests.test_standard_judge_batch76_82_rerun
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_judge_batch76_82_rerun


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "standard_judge_batch_076_082_rerun.json"


def main():
    result = standard_judge_batch76_82_rerun.build()
    assert result["batch_id"] == "standard_judge_batch_076_082_rerun"
    assert result["summary"]["selected"] == 9
    assert result["summary"]["pass"] == 9
    assert result["summary"]["fail"] == 0
    assert result["summary"]["final_approved"] == 0
    assert set(result["summary"]["passed_assets"]) == {
        "BOYBAR01",
        "BOYBAR60",
        "BOYBAR61",
        "BOYBAR62",
        "BUNSTA02",
        "SSENTR01",
        "SSLOCK01",
        "SSWARS01",
        "ZZZZZZ01",
    }
    assert all(verdict["pass"] for verdict in result["verdicts"])
    assert all(not verdict["final_approved"] for verdict in result["verdicts"])
    assert all(
        "source_variant_opencpn:" in " ".join(verdict["source_refs_used"])
        for verdict in result["verdicts"]
    )
    assert REPORT.exists()
    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["pass"] == 9
    assert (ROOT / "catalog" / "standard_judge_batch_076_082_rerun.md").exists()
    print("standard judge batch 076/082 rerun: OK")


if __name__ == "__main__":
    main()
