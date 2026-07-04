"""Render (FORGE-5) — deterministic SVG -> PNG with palette substitution.

Colours live in the SVG as var(--token); a palette maps tokens to hex. One SVG
renders to day/dusk/night by substitution alone — palettes cost no generation.
cairosvg's CSS-variable support is uneven, so we resolve var(--token) ourselves
before rasterizing, which keeps the output byte-stable across environments.
"""
from __future__ import annotations

import ctypes.util
import re
from pathlib import Path

from . import style_contract

_VAR = re.compile(r"var\(--([a-z0-9_]+)\)")
_HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")
_CAIRO_LOOKUP_PATCHED = False


def _ensure_cairo_library() -> None:
    global _CAIRO_LOOKUP_PATCHED
    if _CAIRO_LOOKUP_PATCHED or ctypes.util.find_library("cairo") or not _HOMEBREW_CAIRO.exists():
        return
    original_find_library = ctypes.util.find_library

    def find_library(name: str) -> str | None:
        if name in {"cairo", "cairo-2", "libcairo-2"}:
            return str(_HOMEBREW_CAIRO)
        return original_find_library(name)

    ctypes.util.find_library = find_library
    _CAIRO_LOOKUP_PATCHED = True


def referenced_tokens(svg: str) -> set[str]:
    return set(_VAR.findall(svg))


def inject_palette(svg: str, palette: dict[str, str]) -> str:
    def sub(m):
        tok = m.group(1)
        if tok not in palette:
            raise KeyError(f"palette has no colour token '{tok}'")
        return palette[tok]
    return _VAR.sub(sub, svg)


def apply_render_style(svg: str) -> str:
    return style_contract.normalize_owned_strokes(svg)


def rasterize(svg: str, palette: dict[str, str], size: int = 128) -> bytes:
    _ensure_cairo_library()
    import cairosvg

    resolved = inject_palette(apply_render_style(svg), palette)
    return cairosvg.svg2png(bytestring=resolved.encode(),
                            output_width=size, output_height=size)
