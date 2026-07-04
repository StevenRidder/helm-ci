"""Repair a high-confidence subset of the 163-row queue into owned batch 18.

Run:
  python -m forge.standard_repair_batch10 --render
"""
from __future__ import annotations

import argparse
import ctypes.util
import json
import re
from pathlib import Path

from . import render
from .style_contract import OPENBRIDGE_NAV_PALETTES, OPENBRIDGE_STYLE_ID


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
SOURCE_QUEUE = CATALOG / "standard_repair_queue.json"
SOURCE_TABLE = CATALOG / "standard_source_table.json"
OUT = ROOT / "out" / "standard_repair_batch10"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch18"
REPORT = CATALOG / "owned_repair_batch18.json"
SUMMARY = CATALOG / "owned_repair_batch18.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

EXPECTED_QUEUE = [
    "BCNCON81", "BOYCON81", "BOYLAT52", "BOYLAT53", "BOYSPH79", "BOYSPR02",
    "BOYSPR03", "BOYSUP01", "BOYSUP02", "BOYSUP03", "BOYSUP65", "BRIDGE01",
    "BUNSTA02", "BUNSTA03", "CGUSTA02", "CRANES01", "CURDEF01", "CURENT01",
    "CUSTOM01", "DANGER53", "DAYSQR21", "DGPS01DRFSTA01", "DISMAR03",
    "DISMAR04", "DWRTPT51", "EBBSTR01", "ESSARE01", "EVENTS02", "FAIRWY51",
    "FAIRWY52", "FLDSTR01", "FLGSTF01", "FLTHAZ02", "FOGSIG01", "FOULGND1",
    "FRYARE51", "FRYARE52", "FSHFAC02", "FSHFAC03", "FSHGRD01", "FSHHAV01",
    "GATCON03", "GATCON04", "HECMTR01", "HECMTR02", "HGWTMK01", "HRBFAC09",
    "HRBFAC10", "HRBFAC11", "HRBFAC12", "HRBFAC13", "HRBFAC14", "HRBFAC15",
    "HRBFAC16", "HRBFAC17", "HRBFAC18", "HULKES01", "INFARE51", "INFORM01",
    "ISODGR51", "ITZARE51", "LITFLT01", "LITFLT02", "LITFLT10", "LITFLT61",
    "LITVES01", "LITVES02", "LITVES60", "LITVES61", "LNDARE01", "MARCUL02",
    "MONUMT02", "MONUMT12", "MORFAC03", "MORFAC04", "MSTCON04", "MSTCON14",
    "NEWOBJ 01", "NEWOBJ01", "NMKINF01", "NMKINF02", "NMKINF03", "NMKINF04",
    "NMKINF05", "NMKINF06", "NMKINF19", "NMKINF20", "NMKINF21", "NMKINF22",
    "NMKINF23", "NMKINF24", "NMKINF25", "NMKINF26", "NMKINF27", "NMKINF28",
    "NMKINF29", "NMKINF38", "NMKINF40", "NMKINF43", "NMKINF44", "NMKINF45",
    "NMKINF46", "NMKINF47", "NMKINF48", "NMKINF49", "NMKINF50", "NMKINF53",
    "NMKPRH02", "NMKPRH06", "NMKPRH07", "NMKPRH08", "NMKPRH10", "NMKPRH11",
    "NMKPRH12", "NMKPRH13", "NMKPRH14", "NMKRCD01", "NMKRCD02", "NMKRCD03",
    "NMKRCD04", "NMKRCD05", "NMKRCD06", "NMKREG01", "NMKREG02", "NMKREG03",
    "NMKREG10", "NMKREG11", "NMKREG12", "NMKREG13", "NMKREG14", "NMKREG15",
    "NMKREG16", "NMKREG17", "NMKREG19", "NMKREG20", "NORTHAR1", "NOTBRD11",
    "NOTBRD12", "NOTMRK01", "NOTMRK02", "NOTMRK03", "OBSTRN03", "OFSPLF01",
    "OSPONE02", "OSPSIX02", "OWNSHP01", "OWNSHP05", "PIER0001", "PILBOP02",
    "PILPNT02", "PLNPOS01", "PLNPOS02", "PLNSPD03", "PLNSPD04", "POSGEN01",
    "POSGEN03", "POSGEN04", "POSITN02", "PRCARE12", "PRCARE51", "PRDINS02",
    "PRICKE03", "PRICKE04",
]

