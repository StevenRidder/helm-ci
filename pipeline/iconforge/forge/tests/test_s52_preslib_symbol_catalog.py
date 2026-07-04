"""Smoke the S-52 PresLib symbol catalogue ingest.

Run:  python3 -m forge.tests.test_s52_preslib_symbol_catalog
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import s52_preslib_symbol_catalog


ROOT = Path(__file__).resolve().parent.parent.parent
CATALOG = ROOT / "catalog" / "s52_preslib_symbol_catalog.json"
JOIN = ROOT / "catalog" / "s52_preslib_symbol_join.json"


def main():
    data = json.loads(CATALOG.read_text())
    entries = data["entries"]
    by_name = {entry["symbol_name"]: entry for entry in entries}
    assert data["status"] == "s52_preslib_symbol_catalog_written"
    assert data["source"]["status"] == "reference_only"
    assert "canonical_asset_source" in data["source"]["forbidden_use"]
    assert s52_preslib_symbol_catalog.validate_entries(entries) == []

    summary = data["summary"]
    assert summary["entries"] == 549
    assert summary["prefix_counts"] == {"AP": 25, "LC": 53, "SY": 471}
    assert summary["entries_with_s57_refs"] == 513
    assert summary["entries_with_int1_refs"] == 485
    assert summary["warning_counts"] == {
        "missing_pivot_point_column": 1,
        "missing_symbol_colours": 22,
        "missing_symbol_explanation": 21,
        "missing_width_of_bounding_box": 1,
        "reference_number_missing": 1,
    }

    bcncar01 = by_name["SY(BCNCAR01)"]
    assert bcncar01["reference_number"] == 16
    assert bcncar01["pdf_page"] == 16
    assert bcncar01["symbol_id"] == "BCNCAR01"
    assert bcncar01["symbol_colours"] == ["OUTLW", "CHYLW"]
    assert bcncar01["pivot"] == {"column": 2.0, "row": 3.05}
    assert bcncar01["bounding_box"] == {"width": 4.02, "height": 6.12}
    assert "BCNCAR" in bcncar01["references"]["s57_tokens"]

    boybar01 = by_name["SY(BOYBAR01)"]
    assert boybar01["reference_number"] == 35
    assert boybar01["symbol_explanation"] == "barrel buoy, paper-chart"
    assert "CHBLK" in boybar01["symbol_colours"]

    achare51 = by_name["LC(ACHARE51)"]
    assert achare51["section"] == "complex_linestyles"
    assert achare51["bounding_box"]["width"] == 30.3

    airare02 = by_name["AP(AIRARE02)"]
    assert airare02["section"] == "area_patterns"
    assert airare02["pattern"]["type"] == "Staggered"
    assert airare02["pattern"]["minimum_distance"] == 20.0

    essare01 = by_name["SY(ESSARE01)"]
    assert essare01["reference_number"] is None
    assert essare01["parse_warnings"] == ["reference_number_missing"]

    join = json.loads(JOIN.read_text())
    assert join["status"] == "s52_preslib_symbol_join_written"
    assert join["summary"] == {
        "catalog_entries": 549,
        "matched_asset_links": 302,
        "matched_entries": 302,
        "unmatched_entries": 247,
    }
    assert (ROOT / "catalog" / "s52_preslib_symbol_catalog.csv").exists()
    assert (ROOT / "catalog" / "s52_preslib_symbol_catalog.md").exists()
    assert (ROOT / "catalog" / "s52_preslib_symbol_join.csv").exists()
    assert (ROOT / "catalog" / "s52_preslib_symbol_join.md").exists()
    print("s52 preslib symbol catalog: OK")


if __name__ == "__main__":
    main()
