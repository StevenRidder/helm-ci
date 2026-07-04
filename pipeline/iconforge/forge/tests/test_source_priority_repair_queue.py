"""Smoke the source-priority Helm-style redraw/repair queue.

Run:  python -m forge.tests.test_source_priority_repair_queue
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import source_priority_repair_queue


ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    result = source_priority_repair_queue.build(limit=120, render_candidate=False)
    selection = result["selection"]

    assert result["status"] == "ready_batch"
    assert selection["source_priority_rows_available"] == 747
    assert selection["queueable_jobs"] == 747
    assert selection["selected_jobs"] == 120
    assert selection["offset"] == 0
    assert selection["skipped_jobs"] == 0
    assert selection["include_s101_redraw"] is True
    assert selection["missing_svg_rows"] == 0
    assert selection["action_counts"]["repair_existing_helm_style_svg"] > 0
    assert selection["action_counts"]["redraw_s101_reference_into_helm_style"] > 0
    assert selection["source_basis_counts"]["helm_multisource_draft_svg"] > 0
    assert selection["source_basis_counts"]["s101_exact_svg"] > 0

    first = result["jobs"][0]
    assert first["queue_action"] in {
        "repair_existing_helm_style_svg",
        "redraw_s101_reference_into_helm_style",
    }
    assert first["style_policy"]["target"] == "helm_owned_visual_style"
    assert first["style_policy"]["copy_reference_art_directly"] is False
    assert "Produce a final Helm-style nautical chart SVG" in first["repair_prompt"]
    assert "Queue action:" in first["repair_prompt"]
    assert "selected_source_priority_svg" in [example["source"] for example in first["visual_examples"]]

    fallback_only = source_priority_repair_queue.build(limit=50, render_candidate=False, include_s101_redraw=False)
    assert fallback_only["selection"]["source_priority_rows_available"] == 503
    assert fallback_only["selection"]["queueable_jobs"] == 503
    assert set(fallback_only["selection"]["action_counts"]) == {"repair_existing_helm_style_svg"}

    second_window = source_priority_repair_queue.build(limit=150, offset=120, render_candidate=False)
    assert second_window["selection"]["selected_jobs"] == 150
    assert second_window["selection"]["offset"] == 120
    assert second_window["selection"]["skipped_jobs"] == 120
    assert second_window["jobs"][0]["asset"] == "BOYCON81"
    assert second_window["jobs"][-1]["asset"] == "TOPSHP97"

    third_window = source_priority_repair_queue.build(limit=150, offset=270, render_candidate=False)
    assert third_window["selection"]["selected_jobs"] == 150
    assert third_window["selection"]["offset"] == 270
    assert third_window["jobs"][0]["asset"] == "TOPSHP98"
    assert third_window["jobs"][-1]["asset"] == "RECTRC55"
    assert third_window["selection"]["action_counts"] == {
        "redraw_s101_reference_into_helm_style": 83,
        "repair_existing_helm_style_svg": 67,
    }

    saved = json.loads((ROOT / "out" / "source_priority_repair" / "repair_queue.json").read_text())
    assert saved["selection"] == third_window["selection"]
    print("source-priority repair queue: OK")


if __name__ == "__main__":
    main()