REPAIRS: dict[str, dict] = {
    "BRIDGE01": {"kind": "bridge"},
    "CGUSTA02": {"kind": "cg_station"},
    "CRANES01": {"kind": "crane"},
    "CURDEF01": {"kind": "current_unknown"},
    "CURENT01": {"kind": "current_branch"},
    "DAYSQR21": {"kind": "day_square_ring"},
    "DWRTPT51": {"kind": "label_box", "label": "DW", "colour": "magenta"},
    "EBBSTR01": {"kind": "stream_arrow", "direction": "up", "colour": "blue"},
    "FAIRWY51": {"kind": "fairway", "mode": "one"},
    "FAIRWY52": {"kind": "fairway", "mode": "two"},
    "FLDSTR01": {"kind": "stream_arrow", "direction": "up", "colour": "blue", "barbs": True},
    "FLGSTF01": {"kind": "flagstaff"},
    "FLTHAZ02": {"kind": "floating_hazard"},
    "FOGSIG01": {"kind": "fog_signal"},
    "FOULGND1": {"kind": "foul_ground"},
    "FRYARE51": {"kind": "label_box", "label": "F", "colour": "magenta", "route": True},
    "FRYARE52": {"kind": "label_box", "label": "CF", "colour": "magenta", "route": True},
    "FSHFAC02": {"kind": "fish_stakes"},
    "FSHFAC03": {"kind": "fish_stakes_area"},
    "FSHGRD01": {"kind": "fish_label", "label": "FG"},
    "FSHHAV01": {"kind": "fish_label", "label": "FH"},
    "HULKES01": {"kind": "hulk"},
    "INFARE51": {"kind": "info_area"},
    "INFORM01": {"kind": "information"},
    "ITZARE51": {"kind": "traffic_area"},
    "LNDARE01": {"kind": "land_point"},
    "MARCUL02": {"kind": "marine_farm"},
    "MONUMT02": {"kind": "monument", "colour": "brown"},
    "MONUMT12": {"kind": "monument", "colour": "black"},
    "MSTCON04": {"kind": "mast", "colour": "brown"},
    "MSTCON14": {"kind": "mast", "colour": "black"},
    "NORTHAR1": {"kind": "north_arrow"},
    "NOTBRD11": {"kind": "notice_board"},
    "OBSTRN03": {"kind": "obstruction_green"},
    "OFSPLF01": {"kind": "offshore_platform"},
    "PILBOP02": {"kind": "pilot_boarding"},
    "PILPNT02": {"kind": "pile_point"},
    "POSGEN01": {"kind": "position", "mode": "ring"},
    "POSGEN03": {"kind": "position", "mode": "target"},
    "POSGEN04": {"kind": "position", "mode": "elevation"},
    "PRCARE12": {"kind": "precaution_triangle", "area": False},
    "PRCARE51": {"kind": "precaution_triangle", "area": True},
    "PRDINS02": {"kind": "production_installation"},
}

