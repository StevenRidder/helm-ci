"""Smoke the FORGE-43 Helm S-101 render trace harness.

Run:
  python3 -m forge.tests.test_electronic_chart1_helm_s101_render
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from .. import electronic_chart1_helm_s101_render


def _first(payload: dict, row_key: str) -> dict:
    for row in payload["rows"] + payload["hard_pile"]:
        if row["row_key"] == row_key:
            return row
    raise AssertionError(f"missing row: {row_key}")


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        result = electronic_chart1_helm_s101_render.write_render_trace(
            json_path=tmp_dir / "electronic_chart1_helm_s101_render.json",
            markdown_path=tmp_dir / "electronic_chart1_helm_s101_render.md",
        )
        payload = json.loads((tmp_dir / "electronic_chart1_helm_s101_render.json").read_text())

        assert result["status"] == "helm_s101_render_trace_ready"
        assert payload["schema"] == "helm.forge.electronic_chart1_helm_s101_render.v1"
        assert payload["status"] == "helm_s101_render_trace_ready"
        assert payload["policy"]["backend_generated"] is True
        assert payload["policy"]["db_resolver_trace_required"] is True
        assert payload["policy"]["uses_forge42_render_evidence"] is True
        assert payload["policy"]["duplicates_artwork_generation"] is False
        assert payload["policy"]["browser_business_logic_allowed"] is False
        assert payload["policy"]["static_json_fallback_allowed"] is False
        assert payload["policy"]["runtime_promotion_allowed"] is False
        assert payload["policy"]["raw_s101_svg_colour_is_not_authority"] is True

        summary = payload["summary"]
        assert summary["fixture_rows"] == 2523
        assert summary["trace_ready_rows"] == 1564
        assert summary["trace_fail_closed_rows"] == 959
        assert summary["accounted_fixture_rows"] == 2523
        assert summary["source_hard_pile_rows"] == 534
        assert summary["forge42_rendered_rows"] == 2374
        assert summary["forge42_render_hard_pile_rows"] == 149
        assert summary["runtime_eligible_rows"] == 0
        assert summary["s101_trace_class_counts"] == {
            "catalogue_rule": 229,
            "direct": 903,
            "documented_deviation": 181,
            "non_s101_or_extension_profile": 494,
            "non_s101_runtime_construct": 43,
            "rule_derived": 370,
            "semantic_only_manual": 297,
            "unresolved": 6,
        }
        assert summary["ready_trace_class_counts"] == {
            "catalogue_rule": 151,
            "direct": 897,
            "documented_deviation": 146,
            "rule_derived": 370,
        }
        assert summary["fail_closed_trace_class_counts"] == {
            "catalogue_rule": 78,
            "direct": 6,
            "documented_deviation": 35,
            "non_s101_or_extension_profile": 494,
            "non_s101_runtime_construct": 43,
            "semantic_only_manual": 297,
            "unresolved": 6,
        }
        assert summary["hard_pile_reason_counts"]["helm_s101_render:no_forge42_candidate_render"] == 149
        assert summary["hard_pile_reason_counts"]["s101_trace:non_s101_or_extension_profile"] == 494
        assert summary["hard_pile_reason_counts"]["s101_trace:semantic_only_manual"] == 297
        assert summary["hard_pile_reason_counts"]["s101_trace:unresolved"] == 6

        assert len(payload["rows"]) == summary["trace_ready_rows"]
        assert len(payload["hard_pile"]) == summary["trace_fail_closed_rows"]
        assert len({row["row_key"] for row in payload["rows"] + payload["hard_pile"]}) == summary["fixture_rows"]
        assert all(row["runtime_gate"]["runtime_eligible"] is False for row in payload["rows"])
        assert all(row["runtime_gate"]["fail_closed"] is True for row in payload["rows"] + payload["hard_pile"])

        for row in payload["rows"][:50]:
            assert row["status"] == "s101_trace_ready"
            assert row["s101_trace"]["db_backed"] is True
            assert row["s101_trace"]["filename_only_match"] is False
            assert row["helm_candidate_render"]["present"] is True
            assert set(row["helm_candidate_render"]["palette_outputs"]) == {"day", "dusk", "night"}
            assert row["helm_candidate_render"]["nonblank_validation"]["all_palette_outputs_nonblank"] is True
            assert row["colour_transform_authority"]["raw_s101_svg_colour_is_not_authority"] is True

        boycan60 = _first(payload, "BOYLAT_BOYCAN60_1907_30184_1907")
        assert boycan60["status"] == "s101_trace_ready"
        assert boycan60["s101_trace"]["classification"] == "rule_derived"
        assert boycan60["s101_trace"]["feature_type"] == "BuoyLateral"
        assert boycan60["s101_trace"]["rule_file"] == "PortrayalCatalog/Rules/SpecialPurposeGeneralBuoy.lua"
        assert boycan60["s101_trace"]["attributes"]["buoyShape"] == "can"
        assert boycan60["s101_trace"]["attributes"]["colour"] == ["red"]
        assert boycan60["s101_trace"]["filename_only_match"] is False
        assert boycan60["helm_candidate_render"]["recipe"]["shape_family"] == "buoy_can"

        topshq28_daymark = _first(payload, "DAYMAR_TOPSHQ28_2160_93930_2161")
        assert topshq28_daymark["status"] == "s101_trace_ready"
        assert topshq28_daymark["s101_trace"]["classification"] == "rule_derived"
        assert topshq28_daymark["s101_trace"]["rule_file"] == "PortrayalCatalog/Rules/Daymark.lua"
        assert topshq28_daymark["topmark_daymark_context"]["topmark_context"] == "daymark"
        assert topshq28_daymark["topmark_daymark_context"]["topmark_shape_source_attribute"] == "TOPSHP"
        assert topshq28_daymark["topmark_daymark_context"]["topmark_shape_code"] == 28

        topshq28_topmark = _first(payload, "TOPMAR_TOPSHQ28_2433_93904_2430")
        assert topshq28_topmark["status"] == "s101_trace_ready"
        assert topshq28_topmark["s101_trace"]["feature_type"] == "Topmark"
        assert topshq28_topmark["topmark_daymark_context"]["topmark_context"] == "topmark"
        assert topshq28_topmark["topmark_daymark_context"]["topmark_shape_source_attribute"] == "TOPSHP"

        topmar_catalogue = _first(payload, "DAYMAR_TOPMAR01_2118_93812_2119")
        assert topmar_catalogue["status"] == "helm_s101_fail_closed"
        assert topmar_catalogue["s101_trace"]["classification"] == "catalogue_rule"
        assert topmar_catalogue["s101_trace"]["db_backed"] is True
        assert topmar_catalogue["s101_trace"]["rule_file"] == "PortrayalCatalog/Rules/TOPMAR02.lua"
        assert "helm_s101_render:no_forge42_candidate_render" in topmar_catalogue["reason_codes"]

        unresolved = [row for row in payload["hard_pile"] if row["s101_trace"]["classification"] == "unresolved"]
        assert len(unresolved) == 6
        for row in unresolved:
            assert "s101_trace:unresolved" in row["reason_codes"]
            assert row["runtime_gate"]["runtime_eligible"] is False

        md = (tmp_dir / "electronic_chart1_helm_s101_render.md").read_text()
        assert "Rule-derived BOY/BCN/TOP rows must carry rule files and attributes" in md
        assert "trace_ready_rows: `1564`" in md
        assert "trace_fail_closed_rows: `959`" in md

    print("electronic Chart 1 Helm S-101 render trace: OK")


if __name__ == "__main__":
    main()
