"""Smoke the CHART-10 symbol readiness release gate.

Run:
  python3 -m forge.tests.test_electronic_chart1_symbol_readiness_gate
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from .. import electronic_chart1_symbol_readiness_gate


def _check(payload: dict, name: str) -> dict:
    for check in payload["checks"]:
        if check["name"] == name:
            return check
    raise AssertionError(f"missing check {name}")


def main() -> None:
    payload = electronic_chart1_symbol_readiness_gate.build_gate()
    summary = payload["summary"]

    assert payload["schema"] == "helm.forge.electronic_chart1_symbol_readiness_gate.v1"
    assert payload["status"] == "release_blocked"
    assert payload["release_ready"] is False
    assert payload["decision"]["may_mark_all_symbols_ready"] is False

    assert summary["total_release_rows"] == 3057
    assert summary["registry_symbols"] == 2636
    assert summary["registry_semantic_accepted_rows"] == 1225
    assert summary["final_approved_rows"] == 0
    assert summary["runtime_export_rows"] == 0
    assert summary["runtime_blocked_rows"] == 3057
    assert summary["hard_pile_rows"] == 698
    assert summary["unsupported_extension_profile_rows"] == 494
    assert summary["scoped_mapping_rows"] == 824
    assert summary["scoped_mapping_unresolved_rows"] == 0
    assert summary["checks_blocked"] == 1
    assert summary["blocked_checks"] == ["proof_gallery_and_human_signoff"]

    mapping = _check(payload, "mapping_audit")
    assert mapping["status"] == "pass"
    assert mapping["summary"]["scoped_rows"] == 824
    assert mapping["summary"]["all_rows_classified"] is True
    assert mapping["summary"]["unresolved_rows"] == 0

    signoff = _check(payload, "proof_gallery_and_human_signoff")
    assert signoff["status"] == "blocked"
    assert signoff["summary"]["registry_semantic_accepted_rows"] == 1225
    assert signoff["summary"]["final_approved_rows"] == 0
    assert "human_review_pending" in signoff["blockers"]

    loader = _check(payload, "cxx_loader_validates_package")
    assert loader["status"] == "pass"
    assert loader["summary"]["matches_runtime_promotion_gate"] is True
    assert loader["summary"]["runtime_eligible_rows"] == 0

    fixtures = _check(payload, "attribute_fixture_suite")
    assert fixtures["status"] == "pass"
    assert fixtures["summary"]["fixtures"] >= 7
    assert fixtures["summary"]["all_default_render_blocked"] is True

    vulkan = _check(payload, "vulkan_day_dusk_night_smoke")
    assert vulkan["status"] == "pass"
    assert vulkan["summary"]["palette_images"] == ["day", "dusk", "night"]

    baseline = _check(payload, "opencpn_baseline_comparison")
    assert baseline["status"] == "pass"
    assert baseline["summary"]["status_counts"] == {
        "needs-review": 2353,
        "not-comparable": 698,
        "pass": 6,
    }

    runtime = _check(payload, "runtime_eligibility_gate")
    assert runtime["status"] == "pass"
    assert runtime["summary"]["runtime_export_rows"] == 0
    assert runtime["summary"]["blocked_rows"] == 3057

    handoff = _check(payload, "adapter_handoff")
    assert handoff["status"] == "pass"
    assert handoff["summary"]["consumers"] == ["opencpn_native", "helm_offscreen"]

    assert payload["remaining_blockers"]["gate_blockers"] == [
        "runtime_export_rows_zero",
        "human_review_pending",
        "visual_or_semantic_diff_not_all_green",
        "hard_pile_not_empty",
    ]
    assert payload["remaining_blockers"]["runtime_reason_counts"]["human_review_status:needs_human_review"] == 3057
    assert payload["remaining_blockers"]["runtime_reason_counts"]["runtime_gate:fail_closed"] == 3057

    commands = [item["command"] for item in payload["validation_commands"]]
    assert "engine/test-symbol-package-loader.sh" in commands
    assert "engine/test-vulkan-symbol-selection-render.sh" in commands
    assert "engine/test-symbol-render-handoff.sh" in commands

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        result = electronic_chart1_symbol_readiness_gate.write_gate(
            json_path=tmp_dir / "gate.json",
            markdown_path=tmp_dir / "gate.md",
        )
        written = json.loads((tmp_dir / "gate.json").read_text())
        assert result["status"] == "release_blocked"
        assert written["summary"] == summary
        md = (tmp_dir / "gate.md").read_text()
        assert "runtime_export_rows: `0`" in md
        assert "proof_gallery_and_human_signoff" in md
        assert "engine/test-symbol-render-handoff.sh" in md

    print("electronic Chart 1 symbol readiness gate: OK")


if __name__ == "__main__":
    main()
