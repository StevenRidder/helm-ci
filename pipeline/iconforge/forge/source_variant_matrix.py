"""Build Unicode-style source/provider variant sheets for Icon Forge symbols.

Each row is one Helm/S-52 asset. Columns show the canonical metadata and the
available visual variants from Helm draft art, Chart No.1 crops, Chart 1
Mappings, OpenCPN reference renders, S-101, and Commons candidates.

Run:
  python -m forge.source_variant_matrix --asset SMCFAC02 --asset BCNCAR01
"""
from __future__ import annotations

import argparse
import html
import json
import re
import urllib.request
from urllib.error import HTTPError, URLError
from pathlib import Path

import cairosvg
from PIL import Image as PilImage
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
OUT = ROOT / "out" / "source_variant_matrix"
S101_DIR = Path("/tmp/s101-audit")

PACK = CATALOG / "multisource_svg_draft_pack.json"
MASTER = CATALOG / "master_symbol_list.json"
SEMANTIC = CATALOG / "chart1_mappings_semantic_targets.json"
OPENBRIDGE = ROOT / "reference_sources" / "openbridge_webcomponents" / "manifest.json"
AQUAMAP = ROOT / "reference_sources" / "aquamap_map_symbols" / "manifest.json"

DEFAULT_ASSETS = ["SMCFAC02", "ACHARE02", "BCNCAR01", "BOYCON60", "TOPSHP92", "WRECKS04"]

PROVIDER_COLUMNS = [
    "helm_generated_draft_svg",
    "opencpn_s52_reference_render",
    "chart1_parity_reference_crop",
    "chart1_mappings_symbol_reference",
    "s101_portrayal_catalogue_svg",
    "aquamap_map_symbols",
    "wikimedia_commons_svg",
    "noto_emoji_concept",
    "openmoji_concept",
    "open_source_icon_concept",
    "openbridge_concept",
    "semantic_target",
]

STYLE_CONTRACT = {
    "format": "helm.iconforge.style_contract.v1",
    "style_id": "helm-s52-owned-svg-v1",
    "purpose": "One consistent owned SVG style for Helm chart symbols across day, dusk, and night palettes.",
    "canonical_svg": {
        "view_box": "0 0 64 64 unless the source symbol requires a non-square aspect ratio",
        "anchor": "preserve S-52 pivot/anchor semantics; center point symbols unless source metadata says otherwise",
        "colors": "use CSS variables/tokens, not baked random RGB; map to Helm day/dusk/night palettes",
        "stroke": "OpenBridge-inspired light/medium strokes; rounded joins/caps for facility and service icons; crisp joins for hazard/topmark geometry",
        "fill": "flat fills only; no gradients, shadows, texture, decorative highlights, or emoji-style rendering",
        "detail": "small-chart legibility first; remove decorative interior detail that will not survive at chart scale",
    },
    "visual_language": [
        "Owned artwork should be clean, chart-like, and S-52 compatible rather than pictorial.",
        "Use OpenBridge's calm maritime pictogram spirit as design inspiration: thinner strokes, generous negative space, simple silhouettes, and restrained detail.",
        "Preserve official silhouettes, topmarks, color order, and orientation before style polish.",
        "Magenta facility/service point symbols should normally use a thin circular enclosure so the family reads consistently; do not apply this enclosure to hazards, topmarks, buoys, beacons, wrecks, rocks, lights, or radio/radar marks when their raw shape carries navigation meaning.",
        "Facility icons may use simple pictograms or lettered circles when that is the established chart convention, but must remain compact and magenta/purple chart markers when S-52 expects that language.",
        "Buoys, beacons, cardinal marks, isolated danger marks, and topmarks are safety-critical; never alter quadrant, cone direction, or red/green/yellow/black semantics for aesthetics.",
        "Reference priority for visual design is Aqua Map map-symbol guide first, then S-101 portrayal symbols, then OpenCPN S-52 render references, with Chart 1/INT 1 and Commons/concept sources used to resolve names and alternate examples.",
        "Aqua Map, OpenCPN, S-101, Chart 1, Commons, emoji, Lucide, OpenMoji, and OpenBridge entries are references; Apache-licensed OpenBridge files may inform style and implementation after provenance tagging, while copyrighted/GPL/license-pending sources remain reference-only unless cleared.",
    ],
    "llm_generation_order": [
        "Read official S-57/S-52/S-101 semantics and safety notes first.",
        "Use Aqua Map as the first visual guide when it has the symbol; use S-101 next for exact chart-symbol geometry; use OpenCPN after that to resolve S-52 compatibility.",
        "Use emoji/open-source concepts only to understand generic primitives such as anchor, shower, trash, triangle, square, or circle.",
        "Render one canonical SVG in the Helm style contract, then render day/dusk/night using palette variables.",
        "Run deterministic structural checks, sibling discrimination, and visual parity checks before accepting.",
    ],
    "rejection_rules": [
        "Reject if a cardinal/topmark orientation changes meaning.",
        "Reject if red/green/yellow/black safety colours are swapped or omitted.",
        "Reject if the SVG looks like a direct trace/import of restricted reference art.",
        "Reject if the symbol is illegible at small chart scale.",
        "Reject if day/dusk/night palettes do not share the same geometry.",
    ],
}

