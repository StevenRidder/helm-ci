"""Smoke the source-backed official symbol table.

Run:  python -m forge.tests.test_official_symbol_table
"""
from __future__ import annotations

from pathlib import Path

from .. import official_symbol_table


ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    result = official_symbol_table.build()
    summary = result["summary"]
    rows = result["rows"]

    assert summary["official_rows"] == 62
    assert summary["rows_with_reference_crops"] == 62
    assert summary["rows_with_attribute_matches"] == 48
    assert summary["attribute_helm_asset_links"] == 1617
    assert summary["precise_helm_asset_links"] == summary["attribute_helm_asset_links"]
    assert summary["rows_with_broad_candidates_only"] == 2
    assert summary["broad_candidate_links"] == 678
    assert summary["s101_exact_asset_links"] == 71
    assert summary["rows_with_commons_candidates"] > 0
    assert summary["evidence_status_counts"]["official_row_attribute_mapped"] == 48
    assert summary["evidence_status_counts"]["official_row_broad_candidate_only"] == 2
    assert summary["evidence_status_counts"]["official_row_unmatched_to_helm_asset"] > 0

    q20 = next(row for row in rows if row["int1"] == "Q20")
    assert q20["official_name"] == "Conical buoy, nun buoy, ogival buoy"
    assert q20["source_boundary"]["source_id"] == "chart1_mappings_pdf_q"
    assert q20["symbol_reference"]["icon_reference_crop"].endswith("Q20.png")
    assert q20["precise_s57_mappings"] == [{
        "source_ref": "BOYXXX.BOYSHP=1",
        "object": "BOYXXX",
        "attributes": [{
            "attribute": "BOYSHP",
            "accepted_values": ["1"],
            "match": "value_any",
        }],
        "precision": "object_and_attributes",
    }]
    assert q20["precise_helm_asset_matches"] == q20["attribute_matched_helm_assets"]
    assert q20["attribute_matched_helm_assets"]
    assert all(
        any(condition.startswith("BOYSHP1") for condition in asset["s57_conditions"])
        for asset in q20["attribute_matched_helm_assets"]
    )

    q7 = next(row for row in rows if row["int1"] == "Q7")
    assert q7["evidence_status"] == "official_row_broad_candidate_only"
    assert q7["broad_candidate_helm_assets"]
    assert not q7["attribute_matched_helm_assets"]

    q80 = next(row for row in rows if row["int1"] == "Q80")
    assert q80["section"] == "Beacons"
    assert "Beacon in general" in q80["official_name"]
    assert any(asset["asset"].startswith("BCN") for asset in q80["attribute_matched_helm_assets"])

    for row in rows:
        assert row["int1"]
        assert row["official_name"]
        assert row["source_page"]
        assert row["symbol_reference"]["status"] == "reference_only_not_canonical_artwork"
        assert "canonical_asset_source" in row["source_boundary"]["forbidden_use"]

    assert (ROOT / "catalog" / "official_symbol_table.yaml").exists()
    assert (ROOT / "catalog" / "official_symbol_table.json").exists()
    assert (ROOT / "catalog" / "official_symbol_table.csv").exists()
    assert (ROOT / "catalog" / "official_symbol_table.md").exists()
    assert "source_id: chart1_mappings_pdf_q" in (ROOT / "catalog" / "official_symbol_table.yaml").read_text()
    print("official symbol table: OK")


if __name__ == "__main__":
    main()
