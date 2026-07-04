"""Smoke the first source-priority Helm-style repair batch.

Run:  python -m forge.tests.test_source_priority_repair_batch1
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import source_priority_repair_batch1


ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    report = source_priority_repair_batch1.build(limit=120, render_outputs=False)

    assert report["status"] == "candidate_batch_pending_visual_review"
    assert report["batch_size"] == 120
    assert report["summary"] == {
        "generated_owned_candidates": 120,
        "license_pending_reference_candidates": 0,
        "redraw_s101_reference_into_helm_style": 19,
        "repair_existing_helm_style_svg": 101,
        "visual_parity": "pending_visual_model_and_human_review",
    }
    assert all(row["qa"]["final_approved"] is False for row in report["symbols"])

    by_asset = {row["asset"]: row for row in report["symbols"]}
    assert by_asset["BCNCAR01"]["queue_action"] == "redraw_s101_reference_into_helm_style"
    assert by_asset["BCNCAR01"]["provenance"]["origin"] == "generated-owned-artwork"
    assert by_asset["BCNCAR01"]["repair_note"].startswith("redrawn in Helm style")
    assert by_asset["TOPMAR90"]["queue_action"] == "repair_existing_helm_style_svg"
    assert by_asset["TOPMAR90"]["provenance"]["origin"] == "generated-owned-artwork"
    assert by_asset["WRECKS04"]["repair_note"].startswith("redrawn in Helm style")

    for asset in ["BCNCAR01", "BOYCAR04", "OBSTRN01", "WRECKS04", "BOYCON80"]:
        svg = ROOT / by_asset[asset]["after_svg"]
        assert svg.exists()

    # S-101 rows must be our own SVG redraws, not raw copied reference files.
    bcncar = by_asset["BCNCAR01"]
    assert (ROOT / bcncar["after_svg"]).read_text() != (ROOT / bcncar["before_svg"]).read_text()
    assert 'data-origin="generated-owned-artwork"' in (ROOT / bcncar["after_svg"]).read_text()
    uwtroc03 = (ROOT / by_asset["UWTROC03"]["after_svg"]).read_text()
    assert 'fill="var(--blue)"' in uwtroc03
    assert 'stroke-dasharray="1 6"' in uwtroc03
    assert 'M14 32H50M32 14V50' in uwtroc03
    uwtroc04 = (ROOT / by_asset["UWTROC04"]["after_svg"]).read_text()
    assert 'M12 32H52M20 13L44 51M44 13L20 51' in uwtroc04
    assert "Q23 14" not in uwtroc04
    wrecks01 = (ROOT / by_asset["WRECKS01"]["after_svg"]).read_text()
    assert 'stroke="var(--black)"' in wrecks01
    assert 'var(--gray)' not in wrecks01
    assert 'M18 42 L7.5 28 L53 42' in wrecks01
    assert 'M31.3 35 L35.5 21' in wrecks01
    assert "L31 23L40 44" not in wrecks01
    # Existing Helm draft rows are already generated-owned, so carrying them
    # forward preserves the style the user preferred.
    boycon = by_asset["BOYCON80"]
    assert (ROOT / boycon["after_svg"]).read_text() == (ROOT / boycon["before_svg"]).read_text()

    saved = json.loads((ROOT / "catalog" / "owned_repair_batch1.json").read_text())
    assert saved["batch_size"] == 120
    print("source-priority repair batch1: OK")


if __name__ == "__main__":
    main()