CONCEPT_VARIANTS = {
    "SMCFAC02": [
        {
            "source": "noto_emoji_concept",
            "label": "sailboat / marina concept",
            "status": "open_reference_concept_needs_review",
            "url": "https://raw.githubusercontent.com/googlefonts/noto-emoji/main/svg/emoji_u26f5.svg",
            "license_status": "Noto Emoji open-source reference; verify exact asset license before reuse",
        },
        {
            "source": "openmoji_concept",
            "label": "OpenMoji sailboat concept",
            "status": "cc_by_sa_reference_concept_needs_counsel_review",
            "url": "https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/color/svg/26F5.svg",
            "license_status": "OpenMoji CC BY-SA; reference/concept only until counsel approves reuse terms",
        },
        {
            "source": "open_source_icon_concept",
            "label": "Lucide sailboat concept",
            "status": "permissive_icon_reference_needs_chart_semantic_review",
            "url": "https://raw.githubusercontent.com/lucide-icons/lucide/main/icons/sailboat.svg",
            "license_status": "Lucide ISC/MIT-style permissive source; keep as concept/reference until counsel intake",
        },
        {
            "source": "openbridge_concept",
            "label": "OpenBridge maritime icon set - marina/harbour concept search",
            "status": "open_reference_concept_needs_intake",
            "url": "https://www.openbridge.no/cases/openbridge-icons",
            "license_status": "OpenBridge appears relevant; perform per-asset/license intake before artwork use",
        },
    ],
    "ACHARE02": [
        {
            "source": "noto_emoji_concept",
            "label": "anchor concept",
            "status": "open_reference_concept_needs_review",
            "url": "https://raw.githubusercontent.com/googlefonts/noto-emoji/main/svg/emoji_u2693.svg",
            "license_status": "Noto Emoji open-source reference; verify exact asset license before reuse",
        },
        {
            "source": "openmoji_concept",
            "label": "OpenMoji anchor concept",
            "status": "cc_by_sa_reference_concept_needs_counsel_review",
            "url": "https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/color/svg/2693.svg",
            "license_status": "OpenMoji CC BY-SA; reference/concept only until counsel approves reuse terms",
        },
        {
            "source": "open_source_icon_concept",
            "label": "Lucide anchor concept",
            "status": "permissive_icon_reference_needs_chart_semantic_review",
            "url": "https://raw.githubusercontent.com/lucide-icons/lucide/main/icons/anchor.svg",
            "license_status": "Lucide ISC/MIT-style permissive source; keep as concept/reference until counsel intake",
        },
    ],
    "BCNCAR01": [
        {
            "source": "noto_emoji_concept",
            "label": "yellow triangle primitive concept",
            "status": "open_reference_primitive_for_colour_shape_only",
            "url": "https://raw.githubusercontent.com/googlefonts/noto-emoji/main/svg/emoji_u26a0.svg",
            "license_status": "Noto Emoji open-source reference; use only as primitive shape/colour cue",
        },
        {
            "source": "openmoji_concept",
            "label": "OpenMoji yellow triangle primitive",
            "status": "cc_by_sa_reference_primitive_needs_counsel_review",
            "url": "https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/color/svg/26A0.svg",
            "license_status": "OpenMoji CC BY-SA; reference/concept only until counsel approves reuse terms",
        },
        {
            "source": "noto_emoji_concept",
            "label": "black circle primitive concept",
            "status": "open_reference_primitive_for_colour_shape_only",
            "url": "https://raw.githubusercontent.com/googlefonts/noto-emoji/main/svg/emoji_u26ab.svg",
            "license_status": "Noto Emoji open-source reference; use only as primitive shape/colour cue",
        },
    ],
    "BOYCON60": [
        {
            "source": "noto_emoji_concept",
            "label": "red upward triangle primitive concept",
            "status": "open_reference_primitive_for_colour_shape_only",
            "url": "https://raw.githubusercontent.com/googlefonts/noto-emoji/main/svg/emoji_u1f53a.svg",
            "license_status": "Noto Emoji open-source reference; use only as primitive shape/colour cue",
        },
        {
            "source": "openmoji_concept",
            "label": "OpenMoji red upward triangle primitive",
            "status": "cc_by_sa_reference_primitive_needs_counsel_review",
            "url": "https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/color/svg/1F53A.svg",
            "license_status": "OpenMoji CC BY-SA; reference/concept only until counsel approves reuse terms",
        },
        {
            "source": "noto_emoji_concept",
            "label": "red circle primitive concept",
            "status": "open_reference_primitive_for_colour_shape_only",
            "url": "https://raw.githubusercontent.com/googlefonts/noto-emoji/main/svg/emoji_u1f534.svg",
            "license_status": "Noto Emoji open-source reference; use only as primitive shape/colour cue",
        },
    ],
    "TOPSHP92": [
        {
            "source": "noto_emoji_concept",
            "label": "red square primitive concept",
            "status": "open_reference_primitive_for_colour_shape_only",
            "url": "https://raw.githubusercontent.com/googlefonts/noto-emoji/main/svg/emoji_u1f7e5.svg",
            "license_status": "Noto Emoji open-source reference; use only as primitive shape/colour cue",
        },
        {
            "source": "openmoji_concept",
            "label": "OpenMoji red square primitive",
            "status": "cc_by_sa_reference_primitive_needs_counsel_review",
            "url": "https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/color/svg/1F7E5.svg",
            "license_status": "OpenMoji CC BY-SA; reference/concept only until counsel approves reuse terms",
        },
        {
            "source": "noto_emoji_concept",
            "label": "white square primitive concept",
            "status": "open_reference_primitive_for_colour_shape_only",
            "url": "https://raw.githubusercontent.com/googlefonts/noto-emoji/main/svg/emoji_u2b1c.svg",
            "license_status": "Noto Emoji open-source reference; use only as primitive shape/colour cue",
        },
    ],
    "SMCFAC_CATSCF_12": [
        {
            "source": "noto_emoji_concept",
            "label": "potable water / water tap concept",
            "status": "open_reference_concept_needs_review",
            "url": "https://raw.githubusercontent.com/googlefonts/noto-emoji/main/svg/emoji_u1f6b0.svg",
            "license_status": "Noto Emoji open-source reference; verify exact asset license before reuse",
        },
        {
            "source": "openmoji_concept",
            "label": "OpenMoji potable water concept",
            "status": "cc_by_sa_reference_concept_needs_counsel_review",
            "url": "https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/color/svg/1F6B0.svg",
            "license_status": "OpenMoji CC BY-SA; reference/concept only until counsel approves reuse terms",
        },
        {
            "source": "open_source_icon_concept",
            "label": "Lucide droplet / water concept",
            "status": "permissive_icon_reference_needs_chart_semantic_review",
            "url": "https://raw.githubusercontent.com/lucide-icons/lucide/main/icons/droplet.svg",
            "license_status": "Lucide ISC/MIT-style permissive source; keep as concept/reference until counsel intake",
        },
    ],
    "SMCFAC_CATSCF_16": [
        {
            "source": "noto_emoji_concept",
            "label": "shower concept",
            "status": "open_reference_concept_needs_review",
            "url": "https://raw.githubusercontent.com/googlefonts/noto-emoji/main/svg/emoji_u1f6bf.svg",
            "license_status": "Noto Emoji open-source reference; verify exact asset license before reuse",
        },
        {
            "source": "openmoji_concept",
            "label": "OpenMoji shower concept",
            "status": "cc_by_sa_reference_concept_needs_counsel_review",
            "url": "https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/color/svg/1F6BF.svg",
            "license_status": "OpenMoji CC BY-SA; reference/concept only until counsel approves reuse terms",
        },
        {
            "source": "open_source_icon_concept",
            "label": "Lucide shower head concept",
            "status": "permissive_icon_reference_needs_chart_semantic_review",
            "url": "https://raw.githubusercontent.com/lucide-icons/lucide/main/icons/shower-head.svg",
            "license_status": "Lucide ISC/MIT-style permissive source; keep as concept/reference until counsel intake",
        },
        {
            "source": "openbridge_concept",
            "label": "OpenBridge maritime/industrial facilities icon concept search",
            "status": "open_reference_concept_needs_intake",
            "url": "https://www.openbridge.no/",
            "license_status": "OpenBridge appears relevant; perform per-asset/license intake before artwork use",
        },
    ],
    "SMCFAC_CATSCF_21": [
        {
            "source": "noto_emoji_concept",
            "label": "wastebasket / refuse bin concept",
            "status": "open_reference_concept_needs_review",
            "url": "https://raw.githubusercontent.com/googlefonts/noto-emoji/main/svg/emoji_u1f5d1.svg",
            "license_status": "Noto Emoji open-source reference; verify exact asset license before reuse",
        },
        {
            "source": "openmoji_concept",
            "label": "OpenMoji wastebasket concept",
            "status": "cc_by_sa_reference_concept_needs_counsel_review",
            "url": "https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/color/svg/1F5D1.svg",
            "license_status": "OpenMoji CC BY-SA; reference/concept only until counsel approves reuse terms",
        },
        {
            "source": "open_source_icon_concept",
            "label": "Lucide trash concept",
            "status": "permissive_icon_reference_needs_chart_semantic_review",
            "url": "https://raw.githubusercontent.com/lucide-icons/lucide/main/icons/trash-2.svg",
            "license_status": "Lucide ISC/MIT-style permissive source; keep as concept/reference until counsel intake",
        },
    ],
}

CONDITION_LABELS = {
    "BOYSHP1": "conical buoy body",
    "CATCAM1": "north cardinal mark",
    "CATHAF5": "yacht harbour / marina",
    "CATSCF=12": "water tap",
    "CATSCF=16": "showers",
    "CATSCF=21": "refuse bin",
    "COLPAT2": "vertical stripe colour pattern",
    "COLOUR1": "white",
    "COLOUR2": "black",
    "COLOUR3": "red",
    "COLOUR4": "green",
    "COLOUR5": "blue",
    "COLOUR6": "yellow",
    "COLOUR7": "grey",
    "COLOUR8": "brown",
    "COLOUR11": "orange",
    "TOPSHP21": "rectangular topmark",
}