REPAIR_NOTES = {
    "BRIDGE01": "Remove the invented black crosshair and redraw as a magenta opening-bridge ring with diagonal opening cue.",
    "CGUSTA02": "Replace the diamond with a coastguard CG placard/box and point marker.",
    "CRANES01": "Replace the diamond with a generated crane silhouette using boom, post, hook, and base.",
    "CURDEF01": "Redraw as the vertical current arrow with side question marks.",
    "CURENT01": "Redraw as a straight vertical current arrow with lower branching barbs and no curved secondary stroke.",
    "DAYSQR21": "Redraw as a coloured square/rectangular daymark on a stem with base/ring detail.",
    "DWRTPT51": "Replace the diamond with a DW text route mark in the reference style.",
    "EBBSTR01": "Redraw as the upward stream-rate arrow/barb silhouette.",
    "FAIRWY51": "Redraw as a vertical outlined one-way fairway arrow.",
    "FAIRWY52": "Redraw as a vertical outlined two-way fairway arrow.",
    "FLDSTR01": "Redraw as the upward flood-stream arrow with side-barb/rate cue.",
    "FLGSTF01": "Redraw as a brown flagstaff/flagpole witness with flag shape and base detail.",
    "FLTHAZ02": "Replace the diamond with a floating-hazard mark using an open warning hull/float form.",
    "FOGSIG01": "Replace the diamond with a fog-signal bell/horn cue.",
    "FOULGND1": "Redraw as an open foul-ground hash/slash mark without enclosing square.",
    "FRYARE51": "Replace the diamond with a ferry-area route cue and F label.",
    "FRYARE52": "Replace the diamond with a cable-ferry area route cue and CF label.",
    "FSHFAC02": "Redraw as fishing stakes with frame and angled stake.",
    "FSHFAC03": "Redraw as a fishing-stakes area pattern, not a buoy silhouette.",
    "FSHGRD01": "Replace the diamond with a fishing-ground FG symbol.",
    "FSHHAV01": "Replace the diamond with a fish-haven FH symbol.",
    "HULKES01": "Replace the diamond with a brown hulk/wreck-like silhouette.",
    "INFARE51": "Replace the area placeholder with an information/restriction-area symbol.",
    "INFORM01": "Redraw as a reference information marker with boxed i, leader, and origin circle.",
    "ITZARE51": "Replace the diamond with an inshore-traffic-area route/traffic cue.",
    "LNDARE01": "Replace the dashed area placeholder with a land-area point symbol.",
    "MARCUL02": "Redraw as a marine-farm net/line motif.",
    "MONUMT02": "Replace the diamond with a brown monument silhouette.",
    "MONUMT12": "Replace the diamond with a black conspicuous monument silhouette.",
    "MSTCON04": "Replace the diamond with a brown mast/needle silhouette.",
    "MSTCON14": "Replace the diamond with a black conspicuous mast/needle silhouette.",
    "NORTHAR1": "Replace the diamond with an orange north-arrow glyph preserving north/up orientation.",
    "NOTBRD11": "Replace the diamond with a straightforward black notice-board/post silhouette.",
    "OBSTRN03": "Preserve obstruction-circle semantics and use the green-tinted fill/color treatment.",
    "OFSPLF01": "Replace the diamond with a square offshore-platform structure glyph.",
    "PILBOP02": "Replace the diamond with a magenta pilot boarding glyph.",
    "PILPNT02": "Replace the diamond with a pile/bollard square point mark.",
    "POSGEN01": "Replace the diamond with a ring point-position mark.",
    "POSGEN03": "Replace the diamond with a conspicuous target/ring point mark.",
    "POSGEN04": "Replace the diamond with an elevation/control-point target marker.",
    "PRCARE12": "Replace the dashed square with a magenta triangular precautionary-area point symbol.",
    "PRCARE51": "Replace the dashed rectangle pattern with a magenta triangular precaution boundary symbol.",
    "PRDINS02": "Replace the dashed area placeholder with a brown crossed mine/quarry symbol.",
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{name})"


def _text(x: int, y: int, label: str, colour: str, size: int = 18, weight: int = 700) -> str:
    return (
        f'<text x="{x}" y="{y}" text-anchor="middle" font-size="{size}" '
        'font-family="Arial, Helvetica, sans-serif" '
        f'font-weight="{weight}" fill="{_colour(colour)}" stroke="none">{label}</text>'
    )


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch10">'
        f"<title>{asset} standard repair batch 18 candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _bridge() -> str:
    return (
        f'<circle cx="32" cy="32" r="17" fill="none" stroke="{_colour("magenta")}" stroke-width="4"/>'
        f'<path d="M21 43 L43 21" fill="none" stroke="{_colour("magenta")}" stroke-width="4"/>'
        f'<path d="M20 32 H44" fill="none" stroke="{_colour("magenta")}" stroke-width="2.8" stroke-dasharray="5 5"/>'
    )


def _cg_station() -> str:
    return (
        f'<rect x="16" y="16" width="32" height="25" rx="3" fill="{_colour("white")}" '
        f'stroke="{_colour("magenta")}" stroke-width="3.5"/>'
        f'{_text(32, 35, "CG", "magenta", 16)}'
        f'<path d="M32 41 V52" fill="none" stroke="{_colour("magenta")}" stroke-width="3"/>'
        f'<circle cx="32" cy="55" r="3.5" fill="{_colour("magenta")}" stroke="none"/>'
    )


