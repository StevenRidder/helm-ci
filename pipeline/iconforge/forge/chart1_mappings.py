"""Chart 1 Mappings Q-section semantic mapping and reference-only row crops.

The local Chart 1 Mappings PDF is a useful INT 1/S-57 cross-check, but it is
not an artwork source for Helm. This module only emits review crops and a
report that keeps the permission boundary explicit.

Run:  python -m forge.chart1_mappings
"""
from __future__ import annotations

import subprocess
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent.parent
MAPPING = ROOT / "catalog" / "chart1_mappings_q_table.json"
PAGE_DIR = ROOT / "out" / "chart1_mappings" / "reference" / "pages"
ROW_DIR = ROOT / "out" / "chart1_mappings" / "reference" / "rows"
REPORT = ROOT / "out" / "chart1_mappings" / "chart1_mappings_q_table_report.json"
RENDER_PAGE_OFFSET = 2
BASE_RENDER_SIZE = (1190, 1684)
RENDER_DPI = 140

X_FULL_ROW = (90, 1112)
X_ICON_REF = (90, 620)

ROW_BOXES: dict[str, tuple[int, int, int]] = {
    "Q1": (47, 283, 348),
    "Q2": (47, 432, 506),
    "Q3": (47, 506, 581),
    "Q4": (47, 581, 655),
    "Q5": (47, 655, 728),
    "Q6": (47, 728, 802),
    "Q7": (47, 886, 958),
    "Q8": (47, 958, 1033),
    "Q9": (47, 1117, 1203),
    "Q10": (47, 1203, 1289),
    "Q11": (47, 1289, 1362),
    "Q20": (48, 302, 359),
    "Q21": (48, 359, 416),
    "Q22": (48, 416, 473),
    "Q23": (48, 473, 531),
    "Q24": (48, 531, 586),
    "Q25": (48, 586, 643),
    "Q26": (48, 643, 758),
    "Q30": (48, 833, 901),
    "Q31": (48, 901, 969),
    "Q40": (48, 1046, 1105),
    "Q41": (48, 1105, 1188),
    "Q42": (48, 1188, 1358),
    "Q43": (48, 1358, 1415),
    "Q44": (48, 1415, 1501),
    "Q45": (48, 1501, 1557),
    "Q50": (49, 218, 292),
    "Q51": (49, 292, 366),
    "Q52": (49, 366, 438),
    "Q53": (49, 438, 512),
    "Q54": (49, 512, 586),
    "Q55": (49, 586, 660),
    "Q56": (49, 660, 734),
    "Q57": (49, 734, 808),
    "Q58": (49, 808, 882),
    "Q59": (49, 882, 956),
    "Q60": (49, 956, 1029),
    "Q61": (49, 1029, 1102),
    "Q62": (49, 1102, 1176),
    "Q70": (49, 1367, 1440),
    "Q71": (49, 1440, 1520),
    "Q80": (50, 287, 369),
    "Q81": (50, 369, 446),
    "Q82": (50, 446, 526),
    "Q83": (50, 526, 607),
    "Qe": (50, 607, 648),
    "Q90": (50, 727, 794),
    "Q91": (50, 794, 866),
    "Q92": (50, 866, 941),
    "Q100": (50, 1012, 1085),
    "Q101": (50, 1085, 1158),
    "Q102.1": (50, 1158, 1232),
    "Q102.2": (50, 1232, 1306),
    "Q110": (50, 1378, 1453),
    "Q111": (50, 1453, 1520),
    "Q120": (51, 263, 347),
    "Q121": (51, 347, 433),
    "Q122": (51, 433, 632),
    "Q123": (51, 632, 718),
    "Q124": (51, 718, 802),
    "Q125": (51, 802, 887),
    "Q126": (51, 887, 971),
}


def load_mapping() -> dict:
    return json.loads(MAPPING.read_text())


def _page_image(page: int) -> Path:
    # pdftoppm names these renders by physical PDF page; the printed Chart 1
    # page number visible in the source table is two pages lower.
    return PAGE_DIR / f"chart1_mappings_q-{page + RENDER_PAGE_OFFSET}.png"


def _ensure_page_renders(mapping: dict) -> None:
    source = mapping["source"]
    pdf = Path(source.get("local_pdf", ""))
    if not pdf.exists():
        raise FileNotFoundError(f"missing Chart 1 Mappings PDF: {pdf}")
    pages = sorted({row["page"] + RENDER_PAGE_OFFSET for row in mapping["rows"]})
    if all((PAGE_DIR / f"chart1_mappings_q-{page}.png").exists() for page in pages):
        return
    PAGE_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "pdftoppm",
            "-png",
            "-r",
            str(RENDER_DPI),
            "-f",
            str(min(pages)),
            "-l",
            str(max(pages)),
            str(pdf),
            str(PAGE_DIR / "chart1_mappings_q"),
        ],
        check=True,
    )


