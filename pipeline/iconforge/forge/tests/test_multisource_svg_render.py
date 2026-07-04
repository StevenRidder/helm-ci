"""Smoke the multi-source draft SVG renderer.

Run:  python -m forge.tests.test_multisource_svg_render
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import multisource_svg_render


ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    result = multisource_svg_render.build(assets={"TOPMA114", "BOYCAR01"}, size=96)
    summary = result["summary"]

    assert result["status"] == "pass_explicit_subset"
    assert summary["selected_symbols"] == 2
    assert summary["rendered_pngs"] == 6
    assert summary["expected_pngs"] == 6
    assert summary["hard_pile_entries"] == 0
    assert summary["palette_counts"] == {"day": 2, "dusk": 2, "night": 2}

    by_asset_palette = {(row["asset"], row["palette"]): row for row in result["rows"]}
    topmark_day = by_asset_palette[("TOPMA114", "day")]
    assert topmark_day["render"].endswith("TOPMA114__day.png")
    assert topmark_day["bytes"] > 100
    assert "black" in topmark_day["css_tokens"]
    assert (ROOT / topmark_day["render"]).exists()

    saved = json.loads((ROOT / "out" / "multisource_svg_draft" / "render_report.json").read_text())
    assert saved["summary"] == summary
    print("multi-source SVG render: OK")


if __name__ == "__main__":
    main()