def _crane() -> str:
    return (
        f'<path d="M18 50 H46 M24 50 V21 H36 M24 26 L46 18 M40 20 V34" '
        f'fill="none" stroke="{_colour("black")}" stroke-width="4"/>'
        f'<path d="M40 34 C45 36 44 42 39 43" fill="none" stroke="{_colour("black")}" stroke-width="3"/>'
    )


def _current_unknown() -> str:
    return (
        f'<path d="M32 13 V50 M23 23 L32 13 L41 23 M22 44 C27 49 37 49 42 44" '
        f'fill="none" stroke="{_colour("blue")}" stroke-width="4"/>'
        f'{_text(18, 35, "?", "blue", 18)}{_text(46, 35, "?", "blue", 18)}'
    )


def _current_branch() -> str:
    return (
        f'<path d="M32 12 V52 M23 22 L32 12 L41 22 M32 42 L22 52 M32 42 L42 52" '
        f'fill="none" stroke="{_colour("blue")}" stroke-width="4"/>'
    )


def _day_square_ring() -> str:
    return (
        f'<rect x="20" y="11" width="24" height="24" fill="{_colour("yellow")}" '
        f'stroke="{_colour("black")}" stroke-width="3"/>'
        f'<path d="M32 35 V53" fill="none" stroke="{_colour("black")}" stroke-width="4"/>'
        f'<circle cx="32" cy="56" r="4" fill="none" stroke="{_colour("black")}" stroke-width="3"/>'
    )


def _label_box(label: str, colour: str, route: bool = False) -> str:
    route_path = (
        f'<path d="M16 47 C26 39 38 39 48 47" fill="none" stroke="{_colour(colour)}" '
        'stroke-width="3" stroke-dasharray="6 5"/>'
        if route else ""
    )
    return (
        f'<rect x="17" y="18" width="30" height="23" rx="3" fill="none" '
        f'stroke="{_colour(colour)}" stroke-width="3.5"/>'
        f'{_text(32, 35, label, colour, 17)}{route_path}'
    )


def _stream_arrow(colour: str, barbs: bool = False) -> str:
    extra = f'<path d="M32 42 L22 50 M32 42 L42 50" fill="none" stroke="{_colour(colour)}" stroke-width="3.5"/>' if barbs else ""
    return (
        f'<path d="M32 53 V12 M22 24 L32 12 L42 24" fill="none" '
        f'stroke="{_colour(colour)}" stroke-width="4"/>{extra}'
    )


def _fairway(mode: str) -> str:
    top = f'<path d="M32 10 L44 26 H36 V52 H28 V26 H20 Z" fill="none" stroke="{_colour("magenta")}" stroke-width="3.8"/>'
    if mode == "one":
        return top
    return top + f'<path d="M22 43 L32 54 L42 43" fill="none" stroke="{_colour("magenta")}" stroke-width="3.8"/>'


def _flagstaff() -> str:
    return (
        f'<path d="M26 53 V13 M26 15 H45 L39 24 L45 33 H26 M19 56 H33" '
        f'fill="none" stroke="{_colour("brown")}" stroke-width="4"/>'
    )


def _floating_hazard() -> str:
    return (
        f'<path d="M17 41 C24 32 40 32 47 41 L42 50 H22 Z" fill="none" '
        f'stroke="{_colour("black")}" stroke-width="4"/>'
        f'<path d="M25 31 L32 17 L39 31 M24 45 H40" fill="none" stroke="{_colour("black")}" stroke-width="3.5"/>'
    )


def _fog_signal() -> str:
    return (
        f'<path d="M22 37 C22 24 42 24 42 37 L47 49 H17 Z" fill="none" '
        f'stroke="{_colour("black")}" stroke-width="4"/>'
        f'<path d="M18 18 C24 11 40 11 46 18 M22 22 C27 17 37 17 42 22" '
        f'fill="none" stroke="{_colour("black")}" stroke-width="3"/>'
    )


def _foul_ground() -> str:
    return (
        f'<path d="M18 18 L46 46 M46 18 L18 46 M15 32 H49 M32 15 V49" '
        f'fill="none" stroke="{_colour("black")}" stroke-width="3.5"/>'
    )


def _fish_stakes(area: bool = False) -> str:
    base = (
        f'<path d="M18 49 L29 18 L40 49 M24 35 H36 M20 49 H44" fill="none" '
        f'stroke="{_colour("brown")}" stroke-width="3.5"/>'
    )
    if not area:
        return base
    return base + (
        f'<path d="M15 21 H49 M15 43 H49" fill="none" stroke="{_colour("brown")}" '
        'stroke-width="2.5" stroke-dasharray="4 5"/>'
    )


