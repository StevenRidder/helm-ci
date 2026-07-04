"""Smoke the FORGE-45 Electronic Chart 1 diff engine.

Run:
  python3 -m forge.tests.test_electronic_chart1_diff_engine
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from PIL import Image

from .. import electronic_chart1_diff_engine


def _first(payload: dict, row_key: str) -> tuple[str, dict]:
    for row in payload["rows"]:
        if row["row_key"] == row_key:
            return "row", row
    for row in payload["hard_pile"]:
        if row["row_key"] == row_key:
            return "hard_pile", row
    raise AssertionError(f"missing row: {row_key}")


def _artifact_path(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return electronic_chart1_diff_engine.ROOT / path


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        result = electronic_chart1_diff_engine.write_diff(
            json_path=tmp_dir / "electronic_chart1_diff_engine.json",
            markdown_path=tmp_dir / "electronic_chart1_diff_engine.md",
            out_dir=tmp_dir / "diff-pngs",
        )
        payload = json.loads((tmp_dir / "electronic_chart1_diff_engine.json").read_text())

        assert result["status"] == "electronic_chart1_diff_engine_ready"
        assert payload["schema"] == "helm.forge.electronic_chart1_diff_engine.v1"
        assert payload["status"] == "electronic_chart1_diff_engine_ready"
        assert payload["policy"]["backend_generated"] is True
        assert payload["policy"]["browser_business_logic_allowed"] is False
        assert payload["policy"]["static_json_fallback_allowed"] is False
        assert payload["policy"]["runtime_promotion_allowed"] is False
        assert payload["policy"]["visual_diff_is_runtime_promotion"] is False
        assert payload["policy"]["missing_or_unsupported_rows_fail_closed"] is True

        assert set(payload["thresholds"]) == {
            "area_fill",
            "conditional_rule",
            "line_style",
            "point_symbol",
            "text_rule",
        }

        summary = payload["summary"]
        assert summary["authority_rows"] == 3057
        assert summary["accounted_authority_rows"] == 3057
        assert summary["opencpn_reference_rows"] == 2460
        assert summary["helm_s57_render_rows"] == 2374
        assert summary["helm_s101_trace_rows"] == 1564
        assert summary["helm_s101_fail_closed_rows"] == 959
        assert summary["authority_text_ready_rows"] == 889
        assert summary["runtime_eligible_rows"] == 0
        assert summary["diff_verdict_rows"] == 2359
        assert summary["diff_hard_pile_rows"] == 698
        assert summary["diff_pngs"] == 7077
        assert summary["diff_pngs"] == summary["diff_verdict_rows"] * 3
        assert summary["row_taxonomy_counts"] == {
            "area_fill": 80,
            "conditional_rule": 83,
            "line_style": 259,
            "point_symbol": 1828,
            "text_rule": 109,
        }
        assert summary["semantic_gate_counts"] == {
            "green": 696,
            "red": 897,
            "yellow": 766,
        }
        assert summary["proof_gate_counts"] == {
            "red": 2193,
            "yellow": 166,
        }
        assert summary["hard_pile_reason_counts"] == {
            "diff:helm_s57_render_missing": 683,
            "diff:opencpn_reference_missing": 597,
            "diff:unsupported_taxonomy:non_reviewable_construct": 273,
            "diff:unsupported_taxonomy:placeholder_manual": 238,
            "diff:unsupported_taxonomy:runtime_overlay": 16,
        }

        assert len(payload["rows"]) == summary["diff_verdict_rows"]
        assert len(payload["hard_pile"]) == summary["diff_hard_pile_rows"]
        assert len({row["row_key"] for row in payload["rows"] + payload["hard_pile"]}) == 3057
        assert all(row["runtime_gate"]["runtime_eligible"] is False for row in payload["rows"] + payload["hard_pile"])
        assert all(row["runtime_gate"]["fail_closed"] is True for row in payload["rows"] + payload["hard_pile"])
        assert all(row["proof_gate"]["runtime_promoted"] is False for row in payload["rows"])
        assert all(row["proof_gate"]["runtime_promotion_allowed"] is False for row in payload["rows"])

        kind, boycan60 = _first(payload, "BOYLAT_BOYCAN60_1907_30184_1907")
        assert kind == "row"
        assert boycan60["s101_trace"]["classification"] == "rule_derived"
        assert boycan60["s101_trace"]["rule_file"] == "PortrayalCatalog/Rules/SpecialPurposeGeneralBuoy.lua"
        assert boycan60["semantic_gate"]["gate"] == "green"
        assert boycan60["proof_gate"]["gate"] == "red"
        assert "runtime_gate:fail_closed" in boycan60["proof_gate"]["reason_codes"]
        assert "human_qa:pending" in boycan60["proof_gate"]["reason_codes"]
        assert len(boycan60["palette_diffs"]) == 3

        first_diff_path = _artifact_path(boycan60["palette_diffs"][0]["diff_output"]["path"])
        assert first_diff_path.exists()
        with Image.open(first_diff_path) as image:
            assert image.size == (128, 128)
            assert image.convert("RGBA").getbbox() is not None

        kind, topshq28 = _first(payload, "TOPMAR_TOPSHQ28_2433_93904_2430")
        assert kind == "row"
        assert topshq28["s101_trace"]["classification"] == "rule_derived"
        assert topshq28["s101_trace"]["rule_file"] == "PortrayalCatalog/Rules/Daymark.lua"
        assert topshq28["semantic_gate"]["gate"] == "green"

        kind, topmar = _first(payload, "DAYMAR_TOPMAR01_2118_93812_2119")
        assert kind == "hard_pile"
        assert "diff:helm_s57_render_missing" in topmar["reason_codes"]
        assert topmar["runtime_gate"]["runtime_promotion_allowed"] is False

        kind, bridge = _first(payload, "BRIDGE_text-only_15_32051_15")
        assert kind == "row"
        assert bridge["semantic_gate"]["gate"] == "red"
        assert "s101_trace:db_backing_missing" in bridge["semantic_gate"]["reason_codes"]
        assert "s101_trace:semantic_only_manual" in bridge["semantic_gate"]["reason_codes"]

        unsupported = [
            row for row in payload["hard_pile"]
            if "diff:unsupported_taxonomy:placeholder_manual" in row["reason_codes"]
        ]
        assert unsupported

        md = (tmp_dir / "electronic_chart1_diff_engine.md").read_text()
        assert "Visual/semantic diff gates never promote runtime output" in md
        assert "diff_verdict_rows: `2359`" in md
        assert "runtime_eligible_rows: `0`" in md

    print("electronic Chart 1 diff engine: OK")


if __name__ == "__main__":
    main()
