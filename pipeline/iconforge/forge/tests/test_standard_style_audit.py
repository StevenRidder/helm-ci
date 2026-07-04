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
    assert result["contact_sheets"]["sample_count"] >= 25
    assert (ROOT / result["contact_sheets"]["style_contract_satellite_svg"]).exists()
    assert result["summary"]["issue_counts"].get("bad_font_family", 0) == 0

    by_asset = {row["asset"]: row for row in result["rows"]}
    assert by_asset["DANGER53"]["status"] == "style_blocked"
    assert "diamond_placeholder" in by_asset["DANGER53"]["issues"]
    assert by_asset["DGPS01DRFSTA01"]["status"] == "style_blocked"
    assert "generic_symbol" in by_asset["DGPS01DRFSTA01"]["issues"]
    assert by_asset["NEWOBJ01"]["gate_status"] == "failed"

    saved = json.loads((ROOT / "catalog" / "standard_style_audit.json").read_text())
    assert saved["summary"]["candidates_audited"] == summary["candidates_audited"]
    assert (ROOT / "catalog" / "standard_style_audit.csv").exists()
    assert (ROOT / "catalog" / "standard_style_audit.md").exists()
    _smoke_bad_fixtures()
    print("standard style audit: OK")


def _smoke_bad_fixtures() -> None:
    thick = standard_style_audit.audit_svg_text(
        "BOYCANZZ",
        '<svg viewBox="0 0 64 64" data-origin="generated-owned-artwork" '
        'data-style-contract="helm-openbridge-navigation-v1"><path d="M20 10 H44 V54 H20 Z" '
        'fill="var(--red)" stroke="var(--black)" stroke-width="12" '
        'stroke-linecap="round" stroke-linejoin="round"/></svg>',
    )
    assert thick["status"] == "style_review"
    assert "oversized_stroke" in thick["issues"]

    off_palette = standard_style_audit.audit_svg_text(
        "TESTHEX",
        '<svg viewBox="0 0 64 64" data-origin="generated-owned-artwork" '
        'data-style-contract="helm-openbridge-navigation-v1"><circle cx="32" cy="32" r="18" '
        'fill="#ff00ff" stroke="var(--black)" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round"/></svg>',
    )
    assert off_palette["status"] == "style_review"
    assert "literal_fill_colour" in off_palette["issues"]

    missing_edge = standard_style_audit.audit_svg_text(
        "BOYCANYY",
        '<svg viewBox="0 0 64 64" data-origin="generated-owned-artwork" '
        'data-style-contract="helm-openbridge-navigation-v1"><rect x="20" y="10" width="24" height="44" '
        'fill="var(--red)"/></svg>',
    )
    assert missing_edge["status"] == "style_blocked"
    assert "missing_black_edge" in missing_edge["issues"]

    blank = standard_style_audit.audit_svg_text(
        "TESTBLANK",
        '<svg viewBox="0 0 64 64" data-origin="generated-owned-artwork" '
        'data-style-contract="helm-openbridge-navigation-v1"><title>blank</title></svg>',
    )
    assert blank["status"] == "style_blocked"
    assert "blank_svg" in blank["issues"]

    bad_viewbox = standard_style_audit.audit_svg_text(
        "TESTVIEW",
        '<svg data-origin="generated-owned-artwork" data-style-contract="helm-openbridge-navigation-v1">'
        '<circle cx="32" cy="32" r="12" fill="var(--green)"/></svg>',
    )
    assert bad_viewbox["status"] == "style_blocked"
    assert "missing_viewbox" in bad_viewbox["issues"]

    off_canvas = standard_style_audit.audit_svg_text(
        "TESTOFF",
        '<svg viewBox="0 0 64 64" data-origin="generated-owned-artwork" '
        'data-style-contract="helm-openbridge-navigation-v1"><circle cx="300" cy="32" r="12" '
        'fill="var(--green)" stroke="var(--black)" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round"/></svg>',
    )
    assert off_canvas["status"] == "style_blocked"
    assert "off_canvas_geometry" in off_canvas["issues"]


if __name__ == "__main__":
    main()