def _fish_label(label: str) -> str:
    return (
        f'<path d="M17 34 C25 24 39 24 47 34 C39 44 25 44 17 34 Z" fill="none" '
        f'stroke="{_colour("brown")}" stroke-width="3.5"/>'
        f'<path d="M47 34 L55 27 V41 Z" fill="none" stroke="{_colour("brown")}" stroke-width="3.5"/>'
        f'{_text(32, 39, label, "brown", 13)}'
    )


def _hulk() -> str:
    return (
        f'<path d="M14 40 C23 49 41 49 50 40 L44 52 H20 Z" fill="none" '
        f'stroke="{_colour("brown")}" stroke-width="3.8"/>'
        f'<path d="M23 39 L29 24 L39 39 M25 32 H39" fill="none" stroke="{_colour("brown")}" stroke-width="3.2"/>'
    )


def _info_area() -> str:
    return (
        f'<path d="M16 44 C23 33 41 33 48 44" fill="none" stroke="{_colour("magenta")}" '
        'stroke-width="3.5" stroke-dasharray="6 5"/>'
        f'<rect x="24" y="14" width="16" height="22" rx="2" fill="none" stroke="{_colour("magenta")}" stroke-width="3"/>'
        f'{_text(32, 31, "i", "magenta", 18)}'
    )


def _information() -> str:
    return (
        f'<rect x="24" y="12" width="16" height="23" rx="2" fill="none" stroke="{_colour("magenta")}" stroke-width="3.2"/>'
        f'{_text(32, 31, "i", "magenta", 18)}'
        f'<path d="M32 35 V49 M21 52 H43" fill="none" stroke="{_colour("magenta")}" stroke-width="3.2"/>'
        f'<circle cx="32" cy="55" r="3" fill="{_colour("magenta")}" stroke="none"/>'
    )


def _traffic_area() -> str:
    return (
        f'<path d="M18 45 H46 M24 38 H40" fill="none" stroke="{_colour("magenta")}" stroke-width="3.5"/>'
        f'<path d="M22 28 H42 M35 21 L42 28 L35 35 M42 28 H22 M29 21 L22 28 L29 35" '
        f'fill="none" stroke="{_colour("magenta")}" stroke-width="3.2"/>'
    )


def _land_point() -> str:
    return (
        f'<path d="M15 45 C21 29 30 25 35 35 C40 25 49 32 54 45 Z" fill="{_colour("brown")}" '
        f'fill-opacity="0.18" stroke="{_colour("brown")}" stroke-width="3.5"/>'
        f'<path d="M22 50 H46" fill="none" stroke="{_colour("brown")}" stroke-width="3"/>'
    )


def _marine_farm() -> str:
    return (
        f'<path d="M15 20 H49 M15 32 H49 M15 44 H49 M20 15 V49 M32 15 V49 M44 15 V49" '
        f'fill="none" stroke="{_colour("brown")}" stroke-width="2.6" stroke-dasharray="5 4"/>'
    )


def _monument(colour: str) -> str:
    return (
        f'<path d="M32 12 L42 50 H22 Z" fill="none" stroke="{_colour(colour)}" stroke-width="4"/>'
        f'<path d="M24 50 H40 M28 28 H36" fill="none" stroke="{_colour(colour)}" stroke-width="3.5"/>'
    )


def _mast(colour: str) -> str:
    return (
        f'<path d="M32 10 V53 M22 53 H42 M32 18 L22 42 M32 18 L42 42" '
        f'fill="none" stroke="{_colour(colour)}" stroke-width="4"/>'
    )


def _north_arrow() -> str:
    return (
        f'<path d="M32 8 L45 53 L32 43 L19 53 Z" fill="none" stroke="{_colour("orange")}" stroke-width="4"/>'
        f'{_text(32, 31, "N", "orange", 17)}'
    )


def _notice_board() -> str:
    return (
        f'<rect x="19" y="15" width="26" height="20" rx="2" fill="none" stroke="{_colour("black")}" stroke-width="4"/>'
        f'<path d="M32 35 V53 M23 53 H41" fill="none" stroke="{_colour("black")}" stroke-width="4"/>'
    )


