"""Smoke the CHART-8 OpenCPN baseline comparison manifest.

Run:
  python3 -m forge.tests.test_electronic_chart1_opencpn_baseline
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from .. import electronic_chart1_opencpn_baseline


def _first(rows: list[dict], row_key: str) -> dict:
    for row in rows:
        if row["row_key"] == row_key:
            return row
    raise AssertionError(f"missing row: {row_key}")


def main() -> None:
    payload = electronic_chart1_opencpn_baseline.build_baseline()
    summary = payload["summary"]

    assert payload["schema"] == "helm.forge.electronic_chart1_opencpn_baseline.v1"
    assert payload["status"] == "opencpn_baseline_comparison_ready"
    assert payload["policy"]["opencpn_role"] == "reference_comparison_only"
    assert payload["policy"]["comparison_pixels_are_source_artwork"] is False
    assert payload["policy"]["runtime_promotion_allowed"] is False
    assert set(payload["tolerance_checks"]) == {
        "blank_render",
        "wrong_anchor",
        "wrong_palette",
        "wrong_symbol_class",
    }

    assert summary["rows"] == 3057
    assert summary["status_counts"]["not-comparable"] == 698
    assert summary["status_counts"]["needs-review"] > 0
    assert summary["status_counts"]["pass"] > 0
    assert summary["runtime_promotion_allowed_rows"] == 0
    assert summary["rows_with_all_opencpn_palette_refs"] == 2460
    assert summary["human_approval_status_counts"]["needs_human_review"] == 3057
    assert summary["check_status_counts"]["blank_render:pass"] > 0
    assert summary["check_status_counts"]["wrong_palette:needs-review"] > 0
    assert summary["check_status_counts"]["wrong_symbol_class:needs-review"] > 0
    assert summary["check_status_counts"]["wrong_anchor:needs-review"] > 0

    boycan60 = _first(payload["rows"], "BOYLAT_BOYCAN60_1907_30184_1907")
    assert boycan60["comparison_status"] == "needs-review"
    assert boycan60["roles"]["opencpn"] == "reference_comparison_only"
    assert boycan60["roles"]["helm_fixture_render"] == "generated_owned_candidate"
    assert boycan60["proof_bundle"]["proof_data_path"] == "proof/package-proof-data.json"
    assert boycan60["proof_bundle"]["comparison_page"] == "proof/compare-opencpn.html"
    assert boycan60["proof_bundle"]["proof_row_present"] is True
    assert boycan60["human_approval"]["status"] == "needs_human_review"
    assert boycan60["human_approval"]["runtime_promotion_allowed"] is False
    assert set(boycan60["palettes"]) == {"day", "dusk", "night"}
    day = boycan60["palettes"]["day"]
    assert day["opencpn_reference"]["path"].endswith("__day.png")
    assert day["opencpn_reference"]["role"] == "reference_comparison_only"
    assert day["helm_fixture_render"]["path"].endswith("__day.png")
    assert day["visual_diff"]["path"].endswith("__day__opencpn_vs_helm.png")
    assert day["tolerance_checks"]["blank_render"]["status"] == "pass"
    assert day["tolerance_checks"]["wrong_palette"]["metric"] == "mean_rgba_delta"
    assert day["tolerance_checks"]["wrong_symbol_class"]["metric"] == "alpha_iou"
    assert day["tolerance_checks"]["wrong_anchor"]["metric"] == "bbox_iou"

    topmar = _first(payload["rows"], "DAYMAR_TOPMAR01_2118_93812_2119")
    assert topmar["comparison_status"] == "not-comparable"
    assert "diff:helm_s57_render_missing" in topmar["status_reason_codes"]
    assert topmar["palettes"]["day"]["status"] == "not-comparable"
    assert topmar["palettes"]["day"]["opencpn_reference"]["path"]
    assert topmar["palettes"]["day"]["helm_fixture_render"]["path"] is None

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        result = electronic_chart1_opencpn_baseline.write_baseline(
            json_path=tmp_dir / "baseline.json",
            markdown_path=tmp_dir / "baseline.md",
        )
        written = json.loads((tmp_dir / "baseline.json").read_text())
        assert result["status"] == "opencpn_baseline_comparison_ready"
        assert written["summary"] == summary
        md = (tmp_dir / "baseline.md").read_text()
        assert "OpenCPN render paths are reference/comparison only" in md
        assert "Visual diffs and tolerance checks are QA diagnostics" in md
        assert "runtime_promotion_allowed_rows: `0`" in md

    print("electronic Chart 1 OpenCPN baseline comparison: OK")


if __name__ == "__main__":
    main()
