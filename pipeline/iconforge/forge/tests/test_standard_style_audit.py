"""Smoke the Helm/OpenBridge style audit.

Run:  python3 -m forge.tests.test_standard_style_audit
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_style_audit
from ..style_contract import OPENBRIDGE_STYLE_ID


ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    result = standard_style_audit.build()
    summary = result["summary"]

    assert result["status"] == "style_audit_complete"
    assert result["style_contract"]["id"] == OPENBRIDGE_STYLE_ID
    assert summary["source_table_rows"] == 824
    assert summary["candidates_audited"] >= 700
    assert summary["style_pass"] > summary["style_review"]
    assert summary["style_blocked"] >= 1
    assert result["summary"]["issue_counts"].get("bad_font_family", 0) == 0

    by_asset = {row["asset"]: row for row in result["rows"]}
    assert by_asset["DANGER53"]["status"] == "style_blocked"
    assert "diamond_placeholder" in by_asset["DANGER53"]["issues"]
    assert by_asset["VEHTRF01"]["status"] == "style_blocked"
    assert "generic_symbol" in by_asset["VEHTRF01"]["issues"]

    saved = json.loads((ROOT / "catalog" / "standard_style_audit.json").read_text())
    assert saved["summary"]["candidates_audited"] == summary["candidates_audited"]
    assert (ROOT / "catalog" / "standard_style_audit.csv").exists()
    assert (ROOT / "catalog" / "standard_style_audit.md").exists()
    print("standard style audit: OK")


if __name__ == "__main__":
    main()