def _obstruction_green() -> str:
    return (
        f'<circle cx="32" cy="32" r="17" fill="{_colour("green")}" fill-opacity="0.22" '
        f'stroke="{_colour("green")}" stroke-width="3.5" stroke-dasharray="3 5"/>'
        f'<circle cx="32" cy="32" r="5" fill="{_colour("green")}" stroke="none"/>'
    )


def _offshore_platform() -> str:
    return (
        f'<rect x="20" y="14" width="24" height="24" fill="none" stroke="{_colour("black")}" stroke-width="4"/>'
        f'<path d="M23 38 L17 53 M41 38 L47 53 M18 53 H46 M25 24 H39 M32 14 V38" '
        f'fill="none" stroke="{_colour("black")}" stroke-width="3.3"/>'
    )


def _pilot_boarding() -> str:
    return (
        f'<circle cx="32" cy="31" r="15" fill="none" stroke="{_colour("magenta")}" stroke-width="3.5"/>'
        f'{_text(32, 37, "P", "magenta", 22)}'
        f'<path d="M32 46 V55" fill="none" stroke="{_colour("magenta")}" stroke-width="3"/>'
    )


def _pile_point() -> str:
    return (
        f'<rect x="23" y="18" width="18" height="18" fill="none" stroke="{_colour("black")}" stroke-width="4"/>'
        f'<path d="M32 36 V53 M23 53 H41" fill="none" stroke="{_colour("black")}" stroke-width="4"/>'
    )


def _position(mode: str) -> str:
    base = f'<circle cx="32" cy="32" r="15" fill="none" stroke="{_colour("black")}" stroke-width="3.5"/>'
    if mode == "ring":
        return base + f'<circle cx="32" cy="32" r="4" fill="{_colour("black")}" stroke="none"/>'
    if mode == "target":
        return base + f'<path d="M32 13 V51 M13 32 H51" fill="none" stroke="{_colour("black")}" stroke-width="3"/>'
    return base + f'<path d="M22 42 L32 18 L42 42 Z" fill="none" stroke="{_colour("black")}" stroke-width="3"/>'


def _precaution_triangle(area: bool) -> str:
    dash = ' stroke-dasharray="6 5"' if area else ""
    return (
        f'<polygon points="32,12 49,45 15,45" fill="none" stroke="{_colour("magenta")}" '
        f'stroke-width="3.8"{dash}/>'
        f'<path d="M32 24 V35" fill="none" stroke="{_colour("magenta")}" stroke-width="3.4"/>'
        f'<circle cx="32" cy="40" r="2.5" fill="{_colour("magenta")}" stroke="none"/>'
    )


def _production_installation() -> str:
    return (
        f'<path d="M18 48 L46 20 M18 20 L46 48" fill="none" stroke="{_colour("brown")}" stroke-width="4"/>'
        f'<circle cx="32" cy="34" r="11" fill="none" stroke="{_colour("brown")}" stroke-width="3"/>'
    )


def _redraw(asset: str) -> str:
    spec = REPAIRS[asset]
    kind = spec["kind"]
    if kind == "bridge":
        return _svg(asset, _bridge())
    if kind == "cg_station":
        return _svg(asset, _cg_station())
    if kind == "crane":
        return _svg(asset, _crane())
    if kind == "current_unknown":
        return _svg(asset, _current_unknown())
    if kind == "current_branch":
        return _svg(asset, _current_branch())
    if kind == "day_square_ring":
        return _svg(asset, _day_square_ring())
    if kind == "label_box":
        return _svg(asset, _label_box(spec["label"], spec["colour"], spec.get("route", False)))
    if kind == "stream_arrow":
        return _svg(asset, _stream_arrow(spec["colour"], spec.get("barbs", False)))
    if kind == "fairway":
        return _svg(asset, _fairway(spec["mode"]))
    if kind == "flagstaff":
        return _svg(asset, _flagstaff())
    if kind == "floating_hazard":
        return _svg(asset, _floating_hazard())
    if kind == "fog_signal":
        return _svg(asset, _fog_signal())
    if kind == "foul_ground":
        return _svg(asset, _foul_ground())
    if kind == "fish_stakes":
        return _svg(asset, _fish_stakes())
    if kind == "fish_stakes_area":
        return _svg(asset, _fish_stakes(True))
    if kind == "fish_label":
        return _svg(asset, _fish_label(spec["label"]))
    if kind == "hulk":
        return _svg(asset, _hulk())
    if kind == "info_area":
        return _svg(asset, _info_area())
    if kind == "information":
        return _svg(asset, _information())
    if kind == "traffic_area":
        return _svg(asset, _traffic_area())
    if kind == "land_point":
        return _svg(asset, _land_point())
    if kind == "marine_farm":
        return _svg(asset, _marine_farm())
    if kind == "monument":
        return _svg(asset, _monument(spec["colour"]))
    if kind == "mast":
        return _svg(asset, _mast(spec["colour"]))
    if kind == "north_arrow":
        return _svg(asset, _north_arrow())
    if kind == "notice_board":
        return _svg(asset, _notice_board())
    if kind == "obstruction_green":
        return _svg(asset, _obstruction_green())
    if kind == "offshore_platform":
        return _svg(asset, _offshore_platform())
    if kind == "pilot_boarding":
        return _svg(asset, _pilot_boarding())
    if kind == "pile_point":
        return _svg(asset, _pile_point())
    if kind == "position":
        return _svg(asset, _position(spec["mode"]))
    if kind == "precaution_triangle":
        return _svg(asset, _precaution_triangle(spec["area"]))
    if kind == "production_installation":
        return _svg(asset, _production_installation())
    raise KeyError(f"unsupported repair kind: {kind}")


