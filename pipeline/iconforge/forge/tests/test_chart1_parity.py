"""Smoke the Chart No.1 visual parity gate.

Run:  python -m forge.tests.test_chart1_parity
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from .. import chart1_parity


ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "out" / "chart1_parity"


def main():
    rc = chart1_parity.main([])
    assert rc == 0, "Chart No.1 parity gate did not emit reports"

    pilot = json.loads((ROOT / "pilots" / "chart1_visual_parity.json").read_text())
    report = json.loads((OUT / "report.json").read_text())
    hard_pile = json.loads((OUT / "hard_pile.json").read_text())
    provenance = json.loads((OUT / "reference_provenance.json").read_text())
    sample = json.loads((ROOT / "samples" / "chart1_parity_sample50.json").read_text())

    assert pilot["source_catalog_assets"] == 824
    assert len(pilot["entries"]) == 824
    assert pilot["gate_assets"] == 362
    assert pilot["reference"]["pdf_sha256"] == chart1_parity.CHART1_SHA256
    assert any("rastersymbols" in s for s in pilot["reference"]["clean_ip_boundary"])

    assert report["status"] == "review_required"
    assert report["summary"]["full_catalog_assets"] == 824
    assert report["summary"]["crosswalk_rows"] == 824
    assert report["summary"]["gate_assets"] == 362
    assert report["summary"]["hard_pile_entries"] == len(hard_pile)
    assert report["summary"]["verdict_counts"]["deferred"] == 462
    assert report["summary"]["verdict_counts"]["fail"] > 0
    assert report["summary"]["sample_size"] == 50
    assert report["summary"]["evidence_counts"] == {
        "class_panel_reference": 20,
        "exact_symbol_crop": 139,
        "manual_exception": 28,
        "multi_symbol_reference": 175,
        "out_of_scope": 462,
    }
    assert report["summary"]["final_approved"] == 0
    assert report["summary"]["hard_pile_entries"] == 362
    assert report["summary"]["final_approved"] + report["summary"]["hard_pile_entries"] == pilot["gate_assets"]

    for row in report["rows"]:
        if row["final_approval"]:
            assert row["reference_evidence_status"] == "exact_symbol_crop"
            assert row["verdict"] == "pass"
        if row["reference_evidence_status"] in {"class_panel_reference", "multi_symbol_reference"}:
            assert not row["final_approval"]
            assert "no_exact_symbol_crop_final_pass_forbidden" in row["reason_codes"]

    bad_final_evidence = [
        row for row in report["rows"]
        if row["final_approval"] and row["reference_evidence_status"] != "exact_symbol_crop"
    ]
    assert not bad_final_evidence, "only exact_symbol_crop rows may final-approve"

    exact_rows = [row for row in report["rows"] if row["reference_evidence_status"] == "exact_symbol_crop"]
    assert exact_rows, "expected exact-symbol rows"
    assert all(row["reference_comparison"] for row in exact_rows)
    assert all(row["reference_crop"] for row in exact_rows)

    assert provenance["pdf_sha256"] == chart1_parity.CHART1_SHA256
    assert len(provenance["rendered_pages"]) == len(chart1_parity.CHART1_PAGES)
    assert set(provenance["crops"]) >= {
        "cardinal_marks",
        "lateral_regions",
        "isolated_safe_special",
        "shape_can_buoy",
        "shape_conical_buoy",
        "beacon_general",
        "topmark_vertical_rectangle",
        "topmark_cube_point_up",
    }
    for page in provenance["rendered_pages"]:
        image = ROOT / page["image"]
        assert image.exists(), f"missing rendered Chart No.1 page {image}"
        assert Image.open(image).size == (page["width"], page["height"])
    for crop in provenance["crops"].values():
        image = ROOT / crop["image"]
        assert image.exists(), f"missing rendered Chart No.1 crop {image}"
        assert Image.open(image).size == (crop["width"], crop["height"])
        if crop["status"] == "exact_symbol_crop":
            assert crop["width"] <= 90 and crop["height"] <= 90, f"exact crop is too broad: {crop['id']}"

    pilot_entries = {row["asset"]: row for row in pilot["entries"]}
    assert pilot_entries["BOYLAT54"]["reference_crop_status"] == "class_panel_reference"
    assert not pilot_entries["BOYLAT54"]["final_pass_allowed"]
    assert pilot_entries["BOYCAN62"]["reference_crop_status"] == "multi_symbol_reference"
    assert not pilot_entries["BOYCAN62"]["final_pass_allowed"]

    assert len(sample["rows"]) == 50
    assert {row["verdict"] for row in sample["rows"]} & {"fail", "manual", "partial"}
    sheet = ROOT / "samples" / "chart1_parity_sample50.png"
    assert sheet.exists(), "missing committed sample contact sheet"
    assert Image.open(sheet).size[0] >= 1200
    crop_review = json.loads((ROOT / "samples" / "chart1_crop_review.json").read_text())
    assert crop_review["crop_count"] == len(provenance["crops"])
    assert any(entry["mapped_assets"] > 0 for entry in crop_review["entries"])
    crop_sheet = ROOT / "samples" / "chart1_crop_review.png"
    assert crop_sheet.exists(), "missing committed crop review sheet"
    assert Image.open(crop_sheet).size[0] >= 1200

    topmarks = [row for row in report["rows"] if row["asset"].startswith("TOP")]
    assert topmarks, "expected topmark assets in parity report"
    assert any("topmark_not_standalone_chart1_glyph" in row["reason_codes"] for row in topmarks)

    print("chart1 parity gate: OK")


if __name__ == "__main__":
    main()