def _scaled_box(image: Image.Image, box: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = box
    sx = image.width / BASE_RENDER_SIZE[0]
    sy = image.height / BASE_RENDER_SIZE[1]
    return (
        round(x0 * sx),
        round(y0 * sy),
        round(x1 * sx),
        round(y1 * sy),
    )


def validate_mapping(mapping: dict) -> list[str]:
    errors: list[str] = []
    source = mapping.get("source", {})
    forbidden = set(source.get("forbidden_use", []))
    allowed = set(source.get("allowed_use", []))
    rows = mapping.get("rows", [])
    row_ids = [row.get("int1") for row in rows]

    if source.get("status") != "reference_only":
        errors.append("source.status must be reference_only")
    if "canonical_asset_source" not in forbidden:
        errors.append("canonical_asset_source must be forbidden")
    if "crop_extract_svg" not in forbidden:
        errors.append("crop_extract_svg must be forbidden")
    if "s57_object_crosswalk" not in allowed:
        errors.append("s57_object_crosswalk must be allowed")
    if len(rows) != 62:
        errors.append(f"expected 62 Q-section rows, found {len(rows)}")
    if len(row_ids) != len(set(row_ids)):
        errors.append("duplicate INT 1 row ids found")
    missing_boxes = sorted(set(row_ids) - set(ROW_BOXES))
    extra_boxes = sorted(set(ROW_BOXES) - set(row_ids))
    if missing_boxes:
        errors.append(f"missing crop boxes for {missing_boxes}")
    if extra_boxes:
        errors.append(f"crop boxes without mapping rows for {extra_boxes}")
    return errors


def build_reference_crops() -> dict:
    mapping = load_mapping()
    errors = validate_mapping(mapping)
    if errors:
        raise ValueError("; ".join(errors))
    _ensure_page_renders(mapping)

    ROW_DIR.mkdir(parents=True, exist_ok=True)
    icon_dir = ROW_DIR / "icon_refs"
    icon_dir.mkdir(parents=True, exist_ok=True)

    entries = []
    missing_pages = []
    for row in mapping["rows"]:
        row_id = row["int1"]
        page, y0, y1 = ROW_BOXES[row_id]
        page_path = _page_image(page)
        if not page_path.exists():
            missing_pages.append(str(page_path.relative_to(ROOT)))
            continue

        with Image.open(page_path) as image:
            full_path = ROW_DIR / f"{row_id}.png"
            icon_path = icon_dir / f"{row_id}.png"
            full_box = _scaled_box(image, (X_FULL_ROW[0], y0, X_FULL_ROW[1], y1))
            icon_box = _scaled_box(image, (X_ICON_REF[0], y0, X_ICON_REF[1], y1))
            image.crop(full_box).save(full_path)
            image.crop(icon_box).save(icon_path)

        entries.append({
            "int1": row_id,
            "name": row["name"],
            "s57": row["s57"],
            "source_page": page,
            "render_page": page + RENDER_PAGE_OFFSET,
            "row_crop": str(full_path.relative_to(ROOT)),
            "icon_reference_crop": str(icon_path.relative_to(ROOT)),
            "crop_box_pixels": list(full_box),
            "icon_crop_box_pixels": list(icon_box),
            "render_size_pixels": list(image.size),
            "status": "reference_only_not_canonical_artwork",
        })

    report = {
        "status": "pass" if not missing_pages else "missing_page_renders",
        "source": mapping["source"],
        "rows_mapped": len(mapping["rows"]),
        "row_crops_written": len(entries),
        "missing_page_renders": sorted(set(missing_pages)),
        "reference_boundary": {
            "allowed_use": mapping["source"]["allowed_use"],
            "forbidden_use": mapping["source"]["forbidden_use"],
            "note": "Chart 1 Mappings crops are review references only and must not be converted into canonical SVG artwork.",
        },
        "entries": entries,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> int:
    report = build_reference_crops()
    print(json.dumps({
        "status": report["status"],
        "rows_mapped": report["rows_mapped"],
        "row_crops_written": report["row_crops_written"],
        "missing_page_renders": report["missing_page_renders"],
    }, indent=2))
    return 0 if report["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
