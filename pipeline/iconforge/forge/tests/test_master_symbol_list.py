"""Smoke the full Icon Forge master symbol list.

Run:  python -m forge.tests.test_master_symbol_list
"""
from __future__ import annotations

from pathlib import Path

from .. import master_symbol_list


ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    result = master_symbol_list.build()
    summary = result["summary"]
    rows = result["rows"]

    assert summary["total_required_symbols"] == 824
    assert len(rows) == 824
    assert summary["visual_approved"] == 0
    assert summary["generated_manifest_entries"] == 139
    assert summary["generated_unique_assets"] == 139
    assert summary["art_state_counts"] == {
        "external_pd_candidate_needs_review": 34,
        "generate_owned": 420,
        "generated_owned_needs_visual_repair": 139,
        "license_blocked_reference_only": 203,
        "manual_exception": 28,
    }
    assert summary["chart1_evidence_counts"] == {
        "class_panel_reference": 20,
        "exact_symbol_crop": 139,
        "manual_exception": 28,
        "multi_symbol_reference": 175,
        "out_of_scope": 462,
    }
    assert summary["s101_coverage_counts"]["exact_symbol_match"] == 244
    assert summary["commons_pd_candidate_rows"] == 34
    assert summary["chart1_mappings_reference_rows"] == 372

    first = rows[0]
    required = {
        "asset",
        "helm_catalog_id",
        "s57_object_class",
        "art_state",
        "chart1_evidence_status",
        "s101_coverage",
        "next_action",
        "forbidden_sources",
    }
    assert required <= set(first)
    assert any(row["art_state"] == "generated_owned_needs_visual_repair" for row in rows)
    assert any(row["art_state"] == "generate_owned" for row in rows)
    assert any(row["s101_coverage"] == "exact_symbol_match" for row in rows)
    assert all("OpenCPN GPL rastersymbol sprites" in row["forbidden_sources"] for row in rows)

    assert (ROOT / "catalog" / "master_symbol_list.json").exists()
    assert (ROOT / "catalog" / "master_symbol_list.csv").exists()
    assert (ROOT / "catalog" / "master_symbol_list.md").exists()
    assert "Required catalog rows: 824" in (ROOT / "catalog" / "master_symbol_list.md").read_text()
    print("master symbol list: OK")


if __name__ == "__main__":
    main()
