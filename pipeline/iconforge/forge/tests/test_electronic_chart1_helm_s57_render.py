"""Smoke the FORGE-42 Helm S-57 render harness.

Run:
  python3 -m forge.tests.test_electronic_chart1_helm_s57_render
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from PIL import Image

from .. import electronic_chart1_helm_s57_render


def _first(payload: dict, predicate) -> dict:
    for row in payload["rows"] + payload["hard_pile"]:
        if predicate(row):
            return row
    raise AssertionError("missing matching Helm S-57 render row")


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        result = electronic_chart1_helm_s57_render.write_render(
            json_path=tmp_dir / "electronic_chart1_helm_s57_render.json",
            markdown_path=tmp_dir / "electronic_chart1_helm_s57_render.md",
            out_dir=tmp_dir / "helm_s57_pngs",
        )
        payload = json.loads((tmp_dir / "electronic_chart1_helm_s57_render.json").read_text())

        assert result["status"] == "helm_s57_render_ready"
        assert payload["schema"] == "helm.forge.electronic_chart1_helm_s57_render.v1"
        assert payload["status"] == "helm_s57_render_ready"
        assert payload["policy"]["backend_generated"] is True
        assert payload["policy"]["canonical_helm_artwork_only"] is True
        assert payload["policy"]["browser_business_logic_allowed"] is False
        assert payload["policy"]["static_json_fallback_allowed"] is False
        assert payload["policy"]["runtime_promotion_allowed"] is False

        summary = payload["summary"]
        assert summary["fixture_rows"] == 2523
        assert summary["rendered_rows"] == 2374
        assert summary["render_hard_pile_rows"] == 149
        assert summary["source_hard_pile_rows"] == 534
        assert summary["produced_candidate_pngs"] == 7122
        assert summary["expected_candidate_pngs_if_all_rendered"] == 7569
        assert summary["palettes"] == ["day", "dusk", "night"]
        assert summary["rendered_status_counts"] == {
            "rendered": 2356,
            "rendered_with_warnings": 18,
        }
        assert summary["row_taxonomy_counts"] == {
            "area_fill": 80,
            "conditional_rule": 83,
            "line_style": 259,
            "point_symbol": 1843,
            "text_rule": 109,
        }
        assert summary["recipe_status_counts"] == {
            "manual_exception_required": 472,
            "missing": 321,
            "recipe_missing": 48,
            "recipe_ready": 1533,
        }
        assert summary["hard_pile_reason_counts"]["helm_s57_render:missing_palette_output"] == 149
        assert summary["hard_pile_reason_counts"]["helm_s57_render:blank_or_no_renderable_instruction"] == 106

        assert len(payload["rows"]) == summary["rendered_rows"]
        assert len(payload["hard_pile"]) == summary["render_hard_pile_rows"]
        assert len(payload["source_hard_pile"]) == summary["source_hard_pile_rows"]
        assert len({row["row_key"] for row in payload["rows"] + payload["hard_pile"]}) == summary["fixture_rows"]

        for row in payload["rows"][:50]:
            assert set(row["palette_outputs"]) == {"day", "dusk", "night"}
            assert row["nonblank_validation"]["all_palette_outputs_nonblank"] is True
            assert row["helm_trace"]["source_boundary"] == "helm_owned_candidate_render_not_runtime_promotion"
            assert row["runtime_gate"]["fail_closed"] is True
            for palette, metadata in row["palette_outputs"].items():
                assert metadata["palette"] == palette
                assert metadata["nonblank"] is True
                assert metadata["color_source"]
                path = Path(metadata["path"])
                assert path.exists()
                image = Image.open(path)
                assert image.size == (128, 128)
                assert image.getchannel("A").getbbox() is not None

        boycan60 = _first(payload, lambda row: row["row_key"] == "BOYSPP_BOYCAN60_1956_30227_1956")
        assert boycan60["status"] == "rendered"
        assert boycan60["helm_trace"]["art_path"] == "assets/svg/triad_generated/BOYCAN60.svg"
        assert "helm_canonical_svg" in boycan60["helm_trace"]["render_sources"]
        assert boycan60["helm_trace"]["recipe"]["status"] == "recipe_ready"
        assert boycan60["helm_trace"]["recipe"]["shape_family"] == "buoy_can"

        bridge = _first(payload, lambda row: row["row_key"] == "BRIDGE_text-only_15_32051_15")
        assert bridge["status"] == "rendered"
        assert "helm_s57_text_sample" in bridge["helm_trace"]["render_sources"]
        assert "helm_s57_line_sample" in bridge["helm_trace"]["render_sources"]

        admare = _first(payload, lambda row: row["row_key"] == "ADMARE_none_4_32040_4")
        assert admare["status"] == "rendered"
        assert "helm_s57_line_sample" in admare["helm_trace"]["render_sources"]

        quesmrk = _first(payload, lambda row: row["row_key"] == "######_QUESMRK1_0_32036_0")
        assert quesmrk["status"] == "rendered"
        assert "helm_s57_area_sample" in quesmrk["helm_trace"]["render_sources"]
        assert "helm_canonical_svg_pattern_tile" in quesmrk["helm_trace"]["render_sources"]

        arcsln = _first(payload, lambda row: row["row_key"] == "ARCSLN_ARCSLN01_7_32043_7")
        assert arcsln["status"] == "helm_s57_unrenderable"
        assert "helm_line_sample:missing_colour_authority" in arcsln["reason_codes"]
        assert "helm_s57_render:missing_palette_output" in arcsln["reason_codes"]

        md = (tmp_dir / "electronic_chart1_helm_s57_render.md").read_text()
        assert "Candidate renders are generated from backend fixture rows" in md
        assert "render_hard_pile_rows: `149`" in md

    print("electronic Chart 1 Helm S-57 render: OK")


if __name__ == "__main__":
    main()