SAFETY_KEYWORDS = {
    "BCNCAR": "Preserve cardinal orientation and black/yellow topmark semantics; wrong cone direction is a navigation hazard.",
    "BOYLAT": "Preserve lateral colour and buoy shape; wrong red/green or shape can invert channel-side meaning.",
    "DAYMAR": "Preserve topmark silhouette and colour pattern; do not render as a light flare.",
}

COLOUR_LABELS = {
    "1": "white",
    "2": "black",
    "3": "red",
    "4": "green",
    "5": "blue",
    "6": "yellow",
    "7": "grey",
    "8": "brown",
    "9": "amber",
    "10": "violet",
    "11": "orange",
    "12": "magenta",
}

COLPAT_LABELS = {
    "1": "horizontal stripe colour pattern",
    "2": "vertical stripe colour pattern",
    "3": "diagonal stripe colour pattern",
    "4": "squared/checkered colour pattern",
    "5": "border stripe colour pattern",
    "6": "cross stripe colour pattern",
}

BOY_SHAPE_LABELS = {
    "1": "conical buoy body",
    "2": "can buoy body",
    "3": "spherical buoy body",
    "4": "pillar buoy body",
    "5": "spar buoy body",
    "6": "barrel buoy body",
    "7": "super-buoy body",
}

BCN_SHAPE_LABELS = {
    "1": "stake or pole beacon",
    "2": "withy beacon",
    "3": "beacon tower",
    "4": "lattice beacon",
    "5": "beacon pile",
    "6": "cairn beacon",
    "7": "buoyant beacon",
}

CARDINAL_LABELS = {
    "1": "north cardinal mark",
    "2": "east cardinal mark",
    "3": "south cardinal mark",
    "4": "west cardinal mark",
}

NOTO_EMOJI_LICENSE = "Noto Emoji SIL OFL reference; use as concept/primitive cue unless exact reuse is approved"
OPENMOJI_LICENSE = "OpenMoji CC BY-SA; reference/concept only until counsel approves reuse terms"
LUCIDE_LICENSE = "Lucide ISC/MIT-style permissive source; keep as concept/reference until counsel intake"

EMOJI_CODES = {
    "anchor": {"noto": "2693", "openmoji": "2693"},
    "sailboat": {"noto": "26f5", "openmoji": "26F5"},
    "water": {"noto": "1f6b0", "openmoji": "1F6B0"},
    "shower": {"noto": "1f6bf", "openmoji": "1F6BF"},
    "trash": {"noto": "1f5d1", "openmoji": "1F5D1"},
    "warning": {"noto": "26a0", "openmoji": "26A0"},
    "airplane": {"noto": "2708", "openmoji": "2708"},
    "radio": {"noto": "1f4fb", "openmoji": "1F4FB"},
    "hospital": {"noto": "1f3e5", "openmoji": "1F3E5"},
    "fuel": {"noto": "26fd", "openmoji": "26FD"},
    "mail": {"noto": "1f4ee", "openmoji": "1F4EE"},
    "telephone": {"noto": "260e", "openmoji": "260E"},
}

EMOJI_PRIMITIVES = {
    ("red", "circle"): {"noto": "1f534", "openmoji": "1F534"},
    ("green", "circle"): {"noto": "1f7e2", "openmoji": "1F7E2"},
    ("blue", "circle"): {"noto": "1f535", "openmoji": "1F535"},
    ("yellow", "circle"): {"noto": "1f7e1", "openmoji": "1F7E1"},
    ("black", "circle"): {"noto": "26ab", "openmoji": "26AB"},
    ("white", "circle"): {"noto": "26aa", "openmoji": "26AA"},
    ("brown", "circle"): {"noto": "1f7e4", "openmoji": "1F7E4"},
    ("orange", "circle"): {"noto": "1f7e0", "openmoji": "1F7E0"},
    ("red", "square"): {"noto": "1f7e5", "openmoji": "1F7E5"},
    ("green", "square"): {"noto": "1f7e9", "openmoji": "1F7E9"},
    ("blue", "square"): {"noto": "1f7e6", "openmoji": "1F7E6"},
    ("yellow", "square"): {"noto": "1f7e8", "openmoji": "1F7E8"},
    ("black", "square"): {"noto": "2b1b", "openmoji": "2B1B"},
    ("white", "square"): {"noto": "2b1c", "openmoji": "2B1C"},
    ("brown", "square"): {"noto": "1f7eb", "openmoji": "1F7EB"},
    ("orange", "square"): {"noto": "1f7e7", "openmoji": "1F7E7"},
    ("red", "triangle"): {"noto": "1f53a", "openmoji": "1F53A"},
    ("yellow", "triangle"): {"noto": "26a0", "openmoji": "26A0"},
    ("black", "triangle"): {"noto": "25b6", "openmoji": "25B6"},
}

LUCIDE_ICONS = {
    "anchor": "anchor",
    "sailboat": "sailboat",
    "water": "droplet",
    "shower": "shower-head",
    "trash": "trash-2",
    "warning": "triangle-alert",
    "airplane": "plane",
    "radio": "radio",
    "hospital": "hospital",
    "fuel": "fuel",
    "mail": "mailbox",
    "telephone": "phone",
    "circle": "circle",
    "square": "square",
    "triangle": "triangle",
}

OPENBRIDGE_CONCEPT_RULES = [
    ("anchor", ("anchor", "anchorage"), ["anchor-iec", "anchorwatch"]),
    ("harbour", ("harbour", "harbor", "berthing"), ["harbour-berthing"]),
    ("pilot", ("pilot", "pilotage"), ["pilotage", "pilot-onboard"]),
    ("water", ("water tap", "potable water", "drinking water"), ["water-google", "sensor-water-drop-google"]),
    ("shower", ("shower",), ["heavy-rain-showers-day", "light-rain-showers-day"]),
    ("wreck", ("wreck",), ["ship-wreck-iec", "ship-wreck-filled"]),
    ("rock", ("rock",), ["rock"]),
    ("safe_water", ("safe water",), ["simplified-beacon-major-safe-water", "simplified-buoy-safe-water"]),
    ("buoy_can", ("can buoy", "can shape"), ["buoy-can-board", "buoy-can-cone-up", "buoy-can-sphere"]),
    ("buoy_barrel", ("barrel buoy",), ["buoy-barrel-board", "buoy-barrel-sphere"]),
    ("buoy", ("buoy",), ["simplified-buoy-safe-water", "buoy-can-board"]),
    ("beacon", ("beacon",), ["simplified-beacon-major-safe-water", "simplified-beacon-minor-safe-water"]),
    ("radio", ("radio", "radar"), ["radio-button", "radio-button-selected"]),
]

_OPENBRIDGE_CACHE: dict[str, dict] | None = None

AQUAMAP_ASSET_REFERENCES = {
    "SMCFAC02": ["Marina1"],
    "MORFAC03": ["Piles1", "Mooring1"],
    "MORFAC04": ["Piles1", "Mooring1"],
    "BOYMOR03": ["Mooring1"],
    "BCNSAW13": ["BCNSAW1", "BOYSAW1"],
    "LIGHTS05": ["LIGHTSM11", "LIGHTSY11", "LIGHTSW11", "LIGHTSR11", "LIGHTSG11"],
    "FOGSIG01": ["BELL1"],
    "RADRFL03": ["RadarReflector1"],
    "RDOCAL03": ["RadioCallinPoint1"],
    "RDOSTA02": ["RadioCallinPoint1"],
    "WRECKS04": ["SubmergedWreck1", "DangerousWreck1", "EmergedWreck1"],
    "UWTROC04": ["SubmergedRock11", "DangerousRock11", "EmergedRock11"],
}

_AQUAMAP_CACHE: dict[str, dict] | None = None


