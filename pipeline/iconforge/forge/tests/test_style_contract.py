"""Smoke the shared Helm/OpenBridge icon style contract.

Run:  python -m forge.tests.test_style_contract
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import render
from .. import style_contract
from .. import multisource_svg_pack


ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    day = style_contract.OPENBRIDGE_NAV_PALETTES["day"]
    assert day["red"] == "#f15469"
    assert day["green"] == "#68e456"
    assert day["yellow"] == "#f4da48"
    assert day["magenta"] == "#c545c3"
    assert day["orange"] == "#eb7d36"
    assert day["blue"] == "#8fb5d9"
    assert day["ink"] == day["black"]
    assert multisource_svg_pack.PALETTES is style_contract.OPENBRIDGE_NAV_PALETTES

    stylepack = json.loads((ROOT / "stylepacks" / "open-bridge.json").read_text())
    assert stylepack["stroke_width"] == style_contract.OPENBRIDGE_STROKE_WIDTH
    for palette, colors in style_contract.OPENBRIDGE_NAV_PALETTES.items():
        for token, value in colors.items():
            assert stylepack["palettes"][palette][token] == value

    owned_svg = (
        '<svg data-origin="generated-owned-artwork">'
        '<path stroke="var(--black)" stroke-width="1.4"/>'
        '<path stroke="var(--black)" stroke-width="2"/>'
        '<path stroke="var(--black)" stroke-width="3.5"/>'
        '<path stroke="var(--black)" stroke-width="5"/>'
        "</svg>"
    )
    styled = render.apply_render_style(owned_svg)
    assert 'stroke-width="1.8"' in styled
    assert styled.count('stroke-width="1.8"') == 4

    reference_svg = (
        '<svg data-origin="license-pending-s101-reference-art">'
        '<path stroke="var(--black)" stroke-width="2"/>'
        "</svg>"
    )
    assert render.apply_render_style(reference_svg) == reference_svg

    resolved = render.inject_palette(styled, day)
    assert "var(--black)" not in resolved
    assert "#070707" in resolved
    print("style contract: OK")


if __name__ == "__main__":
    main()
