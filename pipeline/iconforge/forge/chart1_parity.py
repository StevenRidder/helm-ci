"""Chart No.1 visual parity gate for the full Icon Forge catalog.

FORGE-12 validates the generated presentation assets against U.S. Chart No.1
reference classes. It is intentionally a gate, not a generator: mismatches are
reported to a hard pile with reason codes instead of being hidden.

Run:  python -m forge.chart1_parity
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import shutil
import subprocess
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import render, scale125_generate


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "pilots" / "full_catalog.json"
PILOT = ROOT / "pilots" / "chart1_visual_parity.json"
OUT = ROOT / "out" / "chart1_parity"
REFERENCE_OUT = OUT / "reference"
SAMPLE_N = 50
SAMPLE_SEED = 20260630

CHART1_URL = "https://repository.library.noaa.gov/view/noaa/2719/noaa_2719_DS1.pdf"
CHART1_RECORD_URL = "https://repository.library.noaa.gov/view/noaa/2719"
CHART1_SHA256 = "0967d6cac35faf54caaff474fc85e90b05964474088b57dd1431585d78a4a1c3"
CHART1_PAGES = list(range(86, 100))

REFERENCE_SECTIONS = {
    "ecdis_summary": {
        "pages": [86],
        "crop_box_unit": [0.0, 0.0, 1.0, 1.0],
        "description": "ECDIS symbol summary for cardinal, lateral, safe-water, special, and beacon symbols.",
    },
    "colors_topmarks": {
        "pages": [87, 88],
        "crop_box_unit": [0.0, 0.0, 1.0, 1.0],
        "description": "Colors of buoys and beacon topmarks; IALA topmark examples.",
    },
    "buoy_shapes": {
        "pages": [89],
        "crop_box_unit": [0.0, 0.0, 1.0, 1.0],
        "description": "Shapes of buoys: conical, can, spherical, pillar, spar, barrel, super buoy.",
    },
    "mooring_buoys": {
        "pages": [90],
        "crop_box_unit": [0.0, 0.0, 1.0, 1.0],
        "description": "Mooring buoy and trot/mooring buoy examples.",
    },
    "special_purpose_buoys": {
        "pages": [91],
        "crop_box_unit": [0.0, 0.0, 1.0, 1.0],
        "description": "Special-purpose buoy families and special-purpose variants.",
    },
    "beacons": {
        "pages": [92, 93, 94],
        "crop_box_unit": [0.0, 0.0, 1.0, 1.0],
        "description": "Beacon, dayboard, stake, tower, and special-purpose beacon examples.",
    },
    "lateral_regions": {
        "pages": [95, 96],
        "crop_box_unit": [0.0, 0.0, 1.0, 1.0],
        "description": "IALA lateral mark region A/B color, shape, and topmark rules.",
    },
    "cardinal_marks": {
        "pages": [97],
        "crop_box_unit": [0.0, 0.0, 1.0, 1.0],
        "description": "Cardinal marks: topmark orientation and black/yellow band order.",
    },
    "isolated_safe_special": {
        "pages": [98],
        "crop_box_unit": [0.0, 0.0, 1.0, 1.0],
        "description": "Isolated danger, safe-water, and special marks.",
    },
    "supplementary": {
        "pages": [99],
        "crop_box_unit": [0.0, 0.0, 1.0, 1.0],
        "description": "Supplementary buoy/beacon examples and junction cases.",
    },
}

REFERENCE_CROPS = {
    "ecdis_summary": {
        "status": "class_panel_reference",
        "page": 86,
        "box_unit": [0.02, 0.08, 0.98, 0.95],
        "chart1_class": "ECDIS buoy/beacon summary region",
    },
    "topmarks": {
        "status": "class_panel_reference",
        "page": 88,
        "box_unit": [0.02, 0.08, 0.98, 0.94],
        "chart1_class": "topmark examples region",
    },
    "topmark_two_cones_up": {
        "status": "exact_symbol_crop",
        "page": 88,
        "box_unit": [0.785, 0.340, 0.807, 0.372],
        "chart1_class": "topmark: 2 cones point upward",
    },
    "topmark_two_cones_down": {
        "status": "exact_symbol_crop",
        "page": 88,
        "box_unit": [0.785, 0.376, 0.807, 0.411],
        "chart1_class": "topmark: 2 cones point downward",
    },
    "topmark_two_cones_base": {
        "status": "exact_symbol_crop",
        "page": 88,
        "box_unit": [0.785, 0.416, 0.807, 0.449],
        "chart1_class": "topmark: 2 cones base to base",
    },
    "topmark_two_cones_point": {
        "status": "exact_symbol_crop",
        "page": 88,
        "box_unit": [0.785, 0.455, 0.807, 0.486],
        "chart1_class": "topmark: 2 cones point to point",
    },
    "topmark_two_spheres": {
        "status": "exact_symbol_crop",
        "page": 88,
        "box_unit": [0.785, 0.492, 0.807, 0.518],
        "chart1_class": "topmark: 2 spheres",
    },
    "topmark_sphere": {
        "status": "exact_symbol_crop",
        "page": 88,
        "box_unit": [0.785, 0.526, 0.807, 0.545],
        "chart1_class": "topmark: sphere",
    },
    "topmark_cone_up": {
        "status": "exact_symbol_crop",
        "page": 88,
        "box_unit": [0.733, 0.552, 0.752, 0.578],
        "chart1_class": "topmark: cone point up",
    },
    "topmark_cone_down": {
        "status": "exact_symbol_crop",
        "page": 88,
        "box_unit": [0.733, 0.587, 0.752, 0.605],
        "chart1_class": "topmark: cone point down",
    },
    "topmark_vertical_rectangle": {
        "status": "exact_symbol_crop",
        "page": 88,
        "box_unit": [0.733, 0.613, 0.752, 0.635],
        "chart1_class": "topmark: cylinder, square, vertical rectangle",
    },
    "topmark_x_shape": {
        "status": "exact_symbol_crop",
        "page": 88,
        "box_unit": [0.733, 0.644, 0.752, 0.663],
        "chart1_class": "topmark: X-shape",
    },
    "topmark_flag_other": {
        "status": "exact_symbol_crop",
        "page": 88,
        "box_unit": [0.733, 0.670, 0.752, 0.696],
        "chart1_class": "topmark: flag or other shape",
    },
    "topmark_horizontal_board": {
        "status": "exact_symbol_crop",
        "page": 88,
        "box_unit": [0.733, 0.704, 0.752, 0.721],
        "chart1_class": "topmark: board, horizontal rectangle",
    },
    "topmark_cube_point_up": {
        "status": "exact_symbol_crop",
        "page": 88,
        "box_unit": [0.733, 0.733, 0.752, 0.752],
        "chart1_class": "topmark: cube point up",
    },
    "topmark_cross_circle": {
        "status": "exact_symbol_crop",
        "page": 88,
        "box_unit": [0.733, 0.760, 0.752, 0.783],
        "chart1_class": "topmark: upright cross over a circle",
    },
    "topmark_t_shape": {
        "status": "exact_symbol_crop",
        "page": 88,
        "box_unit": [0.733, 0.789, 0.752, 0.813],
        "chart1_class": "topmark: T-shape",
    },
    "buoy_shapes": {
        "status": "class_panel_reference",
        "page": 89,
        "box_unit": [0.02, 0.08, 0.98, 0.84],
        "chart1_class": "standard buoy-shape examples region",
    },
    "shape_conical_buoy": {
        "status": "multi_symbol_reference",
        "page": 89,
        "box_unit": [0.735, 0.263, 0.845, 0.302],
        "chart1_class": "conical buoy",
    },
    "shape_can_buoy": {
        "status": "multi_symbol_reference",
        "page": 89,
        "box_unit": [0.735, 0.302, 0.845, 0.341],
        "chart1_class": "can buoy",
    },
    "shape_spherical_buoy": {
        "status": "multi_symbol_reference",
        "page": 89,
        "box_unit": [0.735, 0.341, 0.845, 0.379],
        "chart1_class": "spherical buoy",
    },
    "shape_pillar_buoy": {
        "status": "multi_symbol_reference",
        "page": 89,
        "box_unit": [0.735, 0.379, 0.845, 0.417],
        "chart1_class": "pillar buoy",
    },
    "shape_spar_buoy": {
        "status": "multi_symbol_reference",
        "page": 89,
        "box_unit": [0.735, 0.417, 0.845, 0.455],
        "chart1_class": "spar buoy",
    },
    "shape_barrel_buoy": {
        "status": "multi_symbol_reference",
        "page": 89,
        "box_unit": [0.735, 0.455, 0.845, 0.493],
        "chart1_class": "barrel buoy",
    },
    "shape_super_buoy": {
        "status": "multi_symbol_reference",
        "page": 89,
        "box_unit": [0.735, 0.493, 0.845, 0.606],
        "chart1_class": "super-buoy",
    },
    "mooring_buoys": {
        "status": "multi_symbol_reference",
        "page": 90,
        "box_unit": [0.02, 0.08, 0.98, 0.58],
        "chart1_class": "mooring buoy examples",
    },
    "special_purpose_buoys": {
        "status": "multi_symbol_reference",
        "page": 91,
        "box_unit": [0.02, 0.08, 0.98, 0.88],
        "chart1_class": "special-purpose buoy examples",
    },
    "beacons": {
        "status": "class_panel_reference",
        "page": 92,
        "box_unit": [0.02, 0.08, 0.98, 0.93],
        "chart1_class": "beacon examples region",
    },
    "beacon_general": {
        "status": "multi_symbol_reference",
        "page": 92,
        "box_unit": [0.735, 0.345, 0.828, 0.455],
        "chart1_class": "beacon in general",
    },
    "beacon_with_topmark": {
        "status": "multi_symbol_reference",
        "page": 92,
        "box_unit": [0.735, 0.565, 0.828, 0.840],
        "chart1_class": "beacon with topmark examples",
    },
    "beacon_tower": {
        "status": "multi_symbol_reference",
        "page": 94,
        "box_unit": [0.735, 0.185, 0.828, 0.405],
        "chart1_class": "beacon tower",
    },
    "beacon_lattice": {
        "status": "multi_symbol_reference",
        "page": 94,
        "box_unit": [0.735, 0.405, 0.828, 0.448],
        "chart1_class": "lattice beacon",
    },
    "lateral_regions": {
        "status": "class_panel_reference",
        "page": 95,
        "box_unit": [0.02, 0.08, 0.98, 0.94],
        "chart1_class": "IALA lateral-region examples",
    },
    "cardinal_marks": {
        "status": "multi_symbol_reference",
        "page": 97,
        "box_unit": [0.02, 0.08, 0.98, 0.86],
        "chart1_class": "cardinal marks examples",
    },
    "isolated_safe_special": {
        "status": "multi_symbol_reference",
        "page": 98,
        "box_unit": [0.02, 0.08, 0.98, 0.86],
        "chart1_class": "isolated-danger safe-water special-mark examples",
    },
    "supplementary": {
        "status": "class_panel_reference",
        "page": 99,
        "box_unit": [0.02, 0.08, 0.98, 0.86],
        "chart1_class": "supplementary buoy/beacon examples",
    },
}


@dataclass(frozen=True)
class Target:
    scope: str
    reference_section: str
    chart1_class: str
    expected_shape: str
    expected_colors: list[str]
    expected_topmark: str | None
    reference_crop_id: str
    strict: bool
    checks: list[str]


@dataclass
class ParityRow:
    asset: str
    style: str
    palette: str
    description: str | None
    reference_section: str
    reference_pages: list[int]
    chart1_class: str
    expected_shape: str
    expected_colors: list[str]
    expected_topmark: str | None
    reference_crop_id: str | None
    reference_evidence_status: str
    reference_crop: str | None
    reference_crop_box_unit: list[float] | None
    observed_shape: str
    observed_colors: list[str]
    observed_topmark: str | None
    class_verdict: str
    reference_comparison: dict | None
    final_approval: bool
    verdict: str
    reason_codes: list[str]
    notes: list[str]
    render: str
    svg: str


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", s)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _ensure_chart1_pdf() -> Path:
    REFERENCE_OUT.mkdir(parents=True, exist_ok=True)
    target = REFERENCE_OUT / "us-chart-no-1.pdf"
    candidates = [
        os.environ.get("FORGE_CHART1_PDF"),
        "/private/tmp/chart1/us-chart-no-1.pdf",
        str(target),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate)
        if path.exists():
            if path != target:
                shutil.copyfile(path, target)
            break
    else:
        with urllib.request.urlopen(CHART1_URL, timeout=60) as response:
            target.write_bytes(response.read())

    actual = _sha256(target)
    if actual != CHART1_SHA256:
        raise RuntimeError(
            f"Chart No.1 PDF hash mismatch: expected {CHART1_SHA256}, got {actual}"
        )
    return target


def _render_reference_pages(pdf: Path) -> list[dict]:
    pages_dir = REFERENCE_OUT / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    rendered = []
    pdftoppm = shutil.which("pdftoppm")
    if not pdftoppm:
        raise RuntimeError("pdftoppm is required to render Chart No.1 reference pages")

    prefix = pages_dir / "chart1"
    subprocess.run(
        [pdftoppm, "-f", str(CHART1_PAGES[0]), "-l", str(CHART1_PAGES[-1]), "-r", "160", "-png", str(pdf), str(prefix)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    for page in CHART1_PAGES:
        image = pages_dir / f"chart1-{page:03d}.png"
        if not image.exists():
            suffix = page - CHART1_PAGES[0] + 1
            generated = pages_dir / f"chart1-{suffix:02d}.png"
            if generated.exists():
                generated.rename(image)
        if not image.exists():
            raise RuntimeError(f"missing rendered Chart No.1 page {page}: {image}")
        with Image.open(image) as img:
            rendered.append({
                "page": page,
                "image": _rel(image),
                "width": img.width,
                "height": img.height,
                "sha256": _sha256(image),
            })
    return rendered


def _crop_box_pixels(box_unit: list[float], width: int, height: int) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = box_unit
    return (
        max(0, min(width, round(x0 * width))),
        max(0, min(height, round(y0 * height))),
        max(0, min(width, round(x1 * width))),
        max(0, min(height, round(y1 * height))),
    )


def _render_reference_crops(reference_pages: list[dict]) -> dict[str, dict]:
    pages = {page["page"]: ROOT / page["image"] for page in reference_pages}
    crops_dir = REFERENCE_OUT / "crops"
    crops_dir.mkdir(parents=True, exist_ok=True)
    crop_index: dict[str, dict] = {}
    for crop_id, spec in REFERENCE_CROPS.items():
        page_path = pages[spec["page"]]
        with Image.open(page_path).convert("RGB") as page:
            box = _crop_box_pixels(spec["box_unit"], page.width, page.height)
            crop = page.crop(box)
            crop_path = crops_dir / f"{crop_id}.png"
            crop.save(crop_path)
            crop_index[crop_id] = {
                "id": crop_id,
                "status": spec["status"],
                "page": spec["page"],
                "image": _rel(crop_path),
                "box_unit": spec["box_unit"],
                "box_pixels": list(box),
                "width": crop.width,
                "height": crop.height,
                "sha256": _sha256(crop_path),
                "chart1_class": spec["chart1_class"],
                "source_pdf_sha256": CHART1_SHA256,
                "clean_ip": "NOAA U.S. Chart No.1 public-domain reference crop; not OpenCPN rastersymbol artwork.",
            }
    return crop_index


def _image_metrics(path: Path) -> dict:
    img = Image.open(path).convert("RGB").resize((128, 128), Image.Resampling.LANCZOS)
    pixels = list(img.getdata())
    non_white = []
    red = green = yellow = black = 0
    for i, (r, g, b) in enumerate(pixels):
        x = i % img.width
        y = i // img.width
        if min(255 - r, 255 - g, 255 - b) > 18:
            non_white.append((x, y))
        if r > 140 and g < 100 and b < 100:
            red += 1
        if g > 110 and r < 120 and b < 120:
            green += 1
        if r > 150 and g > 130 and b < 90:
            yellow += 1
        if r < 80 and g < 80 and b < 80:
            black += 1
    if non_white:
        xs = [p[0] for p in non_white]
        ys = [p[1] for p in non_white]
        bbox = [min(xs), min(ys), max(xs), max(ys)]
        aspect = round((bbox[2] - bbox[0] + 1) / max(1, bbox[3] - bbox[1] + 1), 4)
    else:
        bbox = [0, 0, 0, 0]
        aspect = 0.0
    total = len(pixels)
    return {
        "foreground_ratio": round(len(non_white) / total, 4),
        "bbox": bbox,
        "aspect": aspect,
        "color_presence": {
            "red": red / total > 0.005,
            "green": green / total > 0.005,
            "yellow": yellow / total > 0.005,
            "black": black / total > 0.005,
        },
    }


def _compare_to_reference(render_path: Path, crop: dict | None, expected_colors: list[str]) -> dict | None:
    if not crop:
        return None
    generated = _image_metrics(render_path)
    reference = _image_metrics(ROOT / crop["image"])
    color_checks = {}
    for color in expected_colors:
        if color == "white":
            continue
        color_checks[color] = {
            "generated_has": generated["color_presence"].get(color, False),
            "reference_has": reference["color_presence"].get(color, False),
        }
    return {
        "crop_id": crop["id"],
        "crop_status": crop["status"],
        "generated": generated,
        "reference": reference,
        "aspect_delta": round(abs(generated["aspect"] - reference["aspect"]), 4),
        "foreground_delta": round(abs(generated["foreground_ratio"] - reference["foreground_ratio"]), 4),
        "expected_color_checks": color_checks,
    }


def _is_gate_asset(entry: dict) -> bool:
    asset = entry["asset"].upper()
    return entry["family"] == "buoy_beacon_marks" or asset.startswith(("BOY", "BCN", "TOP"))


def _color_tokens(entry: dict) -> list[str]:
    return scale125_generate._tokens(entry)


TOPSHP_CHART1_CROPS = {
    "1": ("topmark_cone_up", "TOPSHP1 cone point up"),
    "2": ("topmark_cone_down", "TOPSHP2 cone point down"),
    "3": ("topmark_sphere", "TOPSHP3 sphere"),
    "4": ("topmark_two_spheres", "TOPSHP4 two spheres"),
    "5": ("topmark_vertical_rectangle", "TOPSHP5 cylinder/can"),
    "6": ("topmark_vertical_rectangle", "TOPSHP6 board"),
    "7": ("topmark_x_shape", "TOPSHP7 X-shape"),
    "9": ("topmark_cube_point_up", "TOPSHP9 cube point up"),
    "10": ("topmark_two_cones_point", "TOPSHP10 two cones point to point"),
    "11": ("topmark_two_cones_base", "TOPSHP11 two cones base to base"),
    "12": ("topmark_cube_point_up", "TOPSHP12 rhombus"),
    "13": ("topmark_two_cones_up", "TOPSHP13 two cones points upward"),
    "14": ("topmark_two_cones_down", "TOPSHP14 two cones points downward"),
    "15": ("topmark_flag_other", "TOPSHP15 besom point up"),
    "16": ("topmark_flag_other", "TOPSHP16 besom point down"),
    "17": ("topmark_flag_other", "TOPSHP17 flag"),
    "19": ("topmark_vertical_rectangle", "TOPSHP19 square"),
    "20": ("topmark_horizontal_board", "TOPSHP20 horizontal rectangle"),
    "21": ("topmark_vertical_rectangle", "TOPSHP21 vertical rectangle"),
    "24": ("topmark_cone_up", "TOPSHP24 triangle point up"),
    "25": ("topmark_cone_down", "TOPSHP25 triangle point down"),
    "26": ("topmark_sphere", "TOPSHP26 circle"),
    "28": ("topmark_t_shape", "TOPSHP28 T-shape"),
    "30": ("topmark_cross_circle", "TOPSHP30 upright cross over a circle"),
    "33": ("topmark_flag_other", "TOPSHP33 other shape"),
}

TOPSHP_MANUAL_EXCEPTIONS = {
    "8": "TOPSHP8 upright cross is not an exact Chart No.1 ECDIS topmark row here",
    "18": "TOPSHP18 sphere over rhombus lacks an exact Chart No.1 crop",
    "22": "TOPSHP22 trapezium up lacks an exact Chart No.1 crop",
    "23": "TOPSHP23 trapezium down lacks an exact Chart No.1 crop",
    "27": "TOPSHP27 two upright crosses lacks an exact Chart No.1 crop",
    "29": "TOPSHP29 triangle over circle lacks an exact Chart No.1 crop",
    "31": "TOPSHP31 rhombus over circle lacks an exact Chart No.1 crop",
    "32": "TOPSHP32 circle over triangle lacks an exact Chart No.1 crop",
}


def _topshape_code(entry: dict) -> str | None:
    for condition in entry.get("conditions") or []:
        match = re.fullmatch(r"TOPSHP(\d+)", condition)
        if match:
            return match.group(1)
    return None


def _topmark_crop_for(entry: dict) -> tuple[str, str, bool]:
    topshp = _topshape_code(entry)
    if topshp in TOPSHP_CHART1_CROPS:
        crop, chart1_class = TOPSHP_CHART1_CROPS[topshp]
        return crop, chart1_class, True
    if topshp in TOPSHP_MANUAL_EXCEPTIONS:
        return "topmarks", TOPSHP_MANUAL_EXCEPTIONS[topshp], False

    desc = (entry.get("description") or "").lower()
    if "cone, point up" in desc:
        return "topmark_cone_up", "topmark cone point up", True
    if "cone, point down" in desc:
        return "topmark_cone_down", "topmark cone point down", True
    if "shere" in desc or "sphere" in desc:
        return "topmark_sphere", "topmark sphere", True
    if "andreas cross" in desc:
        return "topmark_x_shape", "topmark X-shape", True
    if "st.georg cross" in desc:
        return "topmark_cross_circle", "topmark upright cross", True
    if "diamond" in desc:
        return "topmark_cube_point_up", "topmark diamond/cube point up", True
    if "square board" in desc and "diagonal" in desc:
        return "topmark_cube_point_up", "topmark diagonal square board", True
    if "entry prohibited" in desc:
        return "topmark_horizontal_board", "topmark board", True
    if "round board" in desc:
        return "topmark_sphere", "topmark round board", True
    if "square board" in desc or "vertical" in desc:
        return "topmark_vertical_rectangle", "topmark vertical rectangle", True
    return "topmarks", "manual topmark shape exception: missing TOPSHP/description crosswalk", False


def _target_for(entry: dict) -> Target:
    asset = entry["asset"].upper()
    desc = (entry.get("description") or "").lower()
    tokens = _color_tokens(entry)

    if not _is_gate_asset(entry):
        return Target("outside_forge12_gate", "ecdis_summary", "outside buoy/beacon/topmark visual gate", "not_scoped", [], None, "ecdis_summary", False, [])
    if asset.startswith(("BOYCAR", "BCNCAR")):
        return Target("buoy_beacon_topmark", "cardinal_marks", "cardinal buoy/beacon", "cardinal", ["black", "yellow"], "cardinal_cones", "cardinal_marks", True, ["shape", "colors", "topmark"])
    if asset.startswith("BOYCAN"):
        return Target("buoy_beacon_topmark", "buoy_shapes", "can buoy", "can", tokens, None, "shape_can_buoy", True, ["shape", "colors"])
    if asset.startswith("BOYCON"):
        return Target("buoy_beacon_topmark", "buoy_shapes", "conical buoy", "conical", tokens, None, "shape_conical_buoy", True, ["shape", "colors"])
    if asset.startswith(("BOYLAT", "BCNLAT")):
        return Target("buoy_beacon_topmark", "lateral_regions", "lateral buoy/beacon", "lateral", tokens, "optional_lateral_topmark", "lateral_regions", True, ["shape", "colors"])
    if asset.startswith(("BOYSAW", "BCNSAW")) or "safe water" in desc:
        return Target("buoy_beacon_topmark", "isolated_safe_special", "safe-water mark", "safe_water", ["red", "white"], "single_sphere", "isolated_safe_special", True, ["shape", "colors", "topmark"])
    if asset.startswith(("BOYISD", "BCNISD")) or "isolated danger" in desc or "isol.danger" in desc:
        return Target("buoy_beacon_topmark", "isolated_safe_special", "isolated-danger mark", "isolated_danger", ["black", "red"], "two_spheres", "isolated_safe_special", True, ["shape", "colors", "topmark"])
    if asset.startswith(("BOYSPP", "BCNSPP")) or "special" in desc:
        return Target("buoy_beacon_topmark", "special_purpose_buoys", "special-purpose mark", "special", ["yellow"], "x_topmark_optional", "special_purpose_buoys", True, ["shape", "colors"])
    if asset.startswith(("BOYSPR", "BOYPIL", "BOYBAR", "BOYSPH", "BOYSUP")):
        shape = "specialized_buoy"
        crop = "buoy_shapes"
        if asset.startswith("BOYBAR"):
            shape, crop = "barrel", "shape_barrel_buoy"
        elif asset.startswith("BOYPIL"):
            shape, crop = "pillar", "shape_pillar_buoy"
        elif asset.startswith("BOYSPH"):
            shape, crop = "spherical", "shape_spherical_buoy"
        elif asset.startswith("BOYSPR"):
            shape, crop = "spar", "shape_spar_buoy"
        elif asset.startswith("BOYSUP"):
            shape, crop = "super_buoy", "shape_super_buoy"
        return Target("buoy_beacon_topmark", "buoy_shapes", "specialized buoy body", shape, tokens, None, crop, True, ["shape", "colors"])
    if asset.startswith("BOYMOR"):
        return Target("buoy_beacon_topmark", "mooring_buoys", "mooring buoy", "mooring", tokens, None, "mooring_buoys", True, ["shape", "colors"])
    if asset.startswith(("TOPMAR", "TOPMA", "TOPSHP", "TOPSH")):
        crop, chart1_class, strict = _topmark_crop_for(entry)
        expected_shape = "topmark_only" if strict else "manual_topmark_exception"
        return Target("buoy_beacon_topmark", "colors_topmarks", chart1_class, expected_shape, tokens, "standalone_topmark", crop, strict, ["shape", "topmark"])
    if asset.startswith("BCN"):
        crop = "beacon_general"
        shape = "beacon"
        if asset.startswith("BCNTOW"):
            crop, shape = "beacon_tower", "beacon_tower"
        elif asset.startswith("BCNLTC"):
            crop, shape = "beacon_lattice", "lattice_beacon"
        elif asset.startswith("BCNGEN") and any(code in asset for code in ["68", "69", "70", "71", "76"]):
            crop = "beacon_with_topmark"
        return Target("buoy_beacon_topmark", "beacons", "beacon/dayboard/stake/tower", shape, tokens, "optional_topmark", crop, True, ["shape", "colors"])
    return Target("buoy_beacon_topmark", "ecdis_summary", "buoy/beacon related Chart No.1 class", "manual_crosswalk", tokens, None, "ecdis_summary", False, ["manual_crosswalk"])


def _observe(svg: str) -> tuple[str, list[str], str | None]:
    tokens = sorted(render.referenced_tokens(svg))
    if 'rect x="25" y="29" width="14" height="' in svg and "polygon points" in svg:
        return "cardinal", tokens, "cardinal_cones"
    if "M32 22l-13 31h26z" in svg:
        return "conical", tokens, None
    if 'rect x="23" y="24" width="18" height="28"' in svg:
        return "can", tokens, None
    if 'circle cx="32" cy="32" r="8"' in svg and "M32 32 L32 9" in svg:
        return "light_flare", tokens, "light_flare"
    if 'rect x="22" y="22" width="20" height="30"' in svg:
        return "generic_body", tokens, None
    if "polygon points" in svg:
        return "topmark_like", tokens, "polygon"
    if 'ellipse cx="32" cy="34" rx="23" ry="13"' in svg:
        return "wreck_obstruction", tokens, None
    if 'rect x="14" y="14" width="36" height="36"' in svg:
        return "area_pattern", tokens, None
    return "unknown", tokens, None


def _shape_matches(expected: str, observed: str) -> bool:
    if expected == observed:
        return True
    if expected == "lateral" and observed in {"can", "conical"}:
        return True
    return False


def _reference_status(target: Target, crop: dict | None) -> str:
    if target.scope == "outside_forge12_gate":
        return "out_of_scope"
    if not target.strict:
        return "manual_exception"
    if not crop:
        return "missing_reference_crop"
    return crop["status"]


def _evaluate(entry: dict, style: str, palette: str, crop_index: dict[str, dict]) -> ParityRow:
    target = _target_for(entry)
    crop = crop_index.get(target.reference_crop_id)
    reference_status = _reference_status(target, crop)
    svg_path = ROOT / "generated" / "full_catalog" / "compose" / style / f"{_slug(entry['asset'])}.svg"
    render_path = ROOT / "out" / "full_catalog" / "renders" / f"{_slug(entry['asset'])}_{style}_{palette}.png"
    svg = svg_path.read_text()
    observed_shape, observed_colors, observed_topmark = _observe(svg)
    reason_codes: list[str] = []
    notes: list[str] = []

    if target.scope == "outside_forge12_gate":
        verdict = "deferred"
        reason_codes.append("outside_forge12_scope")
        notes.append("FORGE-12 covers buoy/beacon/topmark visual parity first; this asset still receives a catalog row.")
    elif not target.strict:
        verdict = "manual"
        reason_codes.append("missing_exact_chart1_asset_crosswalk")
        notes.append("Asset is buoy/beacon related, but needs manual reference-class assignment before strict judging.")
    else:
        shape_ok = _shape_matches(target.expected_shape, observed_shape)
        if not shape_ok:
            reason_codes.append("wrong_silhouette_or_symbol_body")
        color_ok = all(color in observed_colors for color in target.expected_colors if color != "white")
        if not color_ok:
            reason_codes.append("missing_expected_chart1_colour_token")
        topmark_ok = True
        if target.expected_shape == "topmark_only":
            topmark_ok = observed_shape in {"topmark_like"} and observed_shape not in {"generic_body", "light_flare"}
            if not topmark_ok:
                reason_codes.append("topmark_not_standalone_chart1_glyph")
        if target.expected_shape == "cardinal" and observed_topmark != "cardinal_cones":
            topmark_ok = False
            reason_codes.append("wrong_cardinal_topmark")
        if observed_shape == "light_flare" and target.expected_shape != "light":
            reason_codes.append("non_light_symbol_rendered_as_light_flare")
        if observed_shape == "generic_body" and target.expected_shape not in {"manual_crosswalk", "not_scoped"}:
            reason_codes.append("generic_placeholder_body")
        if reference_status != "exact_symbol_crop":
            reason_codes.append("no_exact_symbol_crop_final_pass_forbidden")
            notes.append(
                f"This row has {reference_status} Chart No.1 evidence, so FORGE-13 cannot treat it as final-approved geometry."
            )

        if not reason_codes:
            verdict = "pass"
        elif reason_codes == ["no_exact_symbol_crop_final_pass_forbidden"]:
            verdict = "manual"
        elif shape_ok and color_ok and topmark_ok:
            verdict = "partial"
        else:
            verdict = "fail"

        notes.append(
            f"Expected {target.expected_shape} from Chart No.1 {target.reference_section}; observed {observed_shape}."
        )

    section = REFERENCE_SECTIONS[target.reference_section]
    reference_comparison = _compare_to_reference(render_path, crop, target.expected_colors)
    final_approval = verdict == "pass" and reference_status == "exact_symbol_crop"
    return ParityRow(
        asset=entry["asset"],
        style=style,
        palette=palette,
        description=entry.get("description"),
        reference_section=target.reference_section,
        reference_pages=section["pages"],
        chart1_class=target.chart1_class,
        expected_shape=target.expected_shape,
        expected_colors=target.expected_colors,
        expected_topmark=target.expected_topmark,
        reference_crop_id=target.reference_crop_id if crop else None,
        reference_evidence_status=reference_status,
        reference_crop=_rel(ROOT / crop["image"]) if crop else None,
        reference_crop_box_unit=crop["box_unit"] if crop else None,
        observed_shape=observed_shape,
        observed_colors=observed_colors,
        observed_topmark=observed_topmark,
        class_verdict=verdict,
        reference_comparison=reference_comparison,
        final_approval=final_approval,
        verdict=verdict,
        reason_codes=sorted(set(reason_codes)),
        notes=notes,
        render=_rel(render_path),
        svg=_rel(svg_path),
    )


def _build_crosswalk(catalog: dict, crop_index: dict[str, dict]) -> dict:
    entries = []
    gate_assets = 0
    evidence_counts: dict[str, int] = {}
    for entry in catalog["entries"]:
        target = _target_for(entry)
        crop = crop_index.get(target.reference_crop_id)
        reference_status = _reference_status(target, crop)
        evidence_counts[reference_status] = evidence_counts.get(reference_status, 0) + 1
        if target.scope == "buoy_beacon_topmark":
            gate_assets += 1
        section = REFERENCE_SECTIONS[target.reference_section]
        entries.append({
            "asset": entry["asset"],
            "asset_kind": entry["asset_kind"],
            "family": entry["family"],
            "description": entry.get("description"),
            "object_class": entry["object_class"],
            "lookup_id": entry["lookup_id"],
            "instruction": entry["instruction"],
            "scope": target.scope,
            "chart1_class": target.chart1_class,
            "reference_section": target.reference_section,
            "reference_pages": section["pages"],
            "reference_section_box_unit": section["crop_box_unit"],
            "reference_crop_id": target.reference_crop_id if crop else None,
            "reference_crop": crop["image"] if crop else None,
            "reference_crop_status": reference_status,
            "reference_crop_box_unit": crop["box_unit"] if crop else None,
            "reference_crop_box_pixels": crop["box_pixels"] if crop else None,
            "reference_crop_sha256": crop["sha256"] if crop else None,
            "final_pass_allowed": reference_status == "exact_symbol_crop",
            "expected_shape": target.expected_shape,
            "expected_colors": target.expected_colors,
            "expected_topmark": target.expected_topmark,
            "strict": target.strict,
            "checks": target.checks,
        })

    data = {
        "id": "chart1_visual_parity",
        "title": "Chart No.1 visual parity crosswalk for Icon Forge full catalog",
        "source_catalog": "pilots/full_catalog.json",
        "source_catalog_assets": catalog["selected_assets"],
        "gate_scope": "buoy/beacon/topmark assets first; every full-catalog asset still receives a row",
        "gate_assets": gate_assets,
        "evidence_counts": evidence_counts,
        "reference": {
            "publication": "U.S. Chart No.1",
            "record_url": CHART1_RECORD_URL,
            "pdf_url": CHART1_URL,
            "pdf_sha256": CHART1_SHA256,
            "pages": CHART1_PAGES,
            "sections": REFERENCE_SECTIONS,
            "crops": crop_index,
            "clean_ip_boundary": [
                "Use U.S. Chart No.1 as public-domain reference material.",
                "Use local chartsymbols.xml for metadata and S-52 asset identity only.",
                "Do not extract or trace OpenCPN GPL rastersymbols-*.png into the owned pack.",
            ],
        },
        "entries": entries,
    }
    PILOT.parent.mkdir(parents=True, exist_ok=True)
    PILOT.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    return data


def _load_catalog() -> dict:
    needs_full_run = not CATALOG.exists()
    if CATALOG.exists():
        catalog = json.loads(CATALOG.read_text())
        first = catalog["entries"][0]
        render_path = ROOT / "out" / "full_catalog" / "renders" / f"{_slug(first['asset'])}_us-paper_day.png"
        svg_path = ROOT / "generated" / "full_catalog" / "compose" / "us-paper" / f"{_slug(first['asset'])}.svg"
        needs_full_run = not render_path.exists() or not svg_path.exists()

    if needs_full_run:
        from . import full_catalog_run

        rc = full_catalog_run.main()
        if rc != 0:
            raise RuntimeError("full catalog run failed; cannot build Chart No.1 parity gate")
    return json.loads(CATALOG.read_text())


def _copy_sample_artifacts(report: dict) -> None:
    samples = ROOT / "samples"
    samples.mkdir(parents=True, exist_ok=True)
    (samples / "chart1_parity_sample50.json").write_text(
        json.dumps(report["sample"], indent=2, sort_keys=True) + "\n"
    )
    sheet = OUT / "contact_sheet_sample50.png"
    if sheet.exists():
        shutil.copyfile(sheet, samples / "chart1_parity_sample50.png")
    crop_review = OUT / "crop_review_sheet.png"
    if crop_review.exists():
        shutil.copyfile(crop_review, samples / "chart1_crop_review.png")
    crop_review_json = OUT / "crop_review.json"
    if crop_review_json.exists():
        shutil.copyfile(crop_review_json, samples / "chart1_crop_review.json")


def _icon(path: Path) -> Image.Image:
    img = Image.open(path).convert("RGBA")
    canvas = Image.new("RGBA", (92, 92), "white")
    img.thumbnail((84, 84), Image.Resampling.LANCZOS)
    canvas.alpha_composite(img, ((92 - img.width) // 2, (92 - img.height) // 2))
    return canvas.convert("RGB")


def _crop_thumb(path: Path) -> Image.Image:
    img = Image.open(path).convert("RGBA")
    canvas = Image.new("RGBA", (132, 92), "white")
    img.thumbnail((124, 84), Image.Resampling.LANCZOS)
    canvas.alpha_composite(img, ((132 - img.width) // 2, (92 - img.height) // 2))
    return canvas.convert("RGB")


def _wrap(draw: ImageDraw.ImageDraw, text: str, x: int, y: int, width: int, font, line_h: int = 15) -> int:
    words = text.split()
    line = ""
    for word in words:
        trial = (line + " " + word).strip()
        if draw.textlength(trial, font=font) <= width:
            line = trial
            continue
        if line:
            draw.text((x, y), line, font=font, fill=(20, 20, 20))
            y += line_h
        line = word
    if line:
        draw.text((x, y), line, font=font, fill=(20, 20, 20))
        y += line_h
    return y


def _contact_sheet(sample_rows: list[dict]) -> None:
    font = ImageFont.load_default()
    row_h = 118
    width = 1540
    height = 78 + row_h * len(sample_rows)
    sheet = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(sheet)
    draw.rectangle((0, 0, width, 44), fill=(26, 32, 40))
    draw.text(
        (14, 14),
        f"FORGE-12 Chart No.1 parity sample: {len(sample_rows)} assets, seed {SAMPLE_SEED}",
        font=font,
        fill="white",
    )
    headers = ["#", "Asset", "Ours", "Chart No.1 ref", "Expected", "Observed", "Verdict", "Reason"]
    xs = [12, 48, 160, 270, 470, 770, 1030, 1135]
    for x, header in zip(xs, headers):
        draw.text((x, 55), header, font=font, fill=(0, 0, 0))

    colors = {
        "pass": (214, 245, 224),
        "partial": (255, 241, 194),
        "fail": (255, 220, 220),
        "manual": (226, 232, 240),
        "deferred": (235, 235, 235),
    }
    y = 78
    for row in sample_rows:
        draw.rectangle((0, y, width, y + row_h - 2), fill=colors.get(row["verdict"], (245, 245, 245)))
        draw.text((12, y + 8), str(row["n"]), font=font, fill=(0, 0, 0))
        draw.text((48, y + 8), row["asset"], font=font, fill=(0, 0, 0))
        sheet.paste(_icon(ROOT / row["render"]), (160, y + 12))
        _wrap(draw, f"{row['reference_section']} p{','.join(map(str, row['reference_pages']))}", 270, y + 8, 180, font)
        _wrap(draw, f"{row['chart1_class']} / {row['expected_shape']}", 470, y + 8, 275, font)
        _wrap(draw, f"{row['observed_shape']} / {','.join(row['observed_colors'])}", 770, y + 8, 240, font)
        draw.text((1030, y + 8), row["verdict"].upper(), font=font, fill=(0, 0, 0))
        _wrap(draw, ", ".join(row["reason_codes"]) or "ok", 1135, y + 8, 375, font, line_h=14)
        y += row_h

    OUT.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT / "contact_sheet_sample50.png")


def _crop_review_sheet(row_dicts: list[dict], crosswalk: dict) -> dict:
    crop_rows: dict[str, list[dict]] = {}
    for row in row_dicts:
        crop_id = row.get("reference_crop_id")
        if crop_id:
            crop_rows.setdefault(crop_id, []).append(row)

    entries = []
    for crop_id, crop in sorted(crosswalk["reference"]["crops"].items()):
        mapped = sorted(crop_rows.get(crop_id, []), key=lambda row: row["asset"])
        verdict_counts: dict[str, int] = {}
        evidence_counts: dict[str, int] = {}
        for row in mapped:
            verdict_counts[row["verdict"]] = verdict_counts.get(row["verdict"], 0) + 1
            evidence = row["reference_evidence_status"]
            evidence_counts[evidence] = evidence_counts.get(evidence, 0) + 1
        entries.append({
            "crop_id": crop_id,
            "status": crop["status"],
            "chart1_class": crop["chart1_class"],
            "page": crop["page"],
            "box_unit": crop["box_unit"],
            "box_pixels": crop["box_pixels"],
            "image": crop["image"],
            "sha256": crop["sha256"],
            "mapped_assets": len(mapped),
            "sample_assets": [row["asset"] for row in mapped[:8]],
            "sample_render": mapped[0]["render"] if mapped else None,
            "verdict_counts": verdict_counts,
            "evidence_counts": evidence_counts,
        })

    review = {
        "schema_version": 1,
        "generator": "iconforge-chart1-crop-review",
        "source": "out/chart1_parity/report.json",
        "pdf_url": CHART1_URL,
        "pdf_sha256": CHART1_SHA256,
        "crop_count": len(entries),
        "entries": entries,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "crop_review.json").write_text(json.dumps(review, indent=2, sort_keys=True) + "\n")

    font = ImageFont.load_default()
    row_h = 116
    width = 1720
    height = 78 + row_h * len(entries)
    sheet = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(sheet)
    draw.rectangle((0, 0, width, 44), fill=(26, 32, 40))
    draw.text(
        (14, 14),
        f"FORGE-14 Chart No.1 crop review: {len(entries)} crops, NOAA Chart No.1 SHA {CHART1_SHA256[:12]}",
        font=font,
        fill="white",
    )
    headers = ["Crop", "Chart No.1", "Generated", "Provenance", "Mapped Assets", "Verdicts / Evidence"]
    xs = [12, 350, 500, 630, 940, 1320]
    for x, header in zip(xs, headers):
        draw.text((x, 55), header, font=font, fill=(0, 0, 0))

    y = 78
    for entry in entries:
        fill = (245, 249, 255) if entry["mapped_assets"] else (242, 242, 242)
        if entry["status"] in {"class_panel_reference", "multi_symbol_reference"}:
            fill = (255, 247, 214)
        draw.rectangle((0, y, width, y + row_h - 2), fill=fill)
        _wrap(draw, f"{entry['crop_id']} / {entry['chart1_class']}", 12, y + 8, 315, font, line_h=14)
        sheet.paste(_crop_thumb(ROOT / entry["image"]), (350, y + 12))
        if entry["sample_render"]:
            sheet.paste(_icon(ROOT / entry["sample_render"]), (520, y + 12))
        _wrap(
            draw,
            f"p{entry['page']} box {entry['box_unit']} sha {entry['sha256'][:12]} status {entry['status']}",
            630,
            y + 8,
            290,
            font,
            line_h=14,
        )
        _wrap(
            draw,
            f"{entry['mapped_assets']} assets: {', '.join(entry['sample_assets']) or 'none'}",
            940,
            y + 8,
            350,
            font,
            line_h=14,
        )
        _wrap(
            draw,
            f"verdicts {entry['verdict_counts']} evidence {entry['evidence_counts']}",
            1320,
            y + 8,
            370,
            font,
            line_h=14,
        )
        y += row_h

    sheet.save(OUT / "crop_review_sheet.png")
    return review


def _report(rows: list[ParityRow], reference_pages: list[dict], crosswalk: dict) -> dict:
    row_dicts = [asdict(r) for r in rows]
    verdict_counts: dict[str, int] = {}
    evidence_counts: dict[str, int] = {}
    for row in row_dicts:
        verdict_counts[row["verdict"]] = verdict_counts.get(row["verdict"], 0) + 1
        evidence = row["reference_evidence_status"]
        evidence_counts[evidence] = evidence_counts.get(evidence, 0) + 1

    gate_rows = [row for row in row_dicts if row["verdict"] != "deferred"]
    final_approved = [row for row in gate_rows if row["final_approval"]]
    hard_pile = [row for row in gate_rows if not row["final_approval"]]
    rng = random.Random(SAMPLE_SEED)
    sample_pool = sorted(gate_rows, key=lambda r: r["asset"])
    sample_rows = rng.sample(sample_pool, min(SAMPLE_N, len(sample_pool)))
    for i, row in enumerate(sample_rows, 1):
        row["n"] = i
    _contact_sheet(sample_rows)
    crop_review = _crop_review_sheet(row_dicts, crosswalk)

    report = {
        "schema_version": 1,
        "generator": "iconforge-chart1-parity",
        "status": "pass" if not hard_pile else "review_required",
        "source_catalog": "pilots/full_catalog.json",
        "crosswalk": "pilots/chart1_visual_parity.json",
        "reference_provenance": {
            "record_url": CHART1_RECORD_URL,
            "pdf_url": CHART1_URL,
            "pdf_sha256": CHART1_SHA256,
            "rendered_pages": reference_pages,
            "sections": REFERENCE_SECTIONS,
            "crops": crosswalk["reference"]["crops"],
        },
        "summary": {
            "full_catalog_assets": crosswalk["source_catalog_assets"],
            "crosswalk_rows": len(crosswalk["entries"]),
            "gate_assets": crosswalk["gate_assets"],
            "styles_checked": ["us-paper"],
            "palettes_checked": ["day"],
            "verdict_counts": verdict_counts,
            "evidence_counts": evidence_counts,
            "final_approved": len(final_approved),
            "hard_pile_entries": len(hard_pile),
            "sample_seed": SAMPLE_SEED,
            "sample_size": len(sample_rows),
            "crop_review": "out/chart1_parity/crop_review.json",
            "crop_review_sheet": "out/chart1_parity/crop_review_sheet.png",
            "non_go_conditions": [
                "Do not publish as Chart No.1 visually approved while status is review_required.",
                "Do not call any row final-approved unless final_approval is true.",
                "Do not treat class_panel_reference or multi_symbol_reference crop evidence as exact icon geometry.",
                "Do not use OpenCPN GPL raster sprites as reference crops for the owned pack.",
            ],
        },
        "sample": {
            "seed": SAMPLE_SEED,
            "size": len(sample_rows),
            "rows": sample_rows,
        },
        "crop_review": {
            "crop_count": crop_review["crop_count"],
            "sheet": "out/chart1_parity/crop_review_sheet.png",
            "json": "out/chart1_parity/crop_review.json",
        },
        "rows": row_dicts,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    (OUT / "hard_pile.json").write_text(json.dumps(hard_pile, indent=2, sort_keys=True) + "\n")
    (OUT / "reference_provenance.json").write_text(
        json.dumps(report["reference_provenance"], indent=2, sort_keys=True) + "\n"
    )
    _copy_sample_artifacts(report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--enforce", action="store_true", help="exit non-zero if visual parity is not pass")
    args = parser.parse_args(argv)

    catalog = _load_catalog()
    pdf = _ensure_chart1_pdf()
    reference_pages = _render_reference_pages(pdf)
    crop_index = _render_reference_crops(reference_pages)
    crosswalk = _build_crosswalk(catalog, crop_index)
    rows = [_evaluate(entry, "us-paper", "day", crop_index) for entry in catalog["entries"]]
    report = _report(rows, reference_pages, crosswalk)

    summary = report["summary"]
    print(f"chart1 parity: {report['status'].upper()}")
    print(f"crosswalk rows: {summary['crosswalk_rows']}")
    print(f"gate assets: {summary['gate_assets']}")
    print(f"verdict counts: {summary['verdict_counts']}")
    print(f"hard pile: {summary['hard_pile_entries']}")
    print(f"report: {OUT / 'report.json'}")
    if args.enforce and report["status"] != "pass":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