def _ensure_cairo_library() -> None:
    if ctypes.util.find_library("cairo") or not HOMEBREW_CAIRO.exists():
        return
    original_find_library = ctypes.util.find_library

    def find_library(name: str) -> str | None:
        if name in {"cairo", "cairo-2", "libcairo-2"}:
            return str(HOMEBREW_CAIRO)
        return original_find_library(name)

    ctypes.util.find_library = find_library


def _render_svg(svg: str, asset: str, palette: str) -> str:
    _ensure_cairo_library()
    out = OUT / "renders" / f"{_safe(asset)}__after__{palette}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(render.rasterize(svg, OPENBRIDGE_NAV_PALETTES[palette], size=160))
    return str(out.relative_to(ROOT))


def _source_judge_for(item: dict) -> str | None:
    batch = item.get("judge", {}).get("batch")
    if batch:
        return f"catalog/{batch}.json"
    return None


def _provider_count(item: dict) -> int:
    refs = item.get("reference_providers") or {}
    return sum(len(refs.get(name) or []) for name in ("s101", "aquamap", "opencpn_render"))


def _required_change(item: dict) -> str | None:
    return item.get("required_change") or item.get("judge", {}).get("required_change")


def _safety_codes(item: dict) -> list[str]:
    return item.get("safety_reason_codes") or item.get("judge", {}).get("safety_reason_codes") or []


def _skip_status(item: dict) -> str:
    asset = item.get("asset", "")
    codes = set(_safety_codes(item))
    required = (_required_change(item) or "").lower()
    if "regenerate/verify" in required or "regenerate or attach" in required:
        return "blocked_missing_local_reference_render"
    if "missing_reference_crop" in codes or "locate/render" in required or "resolve the exact reference" in required:
        return "blocked_missing_reference_or_exact_crop"
    if {"missing_exact_reference", "insufficient_visual_evidence"}.intersection(codes):
        return "hard_blocked_missing_exact_reference"
    if asset.startswith(("NMKINF", "NMKPRH", "NMKRCD", "NMKREG")):
        return "skipped_batch18_notice_board_family_dedicated_pass"
    if asset.startswith(("NOTBRD", "NOTMRK")):
        return "skipped_batch18_notice_board_geometry_or_marker_contract"
    if _provider_count(item) < 2:
        return "skipped_batch18_low_reference_confidence"
    if asset.startswith(("BOY", "BCN", "HRBFAC", "LIT", "MORFAC", "GATCON", "PRICKE")):
        return "skipped_batch18_geometry_heavy_or_exact_contract"
    return "skipped_batch18_outside_bounded_high_confidence_subset"


