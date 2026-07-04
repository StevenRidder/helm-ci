"""Ingest the S-52 Presentation Library symbol catalogue as reference metadata.

This module extracts the local IHO S-52 Annex A Addendum PDF into a structured,
reference-only registry. It is not an artwork import path: the extracted data is
used for rule/QA context such as colour tokens, line weights, pivot points,
bounding boxes, S-57/INT 1 references, and source-page provenance.

Run:
  python3 -m forge.s52_preslib_symbol_catalog
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
TMP = ROOT / "tmp" / "s52_preslib"
DEFAULT_PDF = Path("/Users/steveridder/Downloads/S-52 PresLib Ed 4.0.3 Part I Addendum_Clean.pdf")
TEXT_CACHE = TMP / "s52_preslib_addendum.txt"
SOURCE_TABLE = CATALOG / "standard_source_table.json"
OUT_JSON = CATALOG / "s52_preslib_symbol_catalog.json"
OUT_CSV = CATALOG / "s52_preslib_symbol_catalog.csv"
OUT_MD = CATALOG / "s52_preslib_symbol_catalog.md"
JOIN_JSON = CATALOG / "s52_preslib_symbol_join.json"
JOIN_CSV = CATALOG / "s52_preslib_symbol_join.csv"
JOIN_MD = CATALOG / "s52_preslib_symbol_join.md"

EXPECTED_ENTRY_COUNT = 549
EXPECTED_PREFIX_COUNTS = {"AP": 25, "LC": 53, "SY": 471}
LABELS = [
    "Symbol Explanation:",
    "Look up table affected:",
    "Called by CSP etc.:",
    "Pivot Point Column:",
    "Pivot Point Row:",
    "Width of Bounding Box:",
    "Height of Bounding Box:",
    "Symbol Colours:",
    "Pattern Type:",
    "Pattern Spacing:",
    "Minimum Distance:",
    "Maximum Distance:",
    "Comments:",
    "Examples on ENC:",
    "References:",
]
OPTIONAL_LABELS = {
    "Called by CSP etc.:",
    "Pattern Type:",
    "Pattern Spacing:",
    "Minimum Distance:",
    "Maximum Distance:",
    "Examples on ENC:",
}
SOURCE_BOUNDARY = {
    "source_id": "iho_s52_preslib_ed_4_0_3_part_i_addendum",
    "status": "reference_only",
    "origin": "IHO S-52 Annex A Addendum to Part I: ENC Symbol Catalogue",
    "edition": "4.0(.3)",
    "clarifications_through": "December 2020",
    "allowed_use": [
        "s52_symbol_metadata_reference",
        "qa_invariants",
        "source_page_traceability",
        "s57_int1_crosscheck",
        "line_weight_colour_dimension_validation",
    ],
    "forbidden_use": [
        "canonical_asset_source",
        "artwork_import",
        "pixel_or_vector_trace",
        "public_package_text_republication_without_permission",
    ],
}


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _clean(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())


def _extract_text(pdf: Path) -> str:
    if not pdf.exists():
        raise FileNotFoundError(f"missing S-52 PresLib PDF: {pdf}")
    TMP.mkdir(parents=True, exist_ok=True)
    subprocess.run(["pdftotext", "-layout", str(pdf), str(TEXT_CACHE)], check=True)
    return TEXT_CACHE.read_text(errors="ignore")


def _line_value(line: str, label: str) -> str:
    return line.split(label, 1)[1].strip() if label in line else ""


def _field_blocks(block: str) -> dict[str, list[str]]:
    found: list[tuple[int, str, str]] = []
    for match in re.finditer(r"(?m)^[ \t]*([A-Za-z][A-Za-z0-9 .\/&-]*?:)", block):
        label = match.group(1)
        if label in LABELS:
            found.append((match.start(), label, match.group(0)))
    fields: dict[str, list[str]] = {}
    for index, (start, label, label_text) in enumerate(found):
        end = found[index + 1][0] if index + 1 < len(found) else len(block)
        chunk = block[start:end].splitlines()
        if not chunk:
            fields[label] = []
            continue
        first = _line_value(chunk[0], label)
        lines = [first] if first else []
        lines.extend(line.strip() for line in chunk[1:] if line.strip())
        fields[label] = [_clean(line) for line in lines if _clean(line)]
    return fields


def _first_float(fields: dict[str, list[str]], label: str) -> float | None:
    values = fields.get(label, [])
    if not values:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", values[0])
    return float(match.group(0)) if match else None


def _colours(fields: dict[str, list[str]]) -> list[str]:
    colours: list[str] = []
    for line in fields.get("Symbol Colours:", []):
        for token in re.findall(r"\b[A-Z][A-Z0-9]{2,}\b", line):
            if token not in {"N", "A", "INT", "S57"}:
                colours.append(token)
    return colours


def _section_for(prefix: str, page: int) -> str:
    if prefix == "LC" or page >= 477 and page < 533:
        return "complex_linestyles"
    if prefix == "AP" or page >= 533:
        return "area_patterns"
    return "point_and_centered_area_symbols"


def _reference_lines(fields: dict[str, list[str]]) -> list[str]:
    drop = {"S57 INT 1", "S57", "INT 1"}
    lines = []
    for line in fields.get("References:", []):
        if line in drop:
            continue
        if line.startswith("S-52 Annex A"):
            continue
        if "IHO ECDIS Presentation Library" in line:
            continue
        lines.append(line)
    return lines


def _s57_tokens(reference_lines: list[str]) -> list[str]:
    tokens: list[str] = []
    for line in reference_lines:
        match = re.match(r"^([A-Z$][A-Z0-9_$]{2,})\b", line)
        if match:
            token = match.group(1)
            if token not in {"INT", "S57"} and token not in tokens:
                tokens.append(token)
    return tokens


def _int1_refs(reference_lines: list[str]) -> list[str]:
    refs: list[str] = []
    for line in reference_lines:
        for ref in re.findall(r"\b[A-Z]\s*\d+(?:\.\d+)?(?:-\d+)?\b", line):
            cleaned = _clean(ref)
            if cleaned not in refs:
                refs.append(cleaned)
    return refs


def _parse_entry(block: str, page: int) -> dict:
    header = " ".join(block.splitlines()[:3])
    match = re.search(r"Symbol Name:\s*([A-Z]{2})\(([^)]+)\)\s+RN:\s*(\d+)?", header)
    if not match:
        raise ValueError(f"could not parse symbol header on PDF page {page}: {header[:160]}")
    prefix, symbol_id, rn_raw = match.groups()
    fields = _field_blocks(block)
    missing_labels = [
        label
        for label in LABELS
        if label not in OPTIONAL_LABELS and label not in fields
    ]
    references = _reference_lines(fields)
    return {
        "symbol_name": f"{prefix}({symbol_id})",
        "prefix": prefix,
        "symbol_id": symbol_id,
        "reference_number": int(rn_raw) if rn_raw else None,
        "pdf_page": page,
        "section": _section_for(prefix, page),
        "symbol_explanation": _clean(" ".join(fields.get("Symbol Explanation:", []))) or None,
        "lookup_tables_affected": fields.get("Look up table affected:", []),
        "called_by_csp": fields.get("Called by CSP etc.:", []),
        "pivot": {
            "column": _first_float(fields, "Pivot Point Column:"),
            "row": _first_float(fields, "Pivot Point Row:"),
        },
        "bounding_box": {
            "width": _first_float(fields, "Width of Bounding Box:"),
            "height": _first_float(fields, "Height of Bounding Box:"),
        },
        "symbol_colours": _colours(fields),
        "pattern": {
            "type": _clean(" ".join(fields.get("Pattern Type:", []))) or None,
            "spacing": _clean(" ".join(fields.get("Pattern Spacing:", []))) or None,
            "minimum_distance": _first_float(fields, "Minimum Distance:"),
            "maximum_distance": _first_float(fields, "Maximum Distance:"),
        },
        "comments": fields.get("Comments:", []),
        "examples_on_enc": _clean(" ".join(fields.get("Examples on ENC:", []))) or None,
        "references": {
            "lines": references,
            "s57_tokens": _s57_tokens(references),
            "int1_refs": _int1_refs(references),
        },
        "parse_warnings": (["reference_number_missing"] if rn_raw is None else []) + [
            f"missing_{label[:-1].lower().replace(' ', '_')}" for label in missing_labels
        ],
        "source_boundary": SOURCE_BOUNDARY,
    }


def parse_text(text: str) -> list[dict]:
    entries: list[dict] = []
    pages = text.split("\f")
    for page_number, page in enumerate(pages, 1):
        starts = [match.start() for match in re.finditer(r"(?m)^Symbol Name:", page)]
        for index, start in enumerate(starts):
            end = starts[index + 1] if index + 1 < len(starts) else len(page)
            entries.append(_parse_entry(page[start:end], page_number))
    return entries


def validate_entries(entries: list[dict]) -> list[str]:
    errors: list[str] = []
    names = [entry["symbol_name"] for entry in entries]
    counts = Counter(entry["prefix"] for entry in entries)
    if len(entries) != EXPECTED_ENTRY_COUNT:
        errors.append(f"expected {EXPECTED_ENTRY_COUNT} entries, parsed {len(entries)}")
    if dict(sorted(counts.items())) != EXPECTED_PREFIX_COUNTS:
        errors.append(f"prefix counts mismatch: {dict(sorted(counts.items()))}")
    duplicate_names = sorted(name for name, count in Counter(names).items() if count > 1)
    if duplicate_names != ["SY(CHDATD01)"]:
        errors.append(f"unexpected duplicate symbol names: {duplicate_names}")
    for entry in entries:
        if not entry["lookup_tables_affected"]:
            errors.append(f"{entry['symbol_name']} missing lookup table field")
        if entry["pivot"]["row"] is None:
            errors.append(f"{entry['symbol_name']} missing pivot row")
        if entry["bounding_box"]["height"] is None:
            errors.append(f"{entry['symbol_name']} missing bounding box height")
        if entry["prefix"] == "AP" and not entry["pattern"]["type"]:
            errors.append(f"{entry['symbol_name']} area pattern missing pattern type")
    return errors


def build_catalog(pdf: Path = DEFAULT_PDF) -> dict:
    text = _extract_text(pdf)
    entries = parse_text(text)
    errors = validate_entries(entries)
    if errors:
        raise ValueError("; ".join(errors))
    prefix_counts = Counter(entry["prefix"] for entry in entries)
    warning_counts = Counter(warning for entry in entries for warning in entry["parse_warnings"])
    pdfinfo = _pdfinfo(pdf)
    result = {
        "schema_version": 1,
        "status": "s52_preslib_symbol_catalog_written",
        "project": "vulkan",
        "task_id": "FORGE-15",
        "source": {
            **SOURCE_BOUNDARY,
            "local_pdf": str(pdf),
            "pdf_sha256": _sha256(pdf),
            "pdfinfo": pdfinfo,
        },
        "summary": {
            "entries": len(entries),
            "prefix_counts": dict(sorted(prefix_counts.items())),
            "entries_with_warnings": sum(1 for entry in entries if entry["parse_warnings"]),
            "warning_counts": dict(sorted(warning_counts.items())),
            "entries_with_s57_refs": sum(1 for entry in entries if entry["references"]["s57_tokens"]),
            "entries_with_int1_refs": sum(1 for entry in entries if entry["references"]["int1_refs"]),
            "area_patterns": prefix_counts["AP"],
            "complex_linestyles": prefix_counts["LC"],
            "point_symbols": prefix_counts["SY"],
        },
        "entries": entries,
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    _write_catalog_csv(entries)
    _write_catalog_md(result)
    _write_join(result)
    return result


def _pdfinfo(pdf: Path) -> dict:
    proc = subprocess.run(["pdfinfo", str(pdf)], check=True, text=True, capture_output=True)
    info = {}
    for line in proc.stdout.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        info[key.strip().lower().replace(" ", "_")] = value.strip()
    return info


def _write_catalog_csv(entries: list[dict]) -> None:
    fields = [
        "symbol_name",
        "prefix",
        "symbol_id",
        "reference_number",
        "pdf_page",
        "section",
        "symbol_explanation",
        "lookup_tables_affected",
        "called_by_csp",
        "pivot_column",
        "pivot_row",
        "bbox_width",
        "bbox_height",
        "symbol_colours",
        "pattern_type",
        "pattern_spacing",
        "minimum_distance",
        "maximum_distance",
        "comments",
        "s57_tokens",
        "int1_refs",
        "parse_warnings",
    ]
    with OUT_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for entry in entries:
            writer.writerow({
                "symbol_name": entry["symbol_name"],
                "prefix": entry["prefix"],
                "symbol_id": entry["symbol_id"],
                "reference_number": entry["reference_number"],
                "pdf_page": entry["pdf_page"],
                "section": entry["section"],
                "symbol_explanation": entry["symbol_explanation"],
                "lookup_tables_affected": "; ".join(entry["lookup_tables_affected"]),
                "called_by_csp": "; ".join(entry["called_by_csp"]),
                "pivot_column": entry["pivot"]["column"],
                "pivot_row": entry["pivot"]["row"],
                "bbox_width": entry["bounding_box"]["width"],
                "bbox_height": entry["bounding_box"]["height"],
                "symbol_colours": "; ".join(entry["symbol_colours"]),
                "pattern_type": entry["pattern"]["type"],
                "pattern_spacing": entry["pattern"]["spacing"],
                "minimum_distance": entry["pattern"]["minimum_distance"],
                "maximum_distance": entry["pattern"]["maximum_distance"],
                "comments": "; ".join(entry["comments"]),
                "s57_tokens": "; ".join(entry["references"]["s57_tokens"]),
                "int1_refs": "; ".join(entry["references"]["int1_refs"]),
                "parse_warnings": "; ".join(entry["parse_warnings"]),
            })


def _write_catalog_md(result: dict) -> None:
    summary = result["summary"]
    lines = [
        "# S-52 PresLib Symbol Catalogue",
        "",
        "Reference-only ingest of the IHO S-52 Annex A Addendum to Part I. This is QA metadata, not source artwork.",
        "",
        "## Summary",
        "",
        f"- Entries: {summary['entries']}",
        f"- Point/centered symbols: {summary['point_symbols']}",
        f"- Complex linestyles: {summary['complex_linestyles']}",
        f"- Area patterns: {summary['area_patterns']}",
        f"- Entries with S-57 refs: {summary['entries_with_s57_refs']}",
        f"- Entries with INT 1 refs: {summary['entries_with_int1_refs']}",
        f"- Entries with parse warnings: {summary['entries_with_warnings']}",
        "",
        "## Boundary",
        "",
        "- Allowed: S-52 metadata reference, QA invariants, source-page traceability, S-57/INT 1 cross-checks.",
        "- Forbidden: canonical asset source, artwork import, pixel/vector tracing, public package text republication without permission.",
        "",
        "## Warning Counts",
        "",
    ]
    if summary["warning_counts"]:
        for key, count in summary["warning_counts"].items():
            lines.append(f"- `{key}`: {count}")
    else:
        lines.append("- none")
    OUT_MD.write_text("\n".join(lines) + "\n")


def _source_rows_by_asset() -> dict[str, list[dict]]:
    if not SOURCE_TABLE.exists():
        return {}
    rows = _read_json(SOURCE_TABLE).get("rows", [])
    by_asset: dict[str, list[dict]] = {}
    for row in rows:
        by_asset.setdefault(str(row.get("asset", "")).upper(), []).append(row)
    return by_asset


def _write_join(catalog: dict) -> dict:
    by_asset = _source_rows_by_asset()
    records = []
    for entry in catalog["entries"]:
        matches = by_asset.get(entry["symbol_id"].upper(), [])
        records.append({
            "symbol_name": entry["symbol_name"],
            "symbol_id": entry["symbol_id"],
            "prefix": entry["prefix"],
            "pdf_page": entry["pdf_page"],
            "reference_number": entry["reference_number"],
            "match_count": len(matches),
            "matched_assets": [
                {
                    "asset": row.get("asset"),
                    "kind": row.get("kind"),
                    "family": row.get("family"),
                    "candidate_status": (row.get("helm_candidate") or {}).get("candidate_status"),
                    "source_table_id": row.get("source_table_id"),
                }
                for row in matches
            ],
            "match_status": "matched_standard_source_table_asset" if matches else "not_in_standard_source_table",
        })
    counts = Counter(record["match_status"] for record in records)
    result = {
        "schema_version": 1,
        "status": "s52_preslib_symbol_join_written",
        "source_catalog": "catalog/s52_preslib_symbol_catalog.json",
        "target_table": "catalog/standard_source_table.json",
        "summary": {
            "catalog_entries": len(records),
            "matched_entries": counts["matched_standard_source_table_asset"],
            "unmatched_entries": counts["not_in_standard_source_table"],
            "matched_asset_links": sum(record["match_count"] for record in records),
        },
        "records": records,
    }
    JOIN_JSON.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    with JOIN_CSV.open("w", newline="") as f:
        fields = ["symbol_name", "symbol_id", "prefix", "pdf_page", "reference_number", "match_count", "match_status", "matched_assets"]
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for record in records:
            writer.writerow({
                **{key: record[key] for key in fields if key != "matched_assets"},
                "matched_assets": "; ".join(row["asset"] for row in record["matched_assets"]),
            })
    lines = [
        "# S-52 PresLib Join Report",
        "",
        f"- Catalog entries: {result['summary']['catalog_entries']}",
        f"- Matched entries: {result['summary']['matched_entries']}",
        f"- Unmatched entries: {result['summary']['unmatched_entries']}",
        f"- Matched asset links: {result['summary']['matched_asset_links']}",
        "",
        "This report is a crosswalk only; it does not mutate `standard_source_table.json`.",
    ]
    JOIN_MD.write_text("\n".join(lines) + "\n")
    return result


def load_catalog() -> dict:
    return _read_json(OUT_JSON)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--json", action="store_true", help="print JSON summary")
    args = parser.parse_args()
    result = build_catalog(args.pdf)
    if args.json:
        print(json.dumps(result["summary"], indent=2, sort_keys=True))
    else:
        print(
            "s52 preslib symbol catalog: "
            f"{result['summary']['entries']} entries, "
            f"{result['summary']['entries_with_warnings']} warning rows"
        )


if __name__ == "__main__":
    main()
