"""Smoke the second source-priority Helm-style repair batch.

Run:  python -m forge.tests.test_source_priority_repair_batch2
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import source_priority_repair_batch2


ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    report = source_priority_repair_batch2.build(render_outputs=False)

    assert report["status"] == "candidate_batch_pending_visual_review"
    assert report["batch_offset"] == 120
    assert report["batch_size"] == 150
    assert report["summary"] == {
        "generated_owned_candidates": 150,
        "license_pending_reference_candidates": 0,
        "redraw_s101_reference_into_helm_style": 0,
        "repair_existing_helm_style_svg": 150,
        "visual_parity": "pending_visual_model_and_human_review",
    }
    assert all(row["qa"]["final_approved"] is False for row in report["symbols"])
    assert report["symbols"][0]["asset"] == "BOYCON81"
    assert report["symbols"][-1]["asset"] == "TOPSHP97"
    assert {row["risk_bucket"] for row in report["symbols"]} == {"aids_to_navigation"}

    by_asset = {row["asset"]: row for row in report["symbols"]}
    for asset in ["BOYCON81", "BOYLAT25", "BOYPIL68", "BOYSPH70", "TOPSHP97"]:
        row = by_asset[asset]
        after = ROOT / row["after_svg"]
        before = ROOT / row["before_svg"]
        assert after.exists()
        assert after.read_text() == before.read_text()
        assert row["provenance"]["origin"] == "generated-owned-artwork"
        assert row["provenance"]["generator"] == "forge.source_priority_repair_batch2"

    saved = json.loads((ROOT / "catalog" / "owned_repair_batch2.json").read_text())
    assert saved["batch_offset"] == 120
    assert saved["batch_size"] == 150
    print("source-priority repair batch2: OK")


if __name__ == "__main__":
    main()
