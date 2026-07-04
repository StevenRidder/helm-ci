"""Smoke the DB colour-authority contract.

Run:  python3 -m forge.tests.test_colour_authority_contract
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import colour_authority_contract


ROOT = Path(__file__).resolve().parent.parent.parent


def main() -> None:
    result = colour_authority_contract.build()
    assert result["schema"] == "helm.iconforge.colour_authority_contract.v1"
    assert result["status"] == "colour_authority_complete"
    assert result["summary"]["source_table_rows"] == 824
    assert result["summary"]["rows"] == 824

    counts = result["summary"]["status_counts"]
    assert counts["aligned"] > 0
    assert counts["feature_empty_visual_defined"] > 0
    assert counts["feature_colour_dropped"] > 0
    assert counts["feature_visual_order_difference"] > 0
    assert counts["pattern_orientation_conflict"] > 0
    assert counts["visual_colour_extra"] > 0
    assert result["summary"]["gate_status_counts"].get("warn", 0) == 0
    assert result["summary"]["gate_status_counts"]["blocked"] > 0

    by_asset = {row["asset"]: row for row in result["rows"]}

    boylat25 = by_asset["BOYLAT25"]
    assert boylat25["feature_colour_sequence"] == ["red", "green"]
    assert boylat25["visual_colour_sequence"] == ["red", "green"]
    assert boylat25["status"] == "aligned"
    assert boylat25["gate_status"] == "pass"
    assert boylat25["render_colour_authority"] == "feature_predicates_and_visual_recipe_aligned"

    boypil60 = by_asset["BOYPIL60"]
    assert boypil60["feature_colour_sequence"] == ["red"]
    assert boypil60["visual_colour_sequence"] == ["red"]
    assert boypil60["status"] == "aligned"

    bcngen64 = by_asset["BCNGEN64"]
    assert bcngen64["feature_colour_sequence"] == ["red", "white", "red", "white"]
    assert bcngen64["visual_colour_sequence"] == ["white", "red", "white", "red", "white"]
    assert bcngen64["status"] == "feature_visual_order_difference"
    assert bcngen64["gate_status"] == "blocked"
    assert bcngen64["runtime_blocker"] is True
    assert bcngen64["render_colour_authority"] == "manual_review_required"
    assert bcngen64["missing_feature_colours"] == []
    assert bcngen64["extra_visual_colours"] == []

    bcnlat15 = by_asset["BCNLAT15"]
    assert bcnlat15["status"] == "feature_colour_dropped"
    assert bcnlat15["gate_status"] == "blocked"
    assert bcnlat15["runtime_blocker"] is True
    assert bcnlat15["missing_feature_colours"] == ["green"]
    assert bcnlat15["extra_visual_colours"] == ["white"]
    assert "colour_authority:feature_colour_dropped" in bcnlat15["reason_codes"]

    aisves01 = by_asset["AISVES01"]
    assert aisves01["feature_colour_sequence"] == []
    assert aisves01["visual_colour_sequence"] == ["green", "green"]
    assert aisves01["visual_stroke_sequence"] == ["green", "green"]
    assert aisves01["status"] == "feature_empty_visual_defined"

    boypil73 = by_asset["BOYPIL73"]
    assert boypil73["feature_colour_pattern"] == "vertical bands/stripes in the listed colour order"
    assert boypil73["feature_pattern_requirements"] == ["vertical"]
    assert boypil73["visual_pattern_evidence"] == ["vertical"]
    assert boypil73["status"] == "aligned"

    topshpi3 = by_asset["TOPSHPI3"]
    assert topshpi3["feature_pattern_requirements"] == ["diagonal"]
    assert topshpi3["visual_pattern_evidence"] == []
    assert topshpi3["status"] == "pattern_orientation_conflict"
    assert topshpi3["gate_status"] == "blocked"
    assert "colour_authority:pattern_orientation_missing:diagonal" in topshpi3["reason_codes"]

    daytri01 = by_asset["DAYTRI01"]
    assert daytri01["feature_colour_sequence"] == []
    assert daytri01["visual_colour_sequence"] == ["magenta"]
    assert daytri01["status"] == "feature_empty_visual_defined"

    saved = json.loads((ROOT / "catalog" / "colour_authority_contract.json").read_text())
    assert saved["summary"]["rows"] == result["summary"]["rows"]
    assert (ROOT / "catalog" / "colour_authority_contract.md").exists()

    print("colour authority contract: OK")


if __name__ == "__main__":
    main()