def build(*, render_outputs: bool = False) -> dict:
    queue = json.loads(SOURCE_QUEUE.read_text())
    source_table = json.loads(SOURCE_TABLE.read_text()) if SOURCE_TABLE.exists() else {"rows": []}
    source_rows = {row["asset"]: row for row in source_table.get("rows", [])}
    queue_items = {item["asset"]: item for item in queue.get("items", [])}
    actual_queue = [item["asset"] for item in queue.get("items", [])]
    if actual_queue != EXPECTED_QUEUE:
        raise RuntimeError(f"unexpected standard repair queue: {actual_queue}")

    SVG_OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    blockers = []
    for asset in EXPECTED_QUEUE:
        item = queue_items.get(asset, {})
        source_row = source_rows.get(asset, {})
        if asset not in REPAIRS:
            blockers.append({
                "asset": asset,
                "status": _skip_status(item),
                "required_change": _required_change(item),
                "safety_reason_codes": _safety_codes(item),
                "semantic_brief": item.get("semantic_brief") or source_row.get("semantic_brief"),
                "reference_providers": item.get("reference_providers") or source_row.get("reference_providers", {}),
            })
            continue

        svg = _redraw(asset)
        svg_path = SVG_OUT / f"{_safe(asset)}.svg"
        svg_path.write_text(svg)
        renders = {}
        if render_outputs:
            for palette in PALETTES:
                renders[palette] = _render_svg(svg, asset, palette)
        rows.append({
            "asset": asset,
            "name": item.get("name") or source_row.get("name"),
            "queue_action": item.get("status") or "standard_repair_queue_consumed",
            "risk_bucket": "standard_repair_queue_batch18_high_confidence_subset",
            "candidate_strategy": "owned_redraw_from_standard_repair_queue",
            "candidate_source": item.get("helm_candidate", {}).get("canonical_svg")
            or source_row.get("helm_candidate", {}).get("canonical_svg"),
            "before_svg": item.get("helm_candidate", {}).get("canonical_svg")
            or source_row.get("helm_candidate", {}).get("canonical_svg"),
            "after_svg": str(svg_path.relative_to(ROOT)),
            "after_renders": renders,
            "repair_note": REPAIR_NOTES[asset],
            "required_change": _required_change(item),
            "safety_reason_codes": _safety_codes(item),
            "semantic_brief": item.get("semantic_brief") or source_row.get("semantic_brief"),
            "visual_examples": item.get("reference_providers") or source_row.get("reference_providers", {}),
            "qa": {
                "semantic_pass": False,
                "structural_pass": True,
                "visual_parity": "repaired_pending_judge_rerun",
                "final_approved": False,
            },
            "provenance": {
                "origin": "generated-owned-artwork",
                "source_priority_basis": "standard_repair_queue",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch10",
                "reference_role": "semantic_brief/provider refs are shape witnesses; SVG is owned redraw",
            },
            "source_judge": _source_judge_for(item),
        })

    result = {
        "schema_version": 1,
        "status": "repair_batch_pending_judge_rerun",
        "source_queue": str(SOURCE_QUEUE.relative_to(ROOT)),
        "outputs": {
            "svg_dir": str(SVG_OUT.relative_to(ROOT)),
            "catalog": str(REPORT.relative_to(ROOT)),
            "renders": str((OUT / "renders").relative_to(ROOT)) if render_outputs else None,
        },
        "summary": {
            "source_queue_rows": len(actual_queue),
            "expected_queue_rows": len(EXPECTED_QUEUE),
            "failed_repaired": len(rows),
            "blocked_or_skipped": len(blockers),
            "visual_parity": "repaired_pending_judge_rerun",
        },
        "symbols": rows,
        "blockers": blockers,
    }
    REPORT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    _write_summary(result)
    return result


def _write_summary(result: dict) -> None:
    lines = [
        "# Standard Repair Batch 10 / Owned Repair Batch 18",
        "",
        "Owned redraws for a bounded high-confidence subset of the current 163-row standard repair queue.",
        "",
    ]
    for key, value in result["summary"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Repaired", ""])
    for row in result["symbols"]:
        lines.append(f"- `{row['asset']}`: {row.get('repair_note')}")
    lines.extend(["", "## Blocked / skipped", ""])
    for row in result["blockers"]:
        lines.append(f"- `{row['asset']}`: {row['status']} - {row.get('required_change')}")
    lines.extend(["", "Rows remain pending judge rerun; none are final-approved."])
    SUMMARY.write_text("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args(argv)
    result = build(render_outputs=args.render)
    print(json.dumps({
        "status": result["status"],
        "summary": result["summary"],
        "outputs": result["outputs"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
