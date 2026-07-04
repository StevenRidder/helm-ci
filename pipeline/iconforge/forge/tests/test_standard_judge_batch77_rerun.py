"""Smoke Standard Judge Batch 077 rerun.

Run:  python3 -m forge.tests.test_standard_judge_batch77_rerun
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_judge_batch77_rerun


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "standard_judge_batch_077_rerun.json"


def main():
    result = standard_judge_batch77_rerun.build()
    assert result["batch_id"] == "standard_judge_batch_077_rerun"
    assert result["summary"]["selected"] == 12
    assert result["summary"]["pass"] == 12
    assert result["summary"]["fail"] == 0
    assert result["summary"]["final_approved"] == 0
    assert result["summary"]["failed_assets"] == []
    assert set(result["summary"]["passed_assets"]) == {
        "EVENTS02",
        "HECMTR01",
        "HECMTR02",
        "HGWTMK01",
        "ISODGR51",
        "NOTMRK03",
        "OSPONE02",
        "OSPSIX02",
        "PLNPOS02",
        "POSITN02",
        "PRICKE03",
        "PRICKE04",
    }
    assert all(not verdict["final_approved"] for verdict in result["verdicts"])
    withies = {verdict["symbol_id"]: verdict for verdict in result["verdicts"] if verdict["symbol_id"].startswith("PRICKE")}
    assert "port-hand withy" in withies["PRICKE03"]["judge_comments"]
    assert "starboard-hand withy" in withies["PRICKE04"]["judge_comments"]
    assert REPORT.exists()
    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["pass"] == 12
    assert (ROOT / "catalog" / "standard_judge_batch_077_rerun.md").exists()
    print("standard judge batch 077 rerun: OK")


if __name__ == "__main__":
    main()