def _read(path: Path) -> dict:
    return json.loads(path.read_text())


def _openbridge_by_id() -> dict[str, dict]:
    global _OPENBRIDGE_CACHE
    if _OPENBRIDGE_CACHE is not None:
        return _OPENBRIDGE_CACHE
    if not OPENBRIDGE.exists():
        _OPENBRIDGE_CACHE = {}
        return _OPENBRIDGE_CACHE
    manifest = _read(OPENBRIDGE)
    base = OPENBRIDGE.parent
    _OPENBRIDGE_CACHE = {
        icon["id"]: {**icon, "path": str((base / icon["local_svg"]).relative_to(ROOT))}
        for icon in manifest.get("icons", [])
        if icon.get("local_svg")
    }
    return _OPENBRIDGE_CACHE


def _aquamap_by_id() -> dict[str, dict]:
    global _AQUAMAP_CACHE
    if _AQUAMAP_CACHE is not None:
        return _AQUAMAP_CACHE
    if not AQUAMAP.exists():
        _AQUAMAP_CACHE = {}
        return _AQUAMAP_CACHE
    manifest = _read(AQUAMAP)
    base = AQUAMAP.parent
    _AQUAMAP_CACHE = {
        entry["id"]: {**entry, "path": str((base / entry["local_image"]).relative_to(ROOT))}
        for entry in manifest.get("entries", [])
        if entry.get("local_image")
    }
    return _AQUAMAP_CACHE


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text)


def _rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _resolve_local(path: str | None) -> Path | None:
    if not path:
        return None
    candidate = Path(path)
    if candidate.is_absolute() and candidate.exists():
        return candidate
    for base in (ROOT, S101_DIR):
        full = base / path
        if full.exists():
            return full
    return None


def _render_svg(svg: Path, png: Path) -> Path | None:
    if not svg.exists():
        return None
    png.parent.mkdir(parents=True, exist_ok=True)
    if not png.exists() or png.stat().st_mtime < svg.stat().st_mtime:
        cairosvg.svg2png(url=str(svg), write_to=str(png), output_width=96, output_height=96)
    return png


def _inline_s101_svg(svg: Path) -> Path:
    css = svg.parent / "daySvgStyle.css"
    if not css.exists():
        return svg
    target = OUT / "cache" / "s101_inline" / svg.name
    target.parent.mkdir(parents=True, exist_ok=True)
    text = svg.read_text()
    text = re.sub(r'<\?xml-stylesheet[^>]+\?>\s*', "", text)
    style = f"<style><![CDATA[\n{css.read_text()}\n]]></style>"
    text, replacements = re.subn(r"(<svg\b[^>]*>)", r"\1\n" + style, text, count=1)
    if replacements != 1:
        raise ValueError(f"could not inline S-101 CSS for {svg}")
    target.write_text(text)
    return target


def _copy_png(source: Path, target: Path) -> Path | None:
    if not source.exists():
        return None
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists() or target.stat().st_mtime < source.stat().st_mtime:
        with PilImage.open(source) as image:
            image.thumbnail((128, 96), PilImage.Resampling.LANCZOS)
            image.save(target)
    return target


def _download_and_render_svg(url: str, png: Path) -> Path | None:
    svg_path = OUT / "cache" / (_safe(Path(url).name) or f"{_safe(url)}.svg")
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    if not svg_path.exists():
        req = urllib.request.Request(url, headers={"User-Agent": "HelmIconForgeVariantMatrix/0.1"})
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                svg_path.write_bytes(response.read())
        except (HTTPError, URLError, TimeoutError):
            return None
    return _render_svg(svg_path, png)


def _example_label(example: dict) -> str:
    return (
        example.get("label")
        or example.get("official_name")
        or example.get("title")
        or example.get("symbol_id")
        or example.get("asset_description")
        or example.get("source")
        or ""
    )


def _provider_entry(asset: str, provider: str, example: dict, index: int) -> dict:
    label = _example_label(example)
    status = example.get("status") or example.get("role") or ""
    path = example.get("path")
    url = example.get("url")
    image_path = None
    source_path = None

    if provider == "helm_generated_draft_svg":
        day_render = ROOT / "out" / "multisource_svg_draft" / "renders" / f"{asset}__day.png"
        if day_render.exists():
            image_path = _copy_png(day_render, OUT / "renders" / asset / f"{provider}_{index}.png")
        else:
            source = _resolve_local(path)
            if source:
                image_path = _render_svg(source, OUT / "renders" / asset / f"{provider}_{index}.png")
                source_path = source
    elif provider == "opencpn_s52_reference_render":
        palette_paths = example.get("paths") or {}
        source = _resolve_local(palette_paths.get("day"))
        if not source:
            source = ROOT / "out" / "opencpn_s52_reference" / f"{asset}__day.png"
        if source and source.exists():
            image_path = _copy_png(source, OUT / "renders" / asset / f"{provider}_{index}.png")
            source_path = source
            if status == "pending_render":
                status = "rendered_reference"
    elif provider in {"chart1_parity_reference_crop", "chart1_mappings_symbol_reference"}:
        source = _resolve_local(path)
        if source:
            image_path = _copy_png(source, OUT / "renders" / asset / f"{provider}_{index}.png")
            source_path = source
    elif provider == "s101_portrayal_catalogue_svg":
        source = _resolve_local(path)
        if source:
            image_path = _render_svg(_inline_s101_svg(source), OUT / "renders" / asset / f"{provider}_{index}.png")
            source_path = source
    elif provider == "aquamap_map_symbols":
        source = _resolve_local(path)
        if source:
            image_path = _copy_png(source, OUT / "renders" / asset / f"{provider}_{index}.png")
            source_path = source
    elif provider == "openbridge_concept":
        source = _resolve_local(path)
        if source:
            image_path = _render_svg(source, OUT / "renders" / asset / f"{provider}_{index}.png")
            source_path = source
    elif provider in {"wikimedia_commons_svg", "noto_emoji_concept", "openmoji_concept", "open_source_icon_concept"} and url:
        image_path = _download_and_render_svg(url, OUT / "renders" / asset / f"{provider}_{index}.png")

    return {
        "provider": provider,
        "label": label,
        "status": status,
        "source_path": _rel(source_path) if source_path else path,
        "url": url,
        "image": _rel(image_path) if image_path else None,
        "metadata": {
            key: value
            for key, value in example.items()
            if key not in {"source", "path", "url", "description_url"}
        },
    }


def _semantic_examples(asset: str, semantic: dict) -> list[dict]:
    rows = []
    for target in semantic.get("targets", []):
        target_asset = target.get("generation_target", {}).get("asset_id")
        if target_asset == asset:
            rows.append({
                "source": "semantic_target",
                "role": "generator_target_without_canonical_art",
                "status": target.get("source_table", {}).get("symbol_cell_status"),
                "official_name": target["official_name"],
                "s57_refs": target["s57_refs"],
                "expected_symbol": target["generation_target"]["expected_symbol"],
                "visual_brief": target["generation_target"]["visual_brief"],
            })
    return rows


def _semantic_by_asset(semantic: dict) -> dict[str, dict]:
    return {
        target["generation_target"]["asset_id"]: target
        for target in semantic.get("targets", [])
    }


def _noto_url(code: str) -> str:
    return f"https://raw.githubusercontent.com/googlefonts/noto-emoji/main/svg/emoji_u{code.lower()}.svg"


def _openmoji_url(code: str) -> str:
    return f"https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/color/svg/{code.upper()}.svg"


def _lucide_url(icon: str) -> str:
    return f"https://raw.githubusercontent.com/lucide-icons/lucide/main/icons/{icon}.svg"


