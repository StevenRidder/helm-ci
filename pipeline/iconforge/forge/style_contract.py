"""Shared Helm/OpenBridge-inspired icon style contract.

The generated chart-symbol SVGs keep semantic colour tokens. This module gives
all current and future renders one visual language: OpenBridge navigation-chart
colour values, Helm's preferred blue, and a common OpenBridge-weight outline.
"""
from __future__ import annotations

import re


OPENBRIDGE_STYLE_ID = "helm-openbridge-navigation-v1"
OPENBRIDGE_STROKE_WIDTH = 1.8
HEAVY_SEMANTIC_STROKE_MIN = 8.0

OPENBRIDGE_NAV_PALETTES = {
    "day": {
        "white": "#ffffff",
        "black": "#070707",
        "red": "#f15469",
        "green": "#68e456",
        "yellow": "#f4da48",
        "blue": "#8fb5d9",
        "orange": "#eb7d36",
        "magenta": "#c545c3",
        "brown": "#b19139",
        "gray": "#7d898c",
        "ink": "#070707",
    },
    "dusk": {
        "white": "#d7d2c5",
        "black": "#14120f",
        "red": "#d65550",
        "green": "#63b565",
        "yellow": "#d3b84a",
        "blue": "#7695ab",
        "orange": "#c9793c",
        "magenta": "#a959a0",
        "brown": "#9a7c3d",
        "gray": "#777b78",
        "ink": "#14120f",
    },
    "night": {
        "white": "#b9b0a1",
        "black": "#050505",
        "red": "#8f3338",
        "green": "#3f7c43",
        "yellow": "#8c7a34",
        "blue": "#455e76",
        "orange": "#7f4a2b",
        "magenta": "#6c3f6e",
        "brown": "#66502f",
        "gray": "#4e5452",
        "ink": "#050505",
    },
}

_STROKE_WIDTH = re.compile(r'(stroke-width=")([0-9]+(?:\.[0-9]+)?)(")')
_OWNED_MARKERS = (
    'data-origin="generated-owned-artwork"',
    "data-origin='generated-owned-artwork'",
)


def is_generated_owned(svg: str) -> bool:
    return any(marker in svg for marker in _OWNED_MARKERS)


def normalize_owned_strokes(svg: str) -> str:
    """Normalize generated-owned outline strokes to OpenBridge icon weight.

    Heavy strokes are often used as filled silhouettes or safety-critical marks
    in the current symbol set, so they are preserved until a human/vision pass
    can intentionally redraw those forms. License-pending references are never
    normalized here; they remain visual witnesses.
    """
    if not is_generated_owned(svg):
        return svg

    def replace(match: re.Match[str]) -> str:
        width = float(match.group(2))
        if width >= HEAVY_SEMANTIC_STROKE_MIN:
            return match.group(0)
        return f'{match.group(1)}{OPENBRIDGE_STROKE_WIDTH:g}{match.group(3)}'

    return _STROKE_WIDTH.sub(replace, svg)
