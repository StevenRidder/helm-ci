"""Smoke the multi-source visual repair queue.

Run:  python -m forge.tests.test_multisource_visual_repair_queue
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import multisource_svg_render
from .. import multisource_visual_repair_queue


ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    # Render the exact-crop topmark rows used by the first queue slice.
    assets = {"TOPMA100", "TOPMA102", "TOPMA106", "TOPMA107", "TOPMA109"}
    render_result = multisource_svg_render.build(assets=assets, size=96)
    assert render_result["summary"]["hard_pile_entries"] == 0

    result = multisource_visual_repair_queue.build(limit=5, palette="day")
    selection = result["selection"]
    assert result["status"] == "ready_explicit_subset"
    assert selection["required_gate_status"] == "exact_crop_failed_verifier"
    assert selection["required_reference_evidence_status"] == "exact_symbol_crop"
    assert selection["exact_failures_available"] == 139
    assert selection["selected_jobs"] == 5
    assert selection["hard_pile_entries"] == 134
    assert selection["shape_counts"] == {"topmark": 5}

    for job in result["jobs"]:
        assert job["asset"].startswith("TOPMA")
        assert job["candidate"]["render"].endswith("__day.png")
        assert job["references"]["chart1_exact_crop"]["status"] == "exact_symbol_crop"
        assert "out/chart1_parity/reference/crops/topmark_" in job["references"]["chart1_exact_crop"]["path"]
        assert job["references"]["opencpn_s52_reference_render"]["license_boundary"] == "local_visual_oracle_not_canonical_artwork"
        assert job["strict_invariants"]
        assert "Return JSON" in job["visual_judge_prompt"]
        assert "trace GPL/OpenCPN raster artwork" in job["visual_judge_prompt"]
        sources = [example["source"] for example in job["visual_examples"]]
        assert sources[:3] == [
            "helm_generated_draft_svg",
            "chart1_exact_crop",
            "opencpn_s52_reference_render",
        ]
        assert "chart1_mappings_symbol_reference" in sources
        assert "Visual examples:" in job["visual_judge_prompt"]

    saved = json.loads((ROOT / "out" / "multisource_visual_repair" / "repair_queue.json").read_text())
    assert saved["selection"] == selection
    print("multi-source visual repair queue: OK")


if __name__ == "__main__":
    main()
