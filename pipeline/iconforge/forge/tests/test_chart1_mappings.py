"""Smoke the Chart 1 Mappings Q-section table.

Run:  python -m forge.tests.test_chart1_mappings
"""
from __future__ import annotations

from .. import chart1_mappings


def main():
    mapping = chart1_mappings.load_mapping()
    errors = chart1_mappings.validate_mapping(mapping)
    assert not errors, errors

    assert mapping["source"]["id"] == "chart1_mappings_pdf_q"
    assert mapping["source"]["status"] == "reference_only"
    assert mapping["source"]["license_status"] == "permission_required_before_artwork_use"
    assert mapping["source"]["local_pdf"].endswith("Chart 1 Mappings.pdf")
    assert mapping["source"]["pdf_sha256"] == "6768d3935f312310686d94dc78683fa29f1e5c00901cd9cf0978481cfd54af64"
    assert "crop_extract_svg" in mapping["source"]["forbidden_use"]
    assert "direct_artwork_derivation" in mapping["source"]["forbidden_use"]
    assert "canonical_asset_source" in mapping["source"]["forbidden_use"]
    assert "s57_object_crosswalk" in mapping["source"]["allowed_use"]

    rows = {row["int1"]: row for row in mapping["rows"]}
    assert len(rows) == 62
    assert rows["Q20"]["name"] == "Conical buoy, nun buoy, ogival buoy"
    assert rows["Q20"]["s57"] == ["BOYXXX.BOYSHP=1"]
    assert rows["Q21"]["name"] == "Can buoy, cylindrical buoy"
    assert rows["Q50"]["s57"] == ["BOYSPP.CATSPM=1.BOYSHP=3", "COLOUR=6", "TOPMAR.TOPSH=7"]
    assert rows["Q80"]["s57"] == ["BCNXXX.BCNSHP.COLOUR"]
    assert rows["Q126"]["name"] == "Notice board"

    report = chart1_mappings.build_reference_crops()
    assert report["status"] == "pass"
    assert report["rows_mapped"] == 62
    assert report["row_crops_written"] == 62
    assert report["missing_page_renders"] == []
    assert report["reference_boundary"]["forbidden_use"] == mapping["source"]["forbidden_use"]
    assert report["entries"][0]["status"] == "reference_only_not_canonical_artwork"
    assert report["entries"][0]["row_crop"].endswith("/Q1.png")
    assert report["entries"][0]["icon_reference_crop"].endswith("/icon_refs/Q1.png")
    print("chart1 mappings q table: OK")


if __name__ == "__main__":
    main()
