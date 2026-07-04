"""Smoke the rendered craft/readability audit.

Run:  python3 -m forge.tests.test_standard_craft_audit
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_craft_audit


ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    result = standard_craft_audit.build()
    summary = result["summary"]

    assert result["status"] == "craft_audit_complete"
    assert summary["candidates_audited"] >= 700
    assert summary["craft_pass"] > summary["craft_review"]
    assert summary["craft_blocked"] >= 1

    by_asset = {row["asset"]: row for row in result["rows"]}
    assert by_asset["DANGER53"]["status"] == "craft_blocked"
    assert "placeholder_shape" in by_asset["DANGER53"]["issues"]
    assert by_asset["VEHTRF01"]["status"] == "craft_blocked"
    assert "placeholder_shape" in by_asset["VEHTRF01"]["issues"]
    assert by_asset["BOYBAR01"]["metrics"]["tiny_bbox_width"] >= 5
    assert by_asset["BOYBAR01"]["metrics"]["center_offset"] <= 0.18

    saved = json.loads((ROOT / "catalog" / "standard_craft_audit.json").read_text())
    assert saved["summary"]["candidates_audited"] == summary["candidates_audited"]
    assert (ROOT / "catalog" / "standard_craft_audit.csv").exists()
    assert (ROOT / "catalog" / "standard_craft_audit.md").exists()
    print("standard craft audit: OK")


if __name__ == "__main__":
    main()
