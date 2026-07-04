"""Smoke the third source-priority Helm-style repair batch.

Run:  python -m forge.tests.test_source_priority_repair_batch3
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import source_priority_repair_batch3


ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    report = source_priority_repair_batch3.build(render_outputs=False)

    assert report["status"] == "candidate_batch_pending_visual_review"
    assert report["batch_offset"] == 270
    assert report["batch_size"] == 150
    assert report["summary"] == {
        "generated_fallback_for_s101_reference": 82,
        "generated_owned_candidates": 150,
        "generated_placeholder_no_fallback": 1,
        "license_pending_reference_candidates": 0,
        "redraw_s101_reference_into_helm_style": 83,
        "repair_existing_helm_style_svg": 67,
        "visual_parity": "pending_visual_model_and_human_review",
    }
    assert all(row["qa"]["final_approved"] is False for row in report["symbols"])
    assert report["symbols"][0]["asset"] == "TOPSHP98"
    assert report["symbols"][-1]["asset"] == "RECTRC55"

    redraw_rows = [row for row in report["symbols"] if row["queue_action"] == "redraw_s101_reference_into_helm_style"]
    assert len(redraw_rows) == 83
    for row in redraw_rows:
        after = (ROOT / row["after_svg"]).read_text()
        before = (ROOT / row["before_svg"]).read_text()
        assert after != before
        assert "license-pending-s101-reference-art" not in after
        assert row["provenance"]["origin"] == "generated-owned-artwork"

    by_asset = {row["asset"]: row for row in report["symbols"]}
    assert by_asset["BCNDEF13"]["candidate_strategy"] == "generated_fallback_for_s101_reference"
    assert by_asset["BCNDEF13"]["candidate_source"] == "assets/svg/multisource_draft/BCNDEF13.svg"
    assert by_asset["MARCUL02"]["candidate_strategy"] == "generated_placeholder_no_fallback"
    assert by_asset["MARCUL02"]["candidate_source"] is None
    assert "marine farm pattern placeholder" in (ROOT / by_asset["MARCUL02"]["after_svg"]).read_text()
    facility_shapes = {
        "SMCFAC02": "marina",
        "HRBFAC12": "ship_yard_letter",
        "HRBFAC13": "harbour_master_letter",
        "HRBFAC14": "pilot_station_letter",
    }
    for asset, shape in facility_shapes.items():
        svg = (ROOT / by_asset[asset]["after_svg"]).read_text()
        assert f'data-shape="{shape}"' in svg
        assert 'data-shape="harbor_service"' not in svg
    hrbfac12 = (ROOT / by_asset["HRBFAC12"]["after_svg"]).read_text()
    hrbfac13 = (ROOT / by_asset["HRBFAC13"]["after_svg"]).read_text()
    hrbfac14 = (ROOT / by_asset["HRBFAC14"]["after_svg"]).read_text()
    assert 'fill="var(--magenta)">SY<' in hrbfac12
    assert 'fill="var(--magenta)">HM<' in hrbfac13
    assert 'fill="var(--magenta)">P<' in hrbfac14

    saved = json.loads((ROOT / "catalog" / "owned_repair_batch3.json").read_text())
    assert saved["batch_offset"] == 270
    assert saved["batch_size"] == 150
    print("source-priority repair batch3: OK")


if __name__ == "__main__":
    main()