def _concept_entry(source: str, key: str, label: str, status: str, url: str, license_status: str, reason: str) -> dict:
    return {
        "source": source,
        "label": label,
        "status": status,
        "url": url,
        "license_status": license_status,
        "match_reason": reason,
        "concept_key": key,
    }


def _emoji_concept_entries(key: str, label: str, reason: str, *, status: str = "auto_reference_concept_needs_review") -> list[dict]:
    codes = EMOJI_CODES.get(key)
    if not codes:
        return []
    return [
        _concept_entry("noto_emoji_concept", key, f"Noto {label}", status, _noto_url(codes["noto"]), NOTO_EMOJI_LICENSE, reason),
        _concept_entry("openmoji_concept", key, f"OpenMoji {label}", "cc_by_sa_reference_concept_needs_counsel_review", _openmoji_url(codes["openmoji"]), OPENMOJI_LICENSE, reason),
    ]


def _primitive_concept_entries(colour: str, shape: str, reason: str) -> list[dict]:
    codes = EMOJI_PRIMITIVES.get((colour, shape))
    if not codes:
        return []
    label = f"{colour} {shape} primitive"
    return [
        _concept_entry("noto_emoji_concept", f"{colour}_{shape}", f"Noto {label}", "auto_reference_primitive_for_colour_shape_only", _noto_url(codes["noto"]), NOTO_EMOJI_LICENSE, reason),
        _concept_entry("openmoji_concept", f"{colour}_{shape}", f"OpenMoji {label}", "cc_by_sa_reference_primitive_needs_counsel_review", _openmoji_url(codes["openmoji"]), OPENMOJI_LICENSE, reason),
    ]


def _lucide_concept_entry(key: str, label: str, reason: str) -> list[dict]:
    icon = LUCIDE_ICONS.get(key)
    if not icon:
        return []
    return [
        _concept_entry(
            "open_source_icon_concept",
            key,
            f"Lucide {label}",
            "auto_permissive_icon_reference_needs_chart_semantic_review",
            _lucide_url(icon),
            LUCIDE_LICENSE,
            reason,
        )
    ]


def _openbridge_concept_entry(key: str, label: str, reason: str) -> list[dict]:
    return [
        {
            "source": "openbridge_concept",
            "label": f"OpenBridge {label} concept intake",
            "status": "open_reference_concept_needs_intake",
            "url": "https://openbridge-jip-storybook.web.app/?path=/docs/introduction-introduction--docs",
            "description_url": "https://github.com/Ocean-Industries-Concept-Lab/openbridge-webcomponents",
            "license_status": "OpenBridge webcomponents/storybook source; perform per-version and per-asset license intake before artwork use",
            "match_reason": reason,
            "concept_key": key,
        }
    ]


def _openbridge_local_entries(search_text: str, reason_prefix: str) -> list[dict]:
    icons = _openbridge_by_id()
    if not icons:
        return []
    entries = []
    seen = set()
    for key, needles, icon_ids in OPENBRIDGE_CONCEPT_RULES:
        if not any(needle in search_text for needle in needles):
            continue
        for icon_id in icon_ids:
            icon = icons.get(icon_id)
            if not icon or icon_id in seen:
                continue
            seen.add(icon_id)
            entries.append({
                "source": "openbridge_concept",
                "label": f"OpenBridge {icon_id}",
                "status": "apache_2_openbridge_reference",
                "path": icon["path"],
                "url": f"https://github.com/Ocean-Industries-Concept-Lab/openbridge-webcomponents/tree/develop/{icon['source_path']}",
                "description_url": "https://openbridge-jip-storybook.web.app/?path=/docs/icons-icon--docs",
                "license_status": "Apache-2.0 OpenBridge webcomponents reference; keep provenance if reused",
                "match_reason": f"{reason_prefix}: {key}",
                "concept_key": key,
            })
    return entries


def _aquamap_reference_entries(asset: str) -> list[dict]:
    icons = _aquamap_by_id()
    if not icons:
        return []
    entries = []
    for icon_id in AQUAMAP_ASSET_REFERENCES.get(asset, []):
        icon = icons.get(icon_id)
        if not icon:
            continue
        entries.append({
            "source": "aquamap_map_symbols",
            "label": f"Aqua Map {icon.get('label') or icon_id}",
            "status": "copyrighted_visual_reference_not_canonical_art",
            "path": icon["path"],
            "url": icon.get("source_url"),
            "description_url": "https://www.aquamap.app/support/15-basic/24-map-symbols",
            "license_status": "Aqua Map support-page raster reference; use for visual guidance only, do not import pixels into canonical SVG",
            "match_reason": "Aqua Map filename mapped to this S-57/S-52 asset",
            "concept_key": "explicit_asset_map",
            "section": icon.get("section"),
        })
    return entries


def _row_search_text(asset: str, symbol: dict | None, master_row: dict | None, semantic_target: dict | None) -> str:
    parts = [
        asset,
        (symbol or {}).get("name"),
        (master_row or {}).get("description"),
        (master_row or {}).get("s57_object_class"),
        (master_row or {}).get("s101_feature_rule"),
        (master_row or {}).get("family"),
        (semantic_target or {}).get("official_name"),
        (semantic_target or {}).get("generation_target", {}).get("visual_brief"),
    ]
    parts.extend((master_row or {}).get("s57_conditions", []))
    return " ".join(str(part) for part in parts if part).lower()


def _colour_numbers(conditions: list[str]) -> list[str]:
    numbers = []
    for condition in conditions:
        if not condition.startswith("COLOUR"):
            continue
        numbers.extend(re.findall(r"\d+", condition[len("COLOUR"):]))
    return numbers


def _shape_candidates(asset: str, search_text: str, conditions: list[str]) -> list[str]:
    shapes = []
    if any(token.startswith("BOYSHP1") for token in conditions) or "conical" in search_text:
        shapes.append("triangle")
    if any(token.startswith("BOYSHP2") for token in conditions) or "can buoy" in search_text:
        shapes.append("square")
    if any(token.startswith("BOYSHP3") for token in conditions) or "spherical" in search_text:
        shapes.append("circle")
    if "topmark" in search_text or any(token.startswith("TOPSHP") for token in conditions):
        shapes.append("square")
    if "cardinal" in search_text or asset.startswith(("BCNCAR", "BOYCAR")):
        shapes.extend(["triangle", "circle"])
    if not shapes and any(token.startswith("COLOUR") for token in conditions):
        shapes.append("circle")
    return list(dict.fromkeys(shapes))


