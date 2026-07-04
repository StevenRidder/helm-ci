"""Build a standards-first review pack for topmark repair.

This pass intentionally separates evidence from generated Helm artwork.  The
standard reference SVGs below are compact shape witnesses for TOPSHP /
topmarkDaymarkShape, used to tell a judge or renderer what silhouette/count/
orientation the final owned artwork must match.

Run:
  python3 -m forge.topmark_standards_pass
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import re
import textwrap
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from . import render, style_contract
from .source_priority_icon_pack import _inline_s101_svg


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
OUT = ROOT / "out" / "topmark_standards_pass"
SOURCE_TABLE = CATALOG / "standard_source_table.json"
SIGNOFF_CSV = ROOT / "out" / "human_review" / "icon_review_signoff.csv"
FEEDBACK_CSV = ROOT / "out" / "human_review" / "icon_review_feedback.csv"
S101_REGISTRY = CATALOG / "s101_reference_registry.json"
S101_ROOTS = (
    Path("/tmp/s101-audit"),
    ROOT / "reference_sources" / "s101_portrayal_catalogue",
)

OUT_JSON = CATALOG / "topmark_standards_pass.json"
OUT_CSV = CATALOG / "topmark_standards_pass.csv"
OUT_MD = CATALOG / "topmark_standards_pass.md"
OUT_HTML = OUT / "index.html"
STD_SVG = OUT / "standard_svg"
STD_PNG = OUT / "standard_png"
STD_SHEET = OUT / "topmark_standard_reference_sheet.png"
S101_SVG = OUT / "s101_svg"
S101_PNG = OUT / "s101_png"
CANDIDATE_PNG = OUT / "candidate_png"

ASSET_RE = re.compile(r"^(TOPMAR|TOPSHP|TOPMA)")
TOPSHP_CODE_RE = re.compile(r"^TOPSHP([0-9]{2})")
TOPMAR_CODE_RE = re.compile(r"^TOPMAR([0-9]{2})")

REFERENCES = [
    {
        "id": "s57-appendix-a-tophsp",
        "label": "IHO S-57 Appendix A, Chapter 2, attribute TOPSHP",
        "url": "https://iho.int/uploads/user/pubs/standards/s-57/31ApAch2.pdf",
        "role": "official code list for topmark shape values 1-33",
        "source_boundary": "standards metadata only",
    },
    {
        "id": "s101-feature-catalogue-topmark-daymark-shape",
        "label": "S-101 Feature Catalogue topmarkDaymarkShape / TOPSHP",
        "url": "https://services.data.shom.fr/static/jeux_test/S-101_FC.htm",
        "role": "S-101 successor attribute values for topmark/daymark shape",
        "source_boundary": "standards metadata only",
    },
    {
        "id": "s101-topmar02-lua",
        "label": "IHO S-101 TOPMAR02.lua portrayal rule",
        "url": "https://raw.githubusercontent.com/iho-ohi/S-101_Portrayal-Catalogue/main/PortrayalCatalog/Rules/TOPMAR02.lua",
        "role": "rule-derived mapping from topmarkDaymarkShape to point instructions",
        "source_boundary": "rule/reference evidence only; not canonical Helm artwork",
    },
    {
        "id": "noaa-nga-chart1-section-q",
        "label": "NOAA/NGA Chart No. 1 Section Q",
        "url": "https://msi.nga.mil/api/publications/download?key=16694005%2FSFH00000%2FSec_Q.pdf",
        "role": "public chart-symbol witness for buoy/topmark families",
        "source_boundary": "public-domain reference/crop evidence only",
    },
    {
        "id": "canada-chart1-topmarks",
        "label": "Canadian Chart 1, Q topmarks",
        "url": "https://charts.gc.ca/publications/chart1-carte1/sections/q-buoys/topmarks-eng.html",
        "role": "human-readable reference page for common topmark shapes",
        "source_boundary": "reference/comparison only",
    },
]


@dataclass(frozen=True)
class Shape:
    code: int
    name: str
    geometry: str
    s101_supported: bool = True

    @property
    def symbol_id(self) -> str:
        return f"TOPSHP{self.code:02d}"

    @property
    def svg_name(self) -> str:
        return f"{self.symbol_id}.svg"

    @property
    def png_name(self) -> str:
        return f"{self.symbol_id}.png"


SHAPES: tuple[Shape, ...] = (
    Shape(1, "cone, point up", "single upward cone/triangle"),
    Shape(2, "cone, point down", "single downward cone/triangle"),
    Shape(3, "sphere", "single circle/sphere"),
    Shape(4, "two spheres", "two stacked circles/spheres"),
    Shape(5, "cylinder", "upright cylinder/can"),
    Shape(6, "board", "rectangular board"),
    Shape(7, "X-shaped", "diagonal cross"),
    Shape(8, "upright cross", "orthogonal cross"),
    Shape(9, "cube, point up", "diamond/square on point"),
    Shape(10, "two cones, point to point", "opposed cones with tips meeting"),
    Shape(11, "two cones, base to base", "opposed cones with bases meeting"),
    Shape(12, "rhombus", "diamond/rhombus"),
    Shape(13, "two cones, points upward", "two stacked upward cones"),
    Shape(14, "two cones, points downward", "two stacked downward cones"),
    Shape(15, "besom, point up", "besom/broom with point up"),
    Shape(16, "besom, point down", "besom/broom with point down"),
    Shape(17, "flag", "staff and flag"),
    Shape(18, "sphere over rhombus", "circle above diamond"),
    Shape(19, "square", "square board"),
    Shape(20, "rectangle, horizontal", "wide horizontal rectangle"),
    Shape(21, "rectangle, vertical", "tall vertical rectangle"),
    Shape(22, "trapezium, up", "trapezium with narrow top and wide base"),
    Shape(23, "trapezium, down", "trapezium with wide top and narrow base"),
    Shape(24, "triangle, point up", "triangle point up"),
    Shape(25, "triangle, point down", "triangle point down"),
    Shape(26, "circle", "circle"),
    Shape(27, "two upright crosses", "two stacked orthogonal crosses"),
    Shape(28, "T-shape", "capital T shape"),
    Shape(29, "triangle over circle", "upward triangle above circle"),
    Shape(30, "upright cross over circle", "orthogonal cross above circle"),
    Shape(31, "rhombus over circle", "diamond above circle"),
    Shape(32, "circle over triangle, point up", "circle above upward triangle"),
    Shape(33, "other", "explicit manual/other topmark shape", False),
)


# S-101 PortrayalCatalog/Rules/TOPMAR02.lua.  These are rule evidence, not
# canonical Helm artwork.  Inversion is intentionally kept because many S-101
# point instructions represent several TOPSHP values.
FLOATING_TOPMARKS = {
    1: "TOPMAR02",
    2: "TOPMAR04",
    3: "TOPMAR10",
    4: "TOPMAR12",
    5: "TOPMAR13",
    6: "TOPMAR14",
    7: "TOPMAR65",
    8: "TOPMAR17",
    9: "TOPMAR16",
    10: "TOPMAR08",
    11: "TOPMAR07",
    12: "TOPMAR14",
    13: "TOPMAR05",
    14: "TOPMAR06",
    15: "TMARDEF2",
    16: "TMARDEF2",
    17: "TMARDEF2",
    18: "TOPMAR10",
    19: "TOPMAR13",
    20: "TOPMAR14",
    21: "TOPMAR13",
    22: "TOPMAR14",
    23: "TOPMAR14",
    24: "TOPMAR02",
    25: "TOPMAR04",
    26: "TOPMAR10",
    27: "TOPMAR17",
    28: "TOPMAR18",
    29: "TOPMAR02",
    30: "TOPMAR17",
    31: "TOPMAR14",
    32: "TOPMAR10",
    33: "TMARDEF2",
}

RIGID_TOPMARKS = {
    1: "TOPMAR22",
    2: "TOPMAR24",
    3: "TOPMAR30",
    4: "TOPMAR32",
    5: "TOPMAR33",
    6: "TOPMAR34",
    7: "TOPMAR85",
    8: "TOPMAR86",
    9: "TOPMAR36",
    10: "TOPMAR28",
    11: "TOPMAR27",
    12: "TOPMAR14",
    13: "TOPMAR25",
    14: "TOPMAR26",
    15: "TOPMAR88",
    16: "TOPMAR87",
    17: "TMARDEF1",
    18: "TOPMAR30",
    19: "TOPMAR33",
    20: "TOPMAR34",
    21: "TOPMAR33",
    22: "TOPMAR34",
    23: "TOPMAR34",
    24: "TOPMAR22",
    25: "TOPMAR24",
    26: "TOPMAR30",
    27: "TOPMAR86",
    28: "TOPMAR89",
    29: "TOPMAR22",
    30: "TOPMAR86",
    31: "TOPMAR14",
    32: "TOPMAR30",
    33: "TMARDEF1",
}


def _shape_by_code(code: int) -> Shape | None:
    return next((shape for shape in SHAPES if shape.code == code), None)


def _invert(mapping: dict[int, str]) -> dict[str, list[int]]:
    out: dict[str, list[int]] = defaultdict(list)
    for code, symbol in mapping.items():
        out[symbol].append(code)
    return {key: sorted(value) for key, value in sorted(out.items())}


def _root(body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" '
        'width="64" height="64" data-origin="generated-owned-standard-reference" '
        'data-style="helm-topmark-standard-reference-v1">'
        "<style>"
        ".mark{fill:var(--black);stroke:var(--black);stroke-linecap:round;stroke-linejoin:round}"
        ".outline{fill:none;stroke:var(--black);stroke-linecap:round;stroke-linejoin:round}"
        ".thin{stroke-width:4}.med{stroke-width:6}.heavy{stroke-width:8}"
        "</style>"
        f"{body}</svg>\n"
    )


def _tri(up: bool, cx: float = 32, y1: float = 12, y2: float = 50, w: float = 34) -> str:
    if up:
        return f'<polygon class="mark" points="{cx},{y1} {cx - w / 2},{y2} {cx + w / 2},{y2}"/>'
    return f'<polygon class="mark" points="{cx - w / 2},{y1} {cx + w / 2},{y1} {cx},{y2}"/>'


def _circle(cx: float = 32, cy: float = 32, r: float = 14) -> str:
    return f'<circle class="mark" cx="{cx}" cy="{cy}" r="{r}"/>'


def _rect(x: float, y: float, w: float, h: float, rx: float = 0) -> str:
    rx_attr = f' rx="{rx}"' if rx else ""
    return f'<rect class="mark" x="{x}" y="{y}" width="{w}" height="{h}"{rx_attr}/>'


def _diamond(cx: float = 32, cy: float = 32, r: float = 18) -> str:
    return f'<polygon class="mark" points="{cx},{cy - r} {cx + r},{cy} {cx},{cy + r} {cx - r},{cy}"/>'


def standard_svg(shape: Shape) -> str:
    code = shape.code
    if code == 1:
        body = _tri(True)
    elif code == 2:
        body = _tri(False)
    elif code == 3:
        body = _circle()
    elif code == 4:
        body = _circle(32, 21, 9) + _circle(32, 43, 9)
    elif code == 5:
        body = (
            '<rect class="mark" x="20" y="16" width="24" height="36" rx="4"/>'
            '<ellipse cx="32" cy="16" rx="12" ry="5" fill="var(--black)"/>'
        )
    elif code == 6:
        body = _rect(13, 22, 38, 20, 2)
    elif code == 7:
        body = (
            '<line class="mark med" x1="17" y1="17" x2="47" y2="47"/>'
            '<line class="mark med" x1="47" y1="17" x2="17" y2="47"/>'
        )
    elif code == 8:
        body = (
            '<line class="mark med" x1="32" y1="13" x2="32" y2="51"/>'
            '<line class="mark med" x1="15" y1="32" x2="49" y2="32"/>'
        )
    elif code == 9:
        body = _diamond()
    elif code == 10:
        body = (
            '<polygon class="mark" points="18,10 46,10 32,31"/>'
            '<polygon class="mark" points="32,33 18,54 46,54"/>'
        )
    elif code == 11:
        body = (
            '<polygon class="mark" points="32,10 18,32 46,32"/>'
            '<polygon class="mark" points="18,32 46,32 32,54"/>'
        )
    elif code == 12:
        body = _diamond()
    elif code == 13:
        body = _tri(True, 32, 7, 27, 25) + _tri(True, 32, 34, 56, 25)
    elif code == 14:
        body = _tri(False, 32, 8, 30, 25) + _tri(False, 32, 37, 58, 25)
    elif code == 15:
        body = (
            '<polygon class="mark" points="32,8 22,34 42,34"/>'
            '<line class="mark thin" x1="32" y1="34" x2="32" y2="56"/>'
            '<line class="mark thin" x1="24" y1="42" x2="40" y2="42"/>'
        )
    elif code == 16:
        body = (
            '<line class="mark thin" x1="32" y1="8" x2="32" y2="30"/>'
            '<line class="mark thin" x1="24" y1="22" x2="40" y2="22"/>'
            '<polygon class="mark" points="22,30 42,30 32,56"/>'
        )
    elif code == 17:
        body = (
            '<line class="mark thin" x1="22" y1="12" x2="22" y2="54"/>'
            '<path class="mark" d="M24 13H49L43 25L49 37H24Z"/>'
        )
    elif code == 18:
        body = _circle(32, 18, 9) + _diamond(32, 43, 14)
    elif code == 19:
        body = _rect(20, 20, 24, 24, 1)
    elif code == 20:
        body = _rect(12, 24, 40, 16, 1)
    elif code == 21:
        body = _rect(24, 12, 16, 40, 1)
    elif code == 22:
        body = '<polygon class="mark" points="23,16 41,16 50,49 14,49"/>'
    elif code == 23:
        body = '<polygon class="mark" points="14,15 50,15 41,48 23,48"/>'
    elif code == 24:
        body = _tri(True)
    elif code == 25:
        body = _tri(False)
    elif code == 26:
        body = _circle()
    elif code == 27:
        body = (
            '<line class="mark thin" x1="32" y1="8" x2="32" y2="28"/>'
            '<line class="mark thin" x1="22" y1="18" x2="42" y2="18"/>'
            '<line class="mark thin" x1="32" y1="36" x2="32" y2="56"/>'
            '<line class="mark thin" x1="22" y1="46" x2="42" y2="46"/>'
        )
    elif code == 28:
        body = (
            '<line class="mark heavy" x1="16" y1="16" x2="48" y2="16"/>'
            '<line class="mark heavy" x1="32" y1="16" x2="32" y2="52"/>'
        )
    elif code == 29:
        body = _tri(True, 32, 6, 28, 25) + _circle(32, 46, 9)
    elif code == 30:
        body = (
            '<line class="mark thin" x1="32" y1="7" x2="32" y2="29"/>'
            '<line class="mark thin" x1="21" y1="18" x2="43" y2="18"/>'
            + _circle(32, 47, 9)
        )
    elif code == 31:
        body = _diamond(32, 18, 11) + _circle(32, 47, 9)
    elif code == 32:
        body = _circle(32, 17, 9) + _tri(True, 32, 33, 58, 26)
    elif code == 33:
        body = (
            '<circle class="outline thin" cx="32" cy="32" r="20"/>'
            '<path class="outline thin" d="M25 25c1-7 14-8 14 1c0 7-8 7-8 13"/>'
            '<circle class="mark" cx="32" cy="48" r="2.8"/>'
        )
    else:
        raise ValueError(f"unknown TOPSHP shape code {code}")
    return _root(body)


def _safe_name(asset: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", asset)


def _read_rows() -> list[dict]:
    return json.loads(SOURCE_TABLE.read_text())["rows"]


def _read_s101_registry() -> dict:
    return json.loads(S101_REGISTRY.read_text())


def _s101_topmark_rows() -> list[dict]:
    registry = _read_s101_registry()
    rows = [
        row
        for row in registry["svg_symbols"]
        if row["id"].startswith("TOPMAR") or row["id"].startswith("TMARDEF")
    ]
    return sorted(rows, key=lambda row: row["id"])


def _resolve_s101_source(symbol_file: str | None) -> Path | None:
    if not symbol_file:
        return None
    for root in S101_ROOTS:
        candidate = root / symbol_file
        if candidate.exists():
            return candidate
    return None


def _read_approved_and_rejected() -> tuple[set[str], set[str]]:
    approved: set[str] = set()
    rejected: set[str] = set()
    if SIGNOFF_CSV.exists():
        with SIGNOFF_CSV.open() as handle:
            for row in csv.DictReader(handle):
                asset = row.get("asset") or ""
                if row.get("final_decision") == "approve" or row.get("final_approved") == "True":
                    approved.add(asset)
                if row.get("final_decision") == "reject_remediate":
                    rejected.add(asset)
    if FEEDBACK_CSV.exists():
        with FEEDBACK_CSV.open() as handle:
            for row in csv.DictReader(handle):
                asset = row.get("asset") or ""
                if asset:
                    rejected.add(asset)
    return approved, rejected


def _shape_from_s57_conditions(row: dict) -> dict | None:
    conditions = (row.get("s57_structure") or {}).get("conditions") or []
    for condition in conditions:
        match = re.match(r"TOPSHP([0-9]{1,2})\b", str(condition))
        if not match:
            continue
        code = int(match.group(1))
        shape = _shape_by_code(code)
        if not shape:
            continue
        return {
            "shape_code": code,
            "shape_id": shape.symbol_id,
            "shape_name": shape.name,
            "basis": "s57_structure_conditions_TOPSHP",
            "confidence": 0.99,
            "ambiguous": False,
            "candidate_shape_codes": [code],
            "source_condition": condition,
        }
    return None


def _shape_from_name(text: str) -> dict | None:
    lower = text.lower()
    if "cone" in lower and "point down" in lower:
        return {"shape_code": 2, "basis": "row_name_inferred_cone_point_down", "confidence": 0.74}
    if "cone" in lower and "point up" in lower:
        return {"shape_code": 1, "basis": "row_name_inferred_cone_point_up", "confidence": 0.74}
    if "two spheres" in lower or "two shere" in lower or "two sphere" in lower:
        return {"shape_code": 4, "basis": "row_name_inferred_two_spheres", "confidence": 0.72}
    if "sphere over rhombus" in lower:
        return {"shape_code": 18, "basis": "row_name_inferred_sphere_over_rhombus", "confidence": 0.75}
    if "sphere" in lower or "shere" in lower:
        return {"shape_code": 3, "basis": "row_name_inferred_sphere", "confidence": 0.62}
    if "st.georg" in lower or "st georg" in lower or "george cross" in lower:
        return {"shape_code": 8, "basis": "row_name_inferred_upright_cross", "confidence": 0.70}
    if "andreas" in lower or "x-shaped" in lower:
        return {"shape_code": 7, "basis": "row_name_inferred_x_cross", "confidence": 0.70}
    if "diamond" in lower or "rhombus" in lower:
        return {"shape_code": 12, "basis": "row_name_inferred_rhombus", "confidence": 0.68}
    if "circle" in lower or "round board" in lower:
        return {"shape_code": 26, "basis": "row_name_inferred_circle", "confidence": 0.60}
    if "square board" in lower and "diagonal" in lower:
        return {"shape_code": 12, "basis": "row_name_inferred_diagonal_square_board", "confidence": 0.56}
    if "square" in lower:
        return {"shape_code": 19, "basis": "row_name_inferred_square", "confidence": 0.56}
    if "vertical" in lower and "board" in lower:
        return {"shape_code": 21, "basis": "row_name_inferred_vertical_board", "confidence": 0.50}
    if "board" in lower:
        return {"shape_code": 6, "basis": "row_name_inferred_board", "confidence": 0.46}
    if "pricken" in lower and "point down" in lower:
        return {"shape_code": 16, "basis": "row_name_inferred_pricken_point_down_as_besom_family", "confidence": 0.42}
    if "pricken" in lower and "point up" in lower:
        return {"shape_code": 15, "basis": "row_name_inferred_pricken_point_up_as_besom_family", "confidence": 0.42}
    return None


def _resolve_expected_shape(asset: str, row: dict, floating_inverse: dict[str, list[int]], rigid_inverse: dict[str, list[int]]) -> dict:
    from_conditions = _shape_from_s57_conditions(row)
    if from_conditions:
        return from_conditions

    topshp = TOPSHP_CODE_RE.match(asset)
    if topshp:
        code = int(topshp.group(1))
        shape = _shape_by_code(code)
        if shape:
            return {
                "shape_code": code,
                "shape_id": shape.symbol_id,
                "shape_name": shape.name,
                "basis": "asset_id_tophsp_code",
                "confidence": 0.98 if code < 33 else 0.40,
                "ambiguous": False,
                "candidate_shape_codes": [code],
            }
        inferred = _shape_from_name(row.get("name") or "")
        if inferred:
            return {
                **inferred,
                "shape_id": f"TOPSHP{inferred['shape_code']:02d}",
                "shape_name": _shape_by_code(inferred["shape_code"]).name,
                "ambiguous": False,
                "candidate_shape_codes": [inferred["shape_code"]],
            }
        return {
            "shape_code": None,
            "shape_id": None,
            "shape_name": None,
            "basis": "asset_id_tophsp_code_outside_official_1_33",
            "confidence": 0.0,
            "ambiguous": True,
            "candidate_shape_codes": [],
        }

    topmar = TOPMAR_CODE_RE.match(asset)
    if topmar:
        floating = floating_inverse.get(asset, [])
        rigid = rigid_inverse.get(asset, [])
        codes = sorted(set(floating + rigid))
        if len(codes) == 1:
            shape = _shape_by_code(codes[0])
            return {
                "shape_code": codes[0],
                "shape_id": shape.symbol_id,
                "shape_name": shape.name,
                "basis": "s101_topmar02_rule_inverse",
                "confidence": 0.86,
                "ambiguous": False,
                "candidate_shape_codes": codes,
                "s101_floating_codes": floating,
                "s101_rigid_codes": rigid,
            }
        if len(codes) > 1:
            names = [_shape_by_code(code).name for code in codes if _shape_by_code(code)]
            return {
                "shape_code": None,
                "shape_id": None,
                "shape_name": "; ".join(names),
                "basis": "s101_topmar02_rule_inverse_ambiguous",
                "confidence": 0.45,
                "ambiguous": True,
                "candidate_shape_codes": codes,
                "s101_floating_codes": floating,
                "s101_rigid_codes": rigid,
            }
        inferred = _shape_from_name(row.get("name") or "")
        if inferred:
            shape = _shape_by_code(inferred["shape_code"])
            return {
                **inferred,
                "shape_id": shape.symbol_id,
                "shape_name": shape.name,
                "ambiguous": False,
                "candidate_shape_codes": [shape.code],
                "s101_floating_codes": [],
                "s101_rigid_codes": [],
            }
        return {
            "shape_code": None,
            "shape_id": None,
            "shape_name": None,
            "basis": "topmar_symbol_not_present_in_s101_topmar02_map",
            "confidence": 0.0,
            "ambiguous": True,
            "candidate_shape_codes": [],
            "s101_floating_codes": [],
            "s101_rigid_codes": [],
        }

    inferred = _shape_from_name(row.get("name") or "")
    if inferred:
        shape = _shape_by_code(inferred["shape_code"])
        return {
            **inferred,
            "shape_id": shape.symbol_id,
            "shape_name": shape.name,
            "ambiguous": False,
            "candidate_shape_codes": [shape.code],
        }
    return {
        "shape_code": None,
        "shape_id": None,
        "shape_name": None,
        "basis": "legacy_topma_row_requires_manual_mapping",
        "confidence": 0.0,
        "ambiguous": True,
        "candidate_shape_codes": [],
    }


def _reference_payload(shape: Shape) -> dict:
    floating_symbol = FLOATING_TOPMARKS.get(shape.code)
    rigid_symbol = RIGID_TOPMARKS.get(shape.code)
    return {
        "shape_code": shape.code,
        "shape_id": shape.symbol_id,
        "shape_name": shape.name,
        "geometry": shape.geometry,
        "s57_tophsp": f"TOPSHP={shape.code}",
        "s101_topmarkDaymarkShape": shape.code if shape.s101_supported else "other/manual",
        "s101_floating_point_instruction": floating_symbol,
        "s101_rigid_point_instruction": rigid_symbol,
        "standard_svg": f"out/topmark_standards_pass/standard_svg/{shape.svg_name}",
        "standard_png": f"out/topmark_standards_pass/standard_png/{shape.png_name}",
        "source_refs": [ref["id"] for ref in REFERENCES],
    }


def _render_svg_to_png(svg: str, out_path: Path, size: int = 128) -> bool:
    try:
        png = render.rasterize(svg, style_contract.OPENBRIDGE_NAV_PALETTES["day"], size=size)
    except Exception:
        return False
    out_path.write_bytes(png)
    return True


def _render_file_to_png(svg_path: Path, out_path: Path, size: int = 128) -> bool:
    if not svg_path.exists():
        return False
    return _render_svg_to_png(svg_path.read_text(), out_path, size=size)


def _write_reference_svgs() -> list[dict]:
    STD_SVG.mkdir(parents=True, exist_ok=True)
    STD_PNG.mkdir(parents=True, exist_ok=True)
    references = []
    for shape in SHAPES:
        svg = standard_svg(shape)
        svg_path = STD_SVG / shape.svg_name
        png_path = STD_PNG / shape.png_name
        svg_path.write_text(svg)
        rendered = _render_svg_to_png(svg, png_path)
        entry = _reference_payload(shape)
        entry["rendered"] = rendered
        references.append(entry)
    _write_reference_sheet(references)
    return references


def _write_reference_sheet(references: list[dict]) -> None:
    from PIL import Image, ImageDraw, ImageFont

    cols = 6
    cell_w = 180
    cell_h = 170
    margin = 18
    header_h = 42
    rows = (len(references) + cols - 1) // cols
    img = Image.new("RGB", (margin * 2 + cols * cell_w, margin * 2 + header_h + rows * cell_h), "#f6f7f9")
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    draw.text((margin, margin), "TOPSHP / topmarkDaymarkShape standard shape witnesses", fill="#171a1f", font=font)
    for idx, ref in enumerate(references):
        col = idx % cols
        row = idx // cols
        x = margin + col * cell_w
        y = margin + header_h + row * cell_h
        draw.rounded_rectangle([x, y, x + cell_w - 10, y + cell_h - 10], radius=6, fill="#ffffff", outline="#d8dde3")
        png_path = ROOT / ref["standard_png"]
        if png_path.exists():
            icon = Image.open(png_path).convert("RGBA").resize((92, 92))
            img.paste(icon, (x + (cell_w - 10 - 92) // 2, y + 10), icon)
        draw.text((x + 10, y + 110), ref["shape_id"], fill="#171a1f", font=font)
        for line_idx, line in enumerate(textwrap.wrap(ref["shape_name"], width=24)[:2]):
            draw.text((x + 10, y + 128 + line_idx * 14), line, fill="#404852", font=font)
    img.save(STD_SHEET)


def _write_s101_topmark_witnesses() -> list[dict]:
    S101_SVG.mkdir(parents=True, exist_ok=True)
    S101_PNG.mkdir(parents=True, exist_ok=True)
    witnesses = []
    for row in _s101_topmark_rows():
        source = _resolve_s101_source(row.get("file"))
        svg_out = S101_SVG / f"{row['id']}.svg"
        png_out = S101_PNG / f"{row['id']}.png"
        rendered = False
        if source:
            _inline_s101_svg(row["id"], source, svg_out)
            rendered = _render_file_to_png(svg_out, png_out, size=128)
        witnesses.append({
            "id": row["id"],
            "description": row.get("description"),
            "s101_file": row.get("file"),
            "source_path": str(source) if source else None,
            "local_source_found": bool(source),
            "license_status": row.get("license_status"),
            "allowed_use": row.get("allowed_use"),
            "forbidden_use_until_cleared": row.get("forbidden_use_until_cleared"),
            "viewBox": row.get("viewBox"),
            "width": row.get("width"),
            "height": row.get("height"),
            "svg": f"out/topmark_standards_pass/s101_svg/{svg_out.name}" if svg_out.exists() else None,
            "png": f"out/topmark_standards_pass/s101_png/{png_out.name}" if png_out.exists() else None,
            "rendered": rendered,
        })
    return witnesses


def _s101_witnesses_for_expected(asset: str, row: dict, expected: dict, witnesses_by_id: dict[str, dict]) -> list[dict]:
    out = []

    def add(symbol_id: str | None, role: str) -> None:
        if not symbol_id:
            return
        witness = witnesses_by_id.get(symbol_id)
        if not witness:
            return
        for item in out:
            if item["id"] == symbol_id:
                if role not in item["roles"]:
                    item["roles"].append(role)
                    item["role"] = "; ".join(item["roles"])
                return
        out.append({
            "id": symbol_id,
            "role": role,
            "roles": [role],
            "description": witness.get("description"),
            "s101_file": witness.get("s101_file"),
            "svg": witness.get("svg"),
            "png": witness.get("png"),
            "license_status": witness.get("license_status"),
        })

    code = expected.get("shape_code")
    if isinstance(code, int):
        object_class = ((row.get("s57_structure") or {}).get("object_class") or "").upper()
        name = (row.get("name") or "").lower()
        prefer_rigid = object_class in {"TOPMAR", "DAYMAR"} or "beacon" in name
        prefer_floating = "buoy" in name
        if prefer_rigid and not prefer_floating:
            roles = [("s101_TOPMAR02_rigid_rule_output", RIGID_TOPMARKS.get(code)), ("s101_TOPMAR02_floating_rule_output", FLOATING_TOPMARKS.get(code))]
        elif prefer_floating and not prefer_rigid:
            roles = [("s101_TOPMAR02_floating_rule_output", FLOATING_TOPMARKS.get(code)), ("s101_TOPMAR02_rigid_rule_output", RIGID_TOPMARKS.get(code))]
        else:
            roles = [("s101_TOPMAR02_floating_rule_output", FLOATING_TOPMARKS.get(code)), ("s101_TOPMAR02_rigid_rule_output", RIGID_TOPMARKS.get(code))]
        for role, symbol_id in roles:
            add(symbol_id, role)
    add(asset, "same_asset_id_if_s101_symbol_exists")
    return out


def _queue_rows(rows: list[dict], witnesses_by_id: dict[str, dict]) -> list[dict]:
    approved, rejected = _read_approved_and_rejected()
    floating_inverse = _invert(FLOATING_TOPMARKS)
    rigid_inverse = _invert(RIGID_TOPMARKS)
    CANDIDATE_PNG.mkdir(parents=True, exist_ok=True)
    items = []
    for row in rows:
        asset = row.get("asset") or ""
        if not ASSET_RE.match(asset):
            continue
        if asset in approved:
            continue
        helm = row.get("helm_candidate") or {}
        candidate_svg = helm.get("canonical_svg") or helm.get("source_svg")
        candidate_png = None
        candidate_rendered = False
        if candidate_svg:
            candidate_png_path = CANDIDATE_PNG / f"{_safe_name(asset)}.png"
            candidate_rendered = _render_file_to_png(ROOT / candidate_svg, candidate_png_path)
            if candidate_rendered:
                candidate_png = f"out/topmark_standards_pass/candidate_png/{candidate_png_path.name}"
        expected = _resolve_expected_shape(asset, row, floating_inverse, rigid_inverse)
        s101_witnesses_for_row = _s101_witnesses_for_expected(asset, row, expected, witnesses_by_id)
        shape_code = expected.get("shape_code")
        standard_png = None
        standard_svg = None
        if isinstance(shape_code, int):
            shape = _shape_by_code(shape_code)
            if shape:
                standard_png = f"out/topmark_standards_pass/standard_png/{shape.png_name}"
                standard_svg = f"out/topmark_standards_pass/standard_svg/{shape.svg_name}"
        items.append({
            "asset": asset,
            "name": row.get("name"),
            "family": row.get("family"),
            "candidate_status": helm.get("candidate_status"),
            "final_approved": False,
            "human_rejected": asset in rejected,
            "source_batch": helm.get("source_batch"),
            "candidate_svg": candidate_svg,
            "candidate_png": candidate_png,
            "candidate_rendered": candidate_rendered,
            "expected_shape": expected,
            "s101_witnesses": s101_witnesses_for_row,
            "standard_svg": standard_svg,
            "standard_png": standard_png,
            "semantic_brief": row.get("semantic_brief"),
            "s57_structure": row.get("s57_structure"),
            "llm_instruction": _llm_instruction(row, expected),
        })
    return sorted(items, key=lambda item: item["asset"])


def _llm_instruction(row: dict, expected: dict) -> str:
    asset = row.get("asset") or ""
    name = row.get("name") or asset
    basis = expected.get("basis")
    if expected.get("shape_code"):
        return (
            f"Render {asset} as a Helm-owned topmark/daymark SVG. Match the official "
            f"{expected['shape_id']} shape exactly for silhouette, count, and orientation: "
            f"{expected['shape_name']}. Use row colours/bands from metadata when present, "
            "but do not substitute a different topmark family. Compare against the standard "
            f"shape witness first; row name is secondary. Basis: {basis}. Name: {name}."
        )
    return (
        f"Do not invent final artwork for {asset}. First resolve the exact official topmark "
        f"shape from S-57/S-101/Chart No.1 evidence, because this row is ambiguous. "
        f"Basis: {basis}. Name: {name}."
    )


def build() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    references = _write_reference_svgs()
    s101_witnesses = _write_s101_topmark_witnesses()
    witnesses_by_id = {witness["id"]: witness for witness in s101_witnesses}
    rows = _read_rows()
    queue = _queue_rows(rows, witnesses_by_id)
    basis_counts = Counter(item["expected_shape"]["basis"] for item in queue)
    status_counts = Counter(item["candidate_status"] for item in queue)
    shape_counts = Counter(
        item["expected_shape"]["shape_id"] or "unresolved"
        for item in queue
    )
    summary = {
        "standard_shape_refs": len(references),
        "topmark_rows_needing_special_pass": len(queue),
        "resolved_exact_or_inferred_shape_rows": sum(1 for item in queue if item["expected_shape"].get("shape_code")),
        "ambiguous_or_unresolved_rows": sum(1 for item in queue if not item["expected_shape"].get("shape_code")),
        "human_rejected_rows": sum(1 for item in queue if item["human_rejected"]),
        "candidate_png_rendered_rows": sum(1 for item in queue if item["candidate_rendered"]),
        "s101_topmark_svg_entries": len(s101_witnesses),
        "s101_topmark_svg_sources_found": sum(1 for witness in s101_witnesses if witness["local_source_found"]),
        "s101_topmark_png_rendered": sum(1 for witness in s101_witnesses if witness["rendered"]),
        "rows_with_s101_witnesses": sum(1 for item in queue if item["s101_witnesses"]),
        "basis_counts": dict(sorted(basis_counts.items())),
        "candidate_status_counts": dict(sorted(status_counts.items())),
        "shape_counts": dict(sorted(shape_counts.items())),
    }
    result = {
        "schema": "helm.iconforge.topmark_standards_pass.v1",
        "project": "vulkan",
        "task_ids": ["FORGE-15", "FORGE-24"],
        "status": "topmark_standards_pass_written",
        "source_table": "catalog/standard_source_table.json",
        "policy": {
            "purpose": "Exact-shape topmark evidence pack for LLM judge/repair comparison.",
            "clean_ip_boundary": "Standard references and Chart No.1/S-101/OpenCPN output are comparison evidence; Helm canonical assets remain generated-owned artwork.",
            "promotion_rule": "No topmark row is final-approved by this pass. The pass only supplies exact shape evidence and repair instructions.",
        },
        "references": REFERENCES,
        "s101_topmar02_mapping": {
            "floating_topmarks": FLOATING_TOPMARKS,
            "rigid_topmarks": RIGID_TOPMARKS,
            "floating_symbol_to_shape_codes": _invert(FLOATING_TOPMARKS),
            "rigid_symbol_to_shape_codes": _invert(RIGID_TOPMARKS),
        },
        "standard_shapes": references,
        "standard_reference_sheet": "out/topmark_standards_pass/topmark_standard_reference_sheet.png",
        "s101_topmark_witnesses": s101_witnesses,
        "summary": summary,
        "queue": queue,
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    _write_csv(queue)
    _write_md(result)
    _write_html(result)
    return result


def _write_csv(queue: list[dict]) -> None:
    fields = [
        "asset",
        "name",
        "candidate_status",
        "human_rejected",
        "expected_shape_id",
        "expected_shape_name",
        "basis",
        "confidence",
        "s101_witness_ids",
        "s101_witness_files",
        "candidate_svg",
        "standard_svg",
        "llm_instruction",
    ]
    with OUT_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for item in queue:
            expected = item["expected_shape"]
            writer.writerow({
                "asset": item["asset"],
                "name": item.get("name") or "",
                "candidate_status": item.get("candidate_status") or "",
                "human_rejected": item.get("human_rejected"),
                "expected_shape_id": expected.get("shape_id") or "",
                "expected_shape_name": expected.get("shape_name") or "",
                "basis": expected.get("basis") or "",
                "confidence": expected.get("confidence"),
                "s101_witness_ids": ",".join(witness["id"] for witness in item.get("s101_witnesses", [])),
                "s101_witness_files": ",".join(witness.get("s101_file") or "" for witness in item.get("s101_witnesses", [])),
                "candidate_svg": item.get("candidate_svg") or "",
                "standard_svg": item.get("standard_svg") or "",
                "llm_instruction": item.get("llm_instruction") or "",
            })


def _write_md(result: dict) -> None:
    lines = [
        "# Topmark Standards Pass",
        "",
        "Dedicated topmark/daymark evidence pack for the LLM judge/repair loop.",
        "",
        "## Summary",
        "",
    ]
    for key, value in result["summary"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Sources", ""])
    for ref in result["references"]:
        lines.append(f"- [{ref['label']}]({ref['url']}) - {ref['role']}")
    lines.extend(["", "## S-101 Topmark SVG Witnesses", ""])
    for witness in result["s101_topmark_witnesses"]:
        lines.append(
            f"- `{witness['id']}`: {witness['description']} "
            f"(`{witness['s101_file']}`, local={witness['local_source_found']}, rendered={witness['rendered']})"
        )
    lines.extend(["", "## Standard Shapes", ""])
    for shape in result["standard_shapes"]:
        lines.append(
            f"- `{shape['shape_id']}`: {shape['shape_name']} "
            f"(floating `{shape['s101_floating_point_instruction']}`, rigid `{shape['s101_rigid_point_instruction']}`)"
        )
    lines.extend(["", "## Queue", ""])
    for item in result["queue"]:
        expected = item["expected_shape"]
        lines.append(
            f"- `{item['asset']}` -> `{expected.get('shape_id') or 'unresolved'}` "
            f"{expected.get('shape_name') or ''} [{expected.get('basis')}]"
        )
    OUT_MD.write_text("\n".join(lines).rstrip() + "\n")


def _rel(path: str | None) -> str | None:
    if not path:
        return None
    if path.startswith("out/"):
        return "../.." + "/" + path
    if path.startswith("assets/"):
        return "../.." + "/" + path
    return path


def _img(path: str | None, alt: str) -> str:
    if not path:
        return '<div class="missing">No witness</div>'
    safe = html.escape(_rel(path) or "")
    return f'<img loading="lazy" src="{safe}" alt="{html.escape(alt)}">'


def _role_text(role: str | None) -> str:
    if not role:
        return "S-101 witness"
    return (
        role.replace("s101_TOPMAR02_", "TOPMAR02 ")
        .replace("_rule_output", " rule")
        .replace("same_asset_id_if_s101_symbol_exists", "same S-52/S-101 asset id")
        .replace("_", " ")
    )


def _s101_witness_html(witnesses: list[dict]) -> str:
    if not witnesses:
        return '<div class="missing">No S-101 TOPMAR witness</div>'
    primary = witnesses[0]
    chunks = []
    primary_label = f"{primary['id']} - {_role_text(primary.get('role'))}"
    chunks.append(
        "<div class='s101primary'>"
        f"{_img(primary.get('png') or primary.get('svg'), primary_label)}"
        f"<b>{html.escape(primary['id'])}</b>"
        f"<span>{html.escape(_role_text(primary.get('role')))}</span>"
        f"<small>{html.escape(primary.get('description') or '')}</small>"
        "</div>"
    )
    if len(witnesses) > 1:
        chunks.append("<div class='s101alts'>")
    for witness in witnesses[1:4]:
        label = f"{witness['id']} - {_role_text(witness.get('role'))}"
        chunks.append(
            "<div class='s101item'>"
            f"{_img(witness.get('png') or witness.get('svg'), label)}"
            f"<span><b>{html.escape(witness['id'])}</b><br>{html.escape(_role_text(witness.get('role')))}</span>"
            "</div>"
        )
    if len(witnesses) > 1:
        chunks.append("</div>")
    return "<div class='s101grid'>" + "".join(chunks) + "</div>"


def _write_html(result: dict) -> None:
    summary = result["summary"]
    cards = []
    for item in result["queue"]:
        expected = item["expected_shape"]
        s101_primary = (item.get("s101_witnesses") or [{}])[0]
        cards.append(
            "<section class='row'>"
            "<div class='meta'>"
            f"<h2>{html.escape(item['asset'])}</h2>"
            f"<p>{html.escape(item.get('name') or item['asset'])}</p>"
            f"<p><b>Expected:</b> {html.escape(expected.get('shape_id') or 'unresolved')} "
            f"{html.escape(expected.get('shape_name') or '')}</p>"
            f"<p><b>Basis:</b> {html.escape(expected.get('basis') or '')} "
            f"({expected.get('confidence')})</p>"
            f"<p><b>S-101 primary:</b> {html.escape(s101_primary.get('id') or 'none')} "
            f"{html.escape(_role_text(s101_primary.get('role')) if s101_primary else '')}</p>"
            f"<p><b>Status:</b> {html.escape(item.get('candidate_status') or '')}</p>"
            f"<p><b>Instruction:</b> {html.escape(item['llm_instruction'])}</p>"
            "</div>"
            "<div class='compare'>"
            "<figure><figcaption>Standard shape witness</figcaption>"
            f"{_img(item.get('standard_png'), 'standard shape')}</figure>"
            "<figure><figcaption>S-101 TOPMAR witness</figcaption>"
            f"{_s101_witness_html(item.get('s101_witnesses') or [])}</figure>"
            "<figure><figcaption>Current Helm candidate</figcaption>"
            f"{_img(item.get('candidate_png') or item.get('candidate_svg'), 'candidate')}</figure>"
            "</div>"
            "</section>"
        )
    source_links = "\n".join(
        f"<li><a href='{html.escape(ref['url'])}'>{html.escape(ref['label'])}</a> - {html.escape(ref['role'])}</li>"
        for ref in result["references"]
    )
    OUT_HTML.write_text(
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>Topmark Standards Pass</title>"
        "<style>"
        "body{font-family:Inter,Arial,sans-serif;margin:0;background:#f5f6f7;color:#171a1f}"
        "header{position:sticky;top:0;background:#ffffff;border-bottom:1px solid #d8dde3;padding:18px 22px;z-index:1}"
        "h1{font-size:24px;margin:0 0 8px} h2{font-size:18px;margin:0 0 8px}"
        ".stats{display:flex;gap:10px;flex-wrap:wrap}.stat{background:#eef2f6;border:1px solid #d8dde3;padding:8px 10px;border-radius:6px}"
        "main{max-width:1320px;margin:0 auto;padding:18px 20px 40px}.sources{background:#fff;border:1px solid #d8dde3;border-radius:6px;padding:14px 18px;margin-bottom:16px}"
        ".row{display:grid;grid-template-columns:minmax(280px,1fr) 620px;gap:18px;background:#fff;border:1px solid #d8dde3;border-radius:6px;margin:14px 0;padding:16px}"
        ".meta p{margin:6px 0;line-height:1.35}.compare{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px}"
        "figure{margin:0;border:1px solid #d8dde3;border-radius:6px;background:#fff;min-height:180px;display:flex;flex-direction:column;align-items:center;justify-content:center}"
        "figcaption{font-size:13px;font-weight:700;color:#404852;margin:10px 0 6px}img{width:128px;height:128px;object-fit:contain;image-rendering:auto}.missing{color:#8a2f2f;font-weight:700;padding:20px;text-align:center}"
        ".s101grid{display:grid;grid-template-columns:1fr;gap:8px;width:100%;padding:0 10px 10px;box-sizing:border-box}.s101primary{display:grid;grid-template-columns:1fr;justify-items:center;gap:4px;text-align:center;color:#242a31}.s101primary img{width:128px;height:128px}.s101primary b{font-size:14px}.s101primary span{font-size:12px;color:#404852}.s101primary small{font-size:11px;color:#606a75;line-height:1.25;min-height:14px}.s101alts{display:grid;grid-template-columns:1fr 1fr;gap:6px}.s101item{display:grid;grid-template-columns:48px 1fr;align-items:center;gap:6px;font-size:11px;color:#404852;border-top:1px solid #eef1f4;padding-top:6px}.s101item img{width:44px;height:44px}"
        ".sheet{width:100%;height:auto;max-height:none;border:1px solid #d8dde3;border-radius:6px;background:#fff;margin-top:8px}"
        "@media(max-width:850px){.row{grid-template-columns:1fr}.compare{grid-template-columns:1fr}}"
        "</style></head><body>"
        "<header><h1>Topmark Standards Pass</h1>"
        "<div class='stats'>"
        f"<div class='stat'>Shape refs: <b>{summary['standard_shape_refs']}</b></div>"
        f"<div class='stat'>Rows queued: <b>{summary['topmark_rows_needing_special_pass']}</b></div>"
        f"<div class='stat'>Resolved: <b>{summary['resolved_exact_or_inferred_shape_rows']}</b></div>"
        f"<div class='stat'>Ambiguous: <b>{summary['ambiguous_or_unresolved_rows']}</b></div>"
        f"<div class='stat'>Candidate PNGs: <b>{summary['candidate_png_rendered_rows']}</b></div>"
        f"<div class='stat'>S-101 TOPMAR SVGs: <b>{summary['s101_topmark_png_rendered']}/{summary['s101_topmark_svg_entries']}</b></div>"
        "</div></header><main>"
        "<section class='sources'><h2>Reference Inputs</h2><ul>"
        f"{source_links}</ul><h2>Standard Shape Sheet</h2>"
        "<img class='sheet' src='topmark_standard_reference_sheet.png' alt='standard topmark sheet'></section>"
        + "\n".join(cards)
        + "</main></body></html>\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args(argv)
    result = build()
    print(json.dumps({
        "status": result["status"],
        "summary": result["summary"],
        "outputs": {
            "json": str(OUT_JSON.relative_to(ROOT)),
            "csv": str(OUT_CSV.relative_to(ROOT)),
            "markdown": str(OUT_MD.relative_to(ROOT)),
            "html": str(OUT_HTML.relative_to(ROOT)),
        },
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
