"""Smoke the FORGE-41 OpenCPN/S-52 reference harness.

Run:
  python3 -m forge.tests.test_electronic_chart1_opencpn_reference
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from PIL import Image

from .. import electronic_chart1_opencpn_reference


def _first(payload: dict, predicate) -> dict:
    for row in payload["rows"] + payload["hard_pile"]:
        if predicate(row):
            return row
    raise AssertionError("missing matching OpenCPN reference row")


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        result = electronic_chart1_opencpn_reference.write_reference(
            json_path=tmp_dir / "electronic_chart1_opencpn_reference.json",
            markdown_path=tmp_dir / "electronic_chart1_opencpn_reference.md",
            out_dir=tmp_dir / "reference_pngs",
        )
        payload = json.loads((tmp_dir / "electronic_chart1_opencpn_reference.json").read_text())

        assert result["status"] == "reference_ready"
        assert payload["schema"] == "helm.forge.electronic_chart1_opencpn_reference.v1"
        assert payload["status"] == "reference_ready"
        assert payload["policy"]["reference_only"] is True
        assert payload["policy"]["canonical_helm_artwork"] is False
        assert payload["policy"]["browser_business_logic_allowed"] is False
        assert payload["policy"]["static_json_fallback_allowed"] is False
        assert payload["policy"]["runtime_promotion_allowed"] is False

        summary = payload["summary"]
        assert summary["fixture_rows"] == 2523
        assert summary["rendered_rows"] == 2460
        assert summary["render_hard_pile_rows"] == 63
        assert summary["source_hard_pile_rows"] == 534
        assert summary["produced_reference_pngs"] == 7380
        assert summary["expected_reference_pngs_if_all_rendered"] == 7569
        assert summary["palettes"] == ["day", "dusk", "night"]
        assert summary["rendered_status_counts"] == {
            "rendered": 2378,
            "rendered_with_warnings": 82,
        }
        assert summary["row_taxonomy_counts"] == {
            "area_fill": 100,
            "conditional_rule": 141,
            "line_style": 282,
            "point_symbol": 1828,
            "text_rule": 109,
        }
        assert summary["hard_pile_reason_counts"]["opencpn_reference_render:missing_palette_output"] == 63

        assert len(payload["rows"]) == summary["rendered_rows"]
        assert len(payload["hard_pile"]) == summary["render_hard_pile_rows"]
        assert len(payload["source_hard_pile"]) == summary["source_hard_pile_rows"]
        assert len({row["row_key"] for row in payload["rows"] + payload["hard_pile"]}) == summary["fixture_rows"]

        for row in payload["rows"][:50]:
            assert set(row["palette_outputs"]) == {"day", "dusk", "night"}
            assert row["nonblank_validation"]["all_palette_outputs_nonblank"] is True
            assert row["reference_trace"]["source_boundary"] == "comparison_evidence_only_not_helm_canonical_art"
            assert row["reference_trace"]["chartsymbols_xml_sha256"] == payload["source"]["opencpn_s52"]["chartsymbols_xml_sha256"]
            assert set(row["reference_trace"]["raster_sheet_sha256"]) == {"day", "dusk", "night"}
            for palette, metadata in row["palette_outputs"].items():
                assert metadata["palette"] == palette
                assert metadata["nonblank"] is True
                path = Path(metadata["path"])
                assert path.exists()
                image = Image.open(path)
                assert image.size == (128, 128)
                assert image.getchannel("A").getbbox() is not None

        boycan60 = _first(payload, lambda row: row["row_key"] == "BOYSPP_BOYCAN60_1956_30227_1956")
        assert boycan60["status"] == "rendered"
        assert boycan60["s52"]["symbol_refs"] == ["BOYCAN60"]
        assert "bitmap_crop" in boycan60["reference_trace"]["render_sources"]
        assert "s52_text_sample" in boycan60["reference_trace"]["render_sources"]
        assert boycan60["runtime_gate"]["fail_closed"] is True

        bridge = _first(payload, lambda row: row["row_key"] == "BRIDGE_text-only_15_32051_15")
        assert bridge["status"] == "rendered"
        assert bridge["s52"]["text_refs"]
        assert "s52_text_sample" in bridge["reference_trace"]["render_sources"]

        admare = _first(payload, lambda row: row["row_key"] == "ADMARE_none_4_32040_4")
        assert admare["status"] == "rendered"
        assert admare["s52"]["line_style_refs"] == ["DASH"]
        assert "s52_instruction_line_sample" in admare["reference_trace"]["render_sources"]

        depare = _first(payload, lambda row: row["row_key"] == "DEPARE_DEPARE01_40_32076_40")
        assert depare["status"] == "reference_unrenderable"
        assert "conditional_ref:DEPARE01:no_direct_asset" in depare["reason_codes"]
        assert "opencpn_reference_render:missing_palette_output" in depare["reason_codes"]

        md = (tmp_dir / "electronic_chart1_opencpn_reference.md").read_text()
        assert "OpenCPN/S-52 output is comparison evidence only" in md
        assert "render_hard_pile_rows: `63`" in md

    print("electronic Chart 1 OpenCPN reference: OK")


if __name__ == "__main__":
    main()