def _auto_concept_examples(asset: str, symbol: dict | None, master_row: dict | None, semantic_target: dict | None) -> list[dict]:
    examples: list[dict] = []
    search_text = _row_search_text(asset, symbol, master_row, semantic_target)
    conditions = (master_row or {}).get("s57_conditions", [])
    examples.extend(_aquamap_reference_entries(asset))
    examples.extend(_openbridge_local_entries(search_text, "OpenBridge local icon keyword match"))
    semantic_map = [
        ("anchor", ("anchor", "anchorage"), "anchor"),
        ("sailboat", ("marina", "yacht", "harbour facility", "harbor facility"), "sailboat / marina"),
        ("water", ("water tap", "potable water", "drinking water"), "water tap"),
        ("shower", ("shower",), "shower"),
        ("trash", ("refuse", "trash", "waste", "garbage"), "refuse bin"),
        ("airplane", ("airport", "airfield"), "airplane"),
        ("radio", ("radio", "radar", "communication"), "radio"),
        ("hospital", ("hospital", "medical", "health"), "hospital"),
        ("fuel", ("fuel", "bunker"), "fuel"),
        ("mail", ("postbox", "post box", "mail"), "mailbox"),
        ("telephone", ("telephone", "phone"), "telephone"),
        ("warning", ("danger", "caution", "prohibited", "restricted"), "warning"),
    ]
    for key, needles, label in semantic_map:
        if any(needle in search_text for needle in needles):
            reason = f"semantic keyword match: {label}"
            examples.extend(_emoji_concept_entries(key, label, reason))
            examples.extend(_lucide_concept_entry(key, label, reason))
            if key in {"sailboat", "shower", "water", "warning", "radio"}:
                examples.extend(_openbridge_concept_entry(key, label, reason))

    colours = [COLOUR_LABELS[number] for number in _colour_numbers(conditions) if number in COLOUR_LABELS]
    shapes = _shape_candidates(asset, search_text, conditions)
    for colour in colours[:3]:
        for shape in shapes[:2]:
            examples.extend(_primitive_concept_entries(colour, shape, f"S-57 colour/shape condition: {colour} {shape}"))
    if "cardinal" in search_text and "yellow" not in colours:
        examples.extend(_primitive_concept_entries("yellow", "triangle", "cardinal mark primitive cue"))
        examples.extend(_primitive_concept_entries("black", "circle", "cardinal mark primitive cue"))

    deduped = []
    seen = set()
    for example in examples:
        key = (example.get("source"), example.get("url") or example.get("label"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(example)
    return deduped


def _concept_examples(asset: str, symbol: dict | None, master_row: dict | None, semantic_target: dict | None) -> list[dict]:
    examples = list(CONCEPT_VARIANTS.get(asset, []))
    examples.extend(_auto_concept_examples(asset, symbol, master_row, semantic_target))
    deduped = []
    seen = set()
    for example in examples:
        key = (example.get("source"), example.get("url") or example.get("label"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(example)
    return deduped


def _parse_semantic_s57(target: dict | None) -> dict:
    if not target:
        return {"object_class": None, "conditions": [], "instruction": None}
    refs = target.get("s57_refs") or []
    if not refs:
        return {"object_class": None, "conditions": [], "instruction": None}
    first = refs[0]
    parts = first.split(".")
    return {
        "object_class": parts[0],
        "conditions": parts[1:],
        "instruction": None,
    }


def _condition_labels(conditions: list[str]) -> list[str]:
    labels = []
    for condition in conditions:
        if condition.startswith("COLOUR"):
            colours = [COLOUR_LABELS.get(number, number) for number in re.findall(r"\d+", condition[len("COLOUR"):])]
            labels.append(", ".join(colours) if colours else condition)
        elif condition.startswith("COLPAT"):
            numbers = re.findall(r"\d+", condition[len("COLPAT"):])
            labels.append(", ".join(COLPAT_LABELS.get(number, number) for number in numbers) if numbers else condition)
        elif condition.startswith("BOYSHP"):
            numbers = re.findall(r"\d+", condition[len("BOYSHP"):])
            labels.append(", ".join(BOY_SHAPE_LABELS.get(number, number) for number in numbers) if numbers else condition)
        elif condition.startswith("BCNSHP"):
            numbers = re.findall(r"\d+", condition[len("BCNSHP"):])
            labels.append(", ".join(BCN_SHAPE_LABELS.get(number, number) for number in numbers) if numbers else condition)
        elif condition.startswith("CATCAM"):
            numbers = re.findall(r"\d+", condition[len("CATCAM"):])
            labels.append(", ".join(CARDINAL_LABELS.get(number, number) for number in numbers) if numbers else condition)
        else:
            labels.append(CONDITION_LABELS.get(condition, condition))
    return labels


def _brief_caption(asset: str, name: str, object_class: str | None, conditions: list[str], semantic_target: dict | None) -> str:
    if semantic_target:
        return semantic_target["generation_target"].get("visual_brief") or semantic_target.get("official_name") or name
    tokens = _condition_labels(conditions)
    pieces = [name or asset]
    if object_class:
        pieces.append(object_class)
    pieces.extend(tokens[:4])
    return "; ".join(piece for piece in pieces if piece)


def _build_visual_brief(asset: str, name: str, master_row: dict | None, semantic_target: dict | None, source_refs: dict, providers: dict) -> dict:
    object_class = (master_row or {}).get("s57_object_class")
    conditions = (master_row or {}).get("s57_conditions", [])
    if semantic_target:
        semantic_s57 = _parse_semantic_s57(semantic_target)
        object_class = object_class or semantic_s57["object_class"]
        conditions = conditions or semantic_s57["conditions"]
    reference_columns = [
        provider
        for provider, entries in providers.items()
        if entries and provider != "semantic_target"
    ]
    source_examples = {
        provider: [
            {
                "label": entry.get("label"),
                "status": entry.get("status"),
                "image": entry.get("image"),
                "source_path": entry.get("source_path"),
                "url": entry.get("url"),
            }
            for entry in entries[:3]
        ]
        for provider, entries in providers.items()
        if entries
    }
    safety_note = SAFETY_KEYWORDS.get(object_class, "Preserve official S-57/S-52 semantics; do not simplify away colour, orientation, or topmark cues.")
    return {
        "format": "helm.iconforge.visual_brief.v1",
        "asset": asset,
        "style_contract_id": STYLE_CONTRACT["style_id"],
        "caption_source": "rules_seed_pending_small_model_caption",
        "model_caption": _brief_caption(asset, name, object_class, conditions, semantic_target),
        "official_name": name,
        "s57_object_class": object_class,
        "s57_conditions": conditions,
        "condition_labels": _condition_labels(conditions),
        "official_definition": (master_row or {}).get("description") or (semantic_target or {}).get("official_name") or name,
        "required_primitives": _condition_labels(conditions),
        "reference_columns": reference_columns,
        "source_examples": source_examples,
        "generation_instructions": [
            "Draw owned SVG artwork in Helm style; do not trace restricted reference art.",
            f"Apply style contract {STYLE_CONTRACT['style_id']} for stroke, fill, palette, anchor, and small-chart legibility.",
            "Use Chart No.1/Chart 1 mapping crops and OpenCPN/S-101 only as comparison references unless license is cleared.",
            "Use emoji/open-source icon concepts only for generic primitive vocabulary such as triangle, circle, square, tap, shower, or bin.",
            safety_note,
        ],
        "qa_checks": [
            "semantic match to S-57 object class and attributes",
            "visual parity against Chart No.1 and provider examples",
            "sibling discrimination against confusable variants",
            "palette pass for day, dusk, and night",
        ],
        "source_refs": source_refs,
    }


def _matrix_rows(assets: list[str]) -> dict:
    pack = _read(PACK)
    master = _read(MASTER)
    semantic = _read(SEMANTIC)
    by_asset = {row["asset"]: row for row in pack["symbols"]}
    master_by_asset = {row["asset"]: row for row in master["rows"]}
    semantic_targets = _semantic_by_asset(semantic)

    rows = []
    for asset in assets:
        symbol = by_asset.get(asset)
        master_row = master_by_asset.get(asset)
        semantic_target = semantic_targets.get(asset)
        if not symbol and not master_row and not semantic_target:
            rows.append({"asset": asset, "status": "missing_from_catalog", "providers": {}})
            continue
        examples = list((symbol or {}).get("examples", []))
        examples.extend(_semantic_examples(asset, semantic))
        examples.extend(_concept_examples(asset, symbol, master_row, semantic_target))
        providers: dict[str, list[dict]] = {provider: [] for provider in PROVIDER_COLUMNS}
        counts: dict[str, int] = {provider: 0 for provider in PROVIDER_COLUMNS}
        for example in examples:
            provider = example.get("source")
            if provider not in providers:
                continue
            counts[provider] += 1
            providers[provider].append(_provider_entry(asset, provider, example, counts[provider]))

        source_refs = (symbol or {}).get("source_refs", {})
        semantic_s57 = _parse_semantic_s57(semantic_target)
        name = (symbol or {}).get("name") or (master_row or {}).get("description") or (semantic_target or {}).get("official_name") or asset
        rows.append({
            "asset": asset,
            "name": name,
            "kind": (symbol or {}).get("kind") or (master_row or {}).get("s52_asset_kind") or "chart-symbol",
            "family": (master_row or {}).get("family") or "semantic_targets",
            "art_state": (master_row or {}).get("art_state") or "semantic_target",
            "shape": (symbol or {}).get("geometry", {}).get("shape"),
            "s57": {
                "object_class": (master_row or {}).get("s57_object_class") or semantic_s57["object_class"],
                "conditions": (master_row or {}).get("s57_conditions", []) or semantic_s57["conditions"],
                "instruction": (master_row or {}).get("s52_instruction") or semantic_s57["instruction"],
            },
            "s101": source_refs.get("s101") or {
                "coverage": (master_row or {}).get("s101_coverage"),
                "symbol_id": (master_row or {}).get("s101_symbol_id"),
                "symbol_file": (master_row or {}).get("s101_symbol_file"),
                "feature_rule": (master_row or {}).get("s101_feature_rule"),
                "license_status": (master_row or {}).get("s101_license_status"),
            },
            "chart1_mappings_refs": source_refs.get("chart1_mappings", {}).get("int1_refs")
            or (master_row or {}).get("chart1_mappings_int1_refs", []),
            "providers": providers,
            "visual_brief": _build_visual_brief(asset, name, master_row, semantic_target, source_refs, providers),
        })
    return {
        "schema_version": 1,
        "method": "Unicode emoji chart style: one canonical symbol row with provider/source variant columns.",
        "style_contract": STYLE_CONTRACT,
        "provider_columns": PROVIDER_COLUMNS,
        "rows": rows,
    }


def _write_json(matrix: dict) -> Path:
    path = OUT / "source_variant_matrix.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(matrix, indent=2, sort_keys=True) + "\n")
    return path


def _coverage_report(matrix: dict) -> dict:
    providers = matrix["provider_columns"]
    rows = matrix["rows"]
    report = {
        "schema_version": 1,
        "row_count": len(rows),
        "provider_counts": {
            provider: sum(1 for row in rows if row.get("providers", {}).get(provider))
            for provider in providers
        },
        "provider_image_counts": {
            provider: sum(
                1
                for row in rows
                if any(entry.get("image") for entry in row.get("providers", {}).get(provider, []))
            )
            for provider in providers
        },
        "family_counts": {},
        "art_state_counts": {},
        "missing_reference_rows": [],
    }
    for row in rows:
        family = row.get("family") or "unknown"
        state = row.get("art_state") or "unknown"
        report["family_counts"][family] = report["family_counts"].get(family, 0) + 1
        report["art_state_counts"][state] = report["art_state_counts"].get(state, 0) + 1
        has_reference = any(
            row.get("providers", {}).get(provider)
            for provider in (
                "opencpn_s52_reference_render",
                "chart1_parity_reference_crop",
                "chart1_mappings_symbol_reference",
                "s101_portrayal_catalogue_svg",
                "wikimedia_commons_svg",
            )
        )
        if not has_reference:
            report["missing_reference_rows"].append({
                "asset": row["asset"],
                "name": row.get("name"),
                "family": family,
                "s57": row.get("s57"),
                "concept_columns": row.get("visual_brief", {}).get("reference_columns", []),
            })
    return report


def _write_report(matrix: dict) -> Path:
    path = OUT / "source_variant_matrix_report.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_coverage_report(matrix), indent=2, sort_keys=True) + "\n")
    return path


def _html_image(entry: dict) -> str:
    if not entry.get("image"):
        return "<div class='missing'>missing render</div>"
    return f"<img src='{html.escape(entry['image'])}' alt='{html.escape(entry.get('label') or entry['provider'])}'>"


def _write_html(matrix: dict) -> Path:
    path = OUT / "source_variant_matrix.html"
    css = """
body { font-family: -apple-system, BlinkMacSystemFont, Helvetica, Arial, sans-serif; margin: 24px; }
table { border-collapse: collapse; width: 100%; table-layout: fixed; }
th, td { border: 1px solid #b9c2cc; padding: 6px; vertical-align: top; font-size: 12px; }
th { background: #20364c; color: white; }
img { max-width: 72px; max-height: 72px; display: block; margin: 0 auto 4px; }
.meta { font-size: 10px; color: #334; overflow-wrap: anywhere; }
.missing { color: #a04b00; font-size: 10px; }
.asset { font-weight: 700; }
"""
    headers = ["Asset / S-57 / S-101"] + PROVIDER_COLUMNS
    rows = []
    for row in matrix["rows"]:
        meta = (
            f"<div class='asset'>{html.escape(row['asset'])}</div>"
            f"<div>{html.escape(row.get('name') or '')}</div>"
            f"<div class='meta'>S-57: {html.escape(str(row.get('s57', {})))}</div>"
            f"<div class='meta'>S-101: {html.escape(str(row.get('s101', {})))}</div>"
            f"<div class='meta'>Chart1 refs: {html.escape(', '.join(row.get('chart1_mappings_refs') or []))}</div>"
            f"<div class='meta'>Brief: {html.escape(row.get('visual_brief', {}).get('model_caption') or '')}</div>"
        )
        cells = [meta]
        for provider in PROVIDER_COLUMNS:
            entries = row.get("providers", {}).get(provider, [])
            if not entries:
                cells.append("<div class='missing'>none</div>")
                continue
            cells.append("".join(
                f"<div>{_html_image(entry)}<div class='meta'>{html.escape(entry.get('label') or '')}</div>"
                f"<div class='meta'>{html.escape(entry.get('status') or '')}</div></div>"
                for entry in entries[:3]
            ))
        rows.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + "</tr>")
    path.write_text(
        "<!doctype html><meta charset='utf-8'><title>Icon Forge Source Variant Matrix</title>"
        f"<style>{css}</style><h1>Icon Forge Source Variant Matrix</h1>"
        "<p>Unicode emoji-chart style: one canonical asset row, source/provider variants as columns.</p>"
        "<table><thead><tr>"
        + "".join(f"<th>{html.escape(h)}</th>" for h in headers)
        + "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )
    return path


def _pdf_para(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(html.escape(str(text)), style)


def _pdf_image(entry: dict, width: float) -> list:
    flows = []
    if entry.get("image"):
        image_path = ROOT / entry["image"]
        if image_path.exists():
            image = Image(str(image_path))
            scale = min(width / image.imageWidth, (1.05 * inch) / image.imageHeight)
            image.drawWidth = image.imageWidth * scale
            image.drawHeight = image.imageHeight * scale
            flows.append(image)
    flows.append(_pdf_para(entry.get("label") or "missing", _STYLES["Tiny"]))
    if entry.get("status"):
        flows.append(_pdf_para(entry["status"], _STYLES["TinyMuted"]))
    return flows


_STYLES = getSampleStyleSheet()
_STYLES["Title"].fontSize = 24
_STYLES["Title"].leading = 29
_STYLES["Heading2"].fontSize = 15
_STYLES["Heading2"].leading = 18
_STYLES.add(ParagraphStyle(name="Tiny", parent=_STYLES["BodyText"], fontSize=7.5, leading=8.7))
_STYLES.add(ParagraphStyle(name="TinyMuted", parent=_STYLES["BodyText"], fontSize=6.9, leading=7.9, textColor=colors.HexColor("#4c5560")))
_STYLES.add(ParagraphStyle(name="Small", parent=_STYLES["BodyText"], fontSize=8.4, leading=9.6))
_STYLES.add(ParagraphStyle(name="HeaderCell", parent=_STYLES["BodyText"], fontSize=7.0, leading=8.0, textColor=colors.white, alignment=1))
_STYLES.add(ParagraphStyle(name="ReadableBody", parent=_STYLES["BodyText"], fontSize=12.0, leading=15.0))
_STYLES.add(ParagraphStyle(name="ReadableSmall", parent=_STYLES["BodyText"], fontSize=10.5, leading=13.0))


def _source_boundary_text() -> str:
    return (
        "Provider variants are comparison references. Helm draft art is generated-owned but still pending visual approval. "
        "Chart 1 / Chart 1 Mappings crops are reference-only. OpenCPN renders are GPL reference oracles, not canonical assets. "
        "S-101 is license-pending reference. Commons rows require per-file license and semantic QA before promotion. "
        "Noto/OpenMoji/Lucide/OpenBridge entries are concept or primitive references unless counsel clears exact asset reuse."
    )


def _style_contract_story() -> list:
    contract = STYLE_CONTRACT
    rows = [
        [_pdf_para("Style id", _STYLES["Small"]), _pdf_para(contract["style_id"], _STYLES["ReadableSmall"])],
        [_pdf_para("Purpose", _STYLES["Small"]), _pdf_para(contract["purpose"], _STYLES["ReadableSmall"])],
        [_pdf_para("Canonical SVG", _STYLES["Small"]), _pdf_para("; ".join(f"{key}: {value}" for key, value in contract["canonical_svg"].items()), _STYLES["ReadableSmall"])],
        [_pdf_para("Visual language", _STYLES["Small"]), _pdf_para(" ".join(contract["visual_language"]), _STYLES["ReadableSmall"])],
        [_pdf_para("LLM order", _STYLES["Small"]), _pdf_para(" ".join(contract["llm_generation_order"]), _STYLES["ReadableSmall"])],
        [_pdf_para("Reject if", _STYLES["Small"]), _pdf_para(" ".join(contract["rejection_rules"]), _STYLES["ReadableSmall"])],
    ]
    table = Table(rows, colWidths=[1.7 * inch, 18.9 * inch])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b8c2cc")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef3f7")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return [
        _pdf_para("Source Boundary", _STYLES["Heading2"]),
        _pdf_para(_source_boundary_text(), _STYLES["ReadableBody"]),
        Spacer(1, 0.16 * inch),
        _pdf_para("LLM Style Contract", _STYLES["Heading2"]),
        table,
    ]


def _write_pdf(matrix: dict, path: Path | None = None, title: str = "Icon Forge Source Variant Matrix") -> Path:
    path = path or OUT / "source_variant_matrix.pdf"
    path.parent.mkdir(parents=True, exist_ok=True)
    story = [
        _pdf_para(title, _STYLES["Title"]),
        _pdf_para("One canonical asset row with source/provider variants as columns. The next page starts the matrix; this page is the readable source and style contract for the LLM rendering pass.", _STYLES["ReadableBody"]),
        Spacer(1, 0.16 * inch),
    ]
    story.extend(_style_contract_story())
    story.append(PageBreak())
    headers = [_pdf_para("Asset / S-57 / S-101", _STYLES["HeaderCell"])] + [
        _pdf_para(provider.replace("_", " "), _STYLES["HeaderCell"]) for provider in PROVIDER_COLUMNS
    ]
    widths = [2.45 * inch] + [1.9 * inch] * len(PROVIDER_COLUMNS)
    data = [headers]
    for row in matrix["rows"]:
        meta = [
            _pdf_para(row["asset"], _STYLES["Small"]),
            _pdf_para(row.get("name") or "", _STYLES["Tiny"]),
            _pdf_para(f"S-57 {row.get('s57', {}).get('object_class')}: {'; '.join(row.get('s57', {}).get('conditions') or [])}", _STYLES["Tiny"]),
            _pdf_para(f"S-101 {row.get('s101', {}).get('symbol_id') or row.get('s101', {}).get('coverage')}", _STYLES["Tiny"]),
            _pdf_para(f"Chart1 refs: {', '.join(row.get('chart1_mappings_refs') or [])}", _STYLES["Tiny"]),
            _pdf_para(f"Brief: {row.get('visual_brief', {}).get('model_caption') or ''}", _STYLES["TinyMuted"]),
        ]
        cells = [meta]
        for provider in PROVIDER_COLUMNS:
            entries = row.get("providers", {}).get(provider, [])
            provider_flows = []
            for entry in entries[:2]:
                provider_flows.extend(_pdf_image(entry, 1.25 * inch))
                provider_flows.append(Spacer(1, 0.02 * inch))
            if not provider_flows:
                provider_flows = [_pdf_para("none", _STYLES["TinyMuted"])]
            cells.append(provider_flows)
        data.append(cells)
    table = Table(data, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#20364c")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#aab3bd")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6f8")]),
    ]))
    story.append(table)
    SimpleDocTemplate(
        str(path),
        pagesize=(24 * inch, 14 * inch),
        leftMargin=0.28 * inch,
        rightMargin=0.28 * inch,
        topMargin=0.28 * inch,
        bottomMargin=0.28 * inch,
    ).build(story)
    return path


def _write_family_pdfs(matrix: dict) -> dict[str, str]:
    outputs = {}
    by_family: dict[str, list[dict]] = {}
    for row in matrix["rows"]:
        by_family.setdefault(row.get("family") or "unknown", []).append(row)
    for family, rows in sorted(by_family.items()):
        family_matrix = {
            "schema_version": matrix["schema_version"],
            "method": matrix["method"],
            "provider_columns": matrix["provider_columns"],
            "rows": rows,
        }
        path = OUT / "family_pdfs" / f"{_safe(family)}.pdf"
        outputs[family] = _rel(_write_pdf(family_matrix, path, f"Icon Forge Source Matrix - {family}"))
    return outputs


def all_assets() -> list[str]:
    master = _read(MASTER)
    semantic = _read(SEMANTIC)
    assets = [row["asset"] for row in master["rows"]]
    for target in semantic.get("targets", []):
        asset = target.get("generation_target", {}).get("asset_id")
        if asset and asset not in assets:
            assets.append(asset)
    return assets


def build(assets: list[str], *, include_pdf: bool = True, family_pdfs: bool = False) -> dict:
    matrix = _matrix_rows(assets)
    matrix["outputs"] = {
        "json": _rel(_write_json(matrix)),
    }
    matrix["outputs"]["html"] = _rel(_write_html(matrix))
    matrix["outputs"]["report"] = _rel(_write_report(matrix))
    if include_pdf:
        matrix["outputs"]["pdf"] = _rel(_write_pdf(matrix))
    if family_pdfs:
        matrix["outputs"]["family_pdfs"] = _write_family_pdfs(matrix)
    _write_json(matrix)
    return matrix


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset", action="append", dest="assets", help="S-52/Helm asset id to include")
    parser.add_argument("--all", action="store_true", help="Build the matrix for every master catalog row plus semantic-only targets")
    parser.add_argument("--skip-pdf", action="store_true", help="Skip the single PDF output; useful for full-catalog JSON/HTML runs")
    parser.add_argument("--family-pdfs", action="store_true", help="Write one PDF per symbol family for readable full-catalog inspection")
    args = parser.parse_args(argv)
    assets = all_assets() if args.all else (args.assets or DEFAULT_ASSETS)
    matrix = build(assets, include_pdf=not args.skip_pdf, family_pdfs=args.family_pdfs)
    summary = {
        "asset_count": len(assets),
        "rows": len(matrix["rows"]),
        "outputs": matrix["outputs"],
    }
    if len(assets) <= 20:
        summary["assets"] = assets
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
