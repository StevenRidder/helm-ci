"""Build the DB colour-authority contract for Icon Forge rows.

This contract keeps two truths separate:
- S-57/S-52 feature predicates describe the chart feature colour semantics.
- The selected Helm visual recipe/SVG describes the generated symbol colours.

Renderers consume the explicit authority decision instead of guessing from an
S-101 witness image, filename, or browser-side fallback.

Run:
  python3 -m forge.colour_authority_contract
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
SOURCE_TABLE = CATALOG / "standard_source_table.json"
REPORT_JSON = CATALOG / "colour_authority_contract.json"
REPORT_MD = CATALOG / "colour_authority_contract.md"

SCHEMA = "helm.iconforge.colour_authority_contract.v1"

FILL_VAR = re.compile(r"""\bfill\s*=\s*["']\s*var\(--([a-zA-Z0-9_-]+)\)\s*["']""")
STYLE_FILL_VAR = re.compile(r"""fill\s*:\s*var\(--([a-zA-Z0-9_-]+)\)""")
STROKE_VAR = re.compile(r"""\bstroke\s*=\s*["']\s*var\(--([a-zA-Z0-9_-]+)\)\s*["']""")
STYLE_STROKE_VAR = re.compile(r"""stroke\s*:\s*var\(--([a-zA-Z0-9_-]+)\)""")
DATA_PATTERN = re.compile(r"""data-pattern\s*=\s*["']([^"']+)["']""")

COLOUR_ALIASES = {
    "gray": "grey",
    "grey": "grey",
    "ink": "black",
}

LOAD_BEARING_COLOURS = {
    "black",
    "blue",
    "brown",
    "green",
    "grey",
    "magenta",
    "orange",
    "red",
    "white",
    "yellow",
}

PASS_STATUSES = {
    "aligned",
    "feature_empty_visual_defined",
    "not_colour_bearing",
}

BLOCKED_STATUSES = {
    "feature_colour_dropped",
    "feature_visual_order_difference",
    "missing_positive_not_colour_bearing_evidence",
    "missing_visual_witness",
    "pattern_orientation_conflict",
    "unresolved",
    "visual_colour_extra",
}

KNOWN_GATE_STATUSES = {"pass", "blocked", "pending"}


def _read_source_rows() -> list[dict[str, Any]]:
    return json.loads(SOURCE_TABLE.read_text()).get("rows", [])


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _normalise_colour(value: Any) -> str | None:
    text = str(value or "").strip().lower().replace("_", "-")
    if not text:
        return None
    text = COLOUR_ALIASES.get(text, text)
    if text not in LOAD_BEARING_COLOURS:
        return None
    return text


def _normalise_sequence(values: list[Any]) -> list[str]:
    out: list[str] = []
    for value in values:
        colour = _normalise_colour(value)
        if colour:
            out.append(colour)
    return out


def _unique_sequence(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _svg_sequences(svg: str) -> tuple[list[str], list[str], str, list[str]]:
    fill_sequence = _normalise_sequence(FILL_VAR.findall(svg) + STYLE_FILL_VAR.findall(svg))
    stroke_sequence = _normalise_sequence(STROKE_VAR.findall(svg) + STYLE_STROKE_VAR.findall(svg))
    pattern_tokens = []
    seen_patterns: set[str] = set()
    for token in DATA_PATTERN.findall(svg):
        if token not in seen_patterns:
            pattern_tokens.append(token)
            seen_patterns.add(token)

    notes: list[str] = []
    if fill_sequence:
        sequence = fill_sequence
        source = "svg_fill_tokens"
    elif stroke_sequence:
        sequence = stroke_sequence
        source = "svg_stroke_tokens_no_fill"
        notes.append("visual_colour_sequence_uses_strokes_because_no_fill_tokens_exist")
    else:
        sequence = []
        source = "svg_fill_tokens_empty"

    if pattern_tokens:
        pattern = ",".join(pattern_tokens)
    elif len(sequence) > 1:
        pattern = "ordered_sequence"
    elif len(sequence) == 1:
        pattern = "solid"
    else:
        pattern = "none"
    return sequence, stroke_sequence, pattern, notes + [f"visual_colour_source={source}"]


def _pattern_requirements(feature_pattern: str | None) -> list[str]:
    text = str(feature_pattern or "").lower()
    requirements: list[str] = []
    for token in ("horizontal", "vertical", "diagonal"):
        if token in text:
            requirements.append(token)
    if "squared" in text or "checkered" in text:
        requirements.append("checkered")
    if "border stripe" in text:
        requirements.append("border")
    return requirements


def _visual_pattern_evidence(visual_pattern: str) -> set[str]:
    text = str(visual_pattern or "").lower()
    evidence: set[str] = set()
    for token in ("horizontal", "vertical", "diagonal", "border"):
        if token in text:
            evidence.add(token)
    if "checkered" in text or "checker" in text or "squared" in text:
        evidence.add("checkered")
    return evidence


def _positive_not_colour_bearing_evidence(row: dict[str, Any]) -> list[str]:
    """Return positive evidence that a zero-colour row is intentionally non-colour-bearing."""
    semantic = row.get("semantic_brief") or {}
    notes: list[str] = []
    if semantic.get("colour_pattern"):
        return []
    use_case = str(semantic.get("use_case") or "").lower()
    shape = str(semantic.get("required_shape") or "").lower()
    name = str(row.get("name") or "").lower()
    text = " ".join([use_case, shape, name])
    if any(token in text for token in ("line", "arc", "boundary", "contour", "area", "coverage")):
        notes.append("semantic_context_marks_geometry_as_non_colour_bearing")
    if str(row.get("kind") or "") in {"line-style", "area-fill"}:
        notes.append("source_kind_is_non_symbol_paint_primitive")
    return notes


def _classify(
    *,
    row: dict[str, Any],
    feature_sequence: list[str],
    feature_pattern: str | None,
    visual_sequence: list[str],
    visual_pattern: str,
    missing_svg: bool,
    missing_feature_colours: list[str],
    extra_visual_colours: list[str],
) -> tuple[str, str, str, bool, list[str], list[str]]:
    evidence_notes: list[str] = []
    if missing_svg:
        return (
            "unresolved",
            "pending",
            "manual_review_required",
            True,
            ["colour_authority:svg_missing"],
            evidence_notes,
        )
    if feature_sequence and not visual_sequence:
        return (
            "missing_visual_witness",
            "blocked",
            "manual_review_required",
            True,
            ["colour_authority:missing_visual_witness"],
            evidence_notes,
        )
    if not feature_sequence and not visual_sequence:
        evidence_notes = _positive_not_colour_bearing_evidence(row)
        if not evidence_notes:
            return (
                "missing_positive_not_colour_bearing_evidence",
                "blocked",
                "manual_review_required",
                True,
                ["colour_authority:missing_positive_not_colour_bearing_evidence"],
                evidence_notes,
            )
        return (
            "not_colour_bearing",
            "pass",
            "not_colour_bearing",
            False,
            [],
            evidence_notes,
        )
    if not feature_sequence and visual_sequence:
        return (
            "feature_empty_visual_defined",
            "pass",
            "generated_visual_recipe",
            False,
            ["colour_authority:feature_empty_visual_defined"],
            evidence_notes,
        )
    if feature_sequence == visual_sequence:
        missing_patterns = [
            token
            for token in _pattern_requirements(feature_pattern)
            if token not in _visual_pattern_evidence(visual_pattern)
        ]
        if missing_patterns:
            return (
                "pattern_orientation_conflict",
                "blocked",
                "manual_review_required",
                True,
                [f"colour_authority:pattern_orientation_missing:{token}" for token in missing_patterns],
                evidence_notes,
            )
        return (
            "aligned",
            "pass",
            "feature_predicates_and_visual_recipe_aligned",
            False,
            [],
            evidence_notes,
        )
    if missing_feature_colours:
        return (
            "feature_colour_dropped",
            "blocked",
            "manual_review_required",
            True,
            ["colour_authority:feature_colour_dropped"],
            evidence_notes,
        )
    if extra_visual_colours:
        return (
            "visual_colour_extra",
            "blocked",
            "manual_review_required",
            True,
            ["colour_authority:visual_colour_extra"],
            evidence_notes,
        )
    return (
        "feature_visual_order_difference",
        "blocked",
        "manual_review_required",
        True,
        ["colour_authority:feature_visual_order_difference"],
        evidence_notes,
    )


def _row_contract(row: dict[str, Any]) -> dict[str, Any]:
    asset = str(row.get("asset") or "")
    semantic = row.get("semantic_brief") or {}
    helm = row.get("helm_candidate") or {}
    feature_sequence = _normalise_sequence(semantic.get("required_colours") or [])
    feature_pattern = semantic.get("colour_pattern")
    feature_unique = _normalise_sequence(semantic.get("unique_required_colours") or [])
    if not feature_unique:
        feature_unique = _unique_sequence(feature_sequence)

    svg_rel = helm.get("canonical_svg") or ""
    svg_path = ROOT / str(svg_rel) if svg_rel else None
    missing_svg = not bool(svg_path and svg_path.exists())
    if missing_svg:
        visual_sequence: list[str] = []
        stroke_sequence: list[str] = []
        visual_pattern = "missing_svg"
        notes = ["canonical_svg_missing_or_unreadable"]
    else:
        svg = svg_path.read_text()
        visual_sequence, stroke_sequence, visual_pattern, notes = _svg_sequences(svg)

    visual_unique = _unique_sequence(visual_sequence)
    missing_feature_colours = [colour for colour in feature_unique if colour not in visual_unique]
    extra_visual_colours = [colour for colour in visual_unique if colour not in feature_unique]

    status, gate_status, render_authority, runtime_blocker, reason_codes, evidence_notes = _classify(
        row=row,
        feature_sequence=feature_sequence,
        feature_pattern=feature_pattern,
        visual_sequence=visual_sequence,
        visual_pattern=visual_pattern,
        missing_svg=missing_svg,
        missing_feature_colours=missing_feature_colours,
        extra_visual_colours=extra_visual_colours,
    )

    if not reason_codes and gate_status == "pass":
        reason_codes = [f"colour_authority:{status}"]

    return {
        "schema": SCHEMA,
        "asset": asset,
        "name": row.get("name") or "",
        "kind": row.get("kind") or "",
        "status": status,
        "gate_status": gate_status,
        "runtime_blocker": runtime_blocker,
        "render_colour_authority": render_authority,
        "feature_colour_sequence": feature_sequence,
        "feature_unique_colours": feature_unique,
        "feature_colour_pattern": feature_pattern or "none",
        "feature_pattern_requirements": _pattern_requirements(feature_pattern),
        "missing_feature_colours": missing_feature_colours,
        "feature_colour_source": "semantic_brief.required_colours",
        "visual_colour_sequence": visual_sequence,
        "visual_unique_colours": visual_unique,
        "extra_visual_colours": extra_visual_colours,
        "visual_stroke_sequence": stroke_sequence,
        "visual_pattern": visual_pattern,
        "visual_pattern_evidence": sorted(_visual_pattern_evidence(visual_pattern)),
        "visual_colour_source": "helm_candidate.canonical_svg_css_fill_tokens",
        "canonical_svg": svg_rel,
        "candidate_status": helm.get("candidate_status") or "",
        "reason_codes": reason_codes,
        "notes": sorted(set(notes + evidence_notes)),
    }


def build() -> dict[str, Any]:
    rows = [_row_contract(row) for row in _read_source_rows()]
    status_counts = Counter(row["status"] for row in rows)
    gate_counts = Counter(row["gate_status"] for row in rows)
    missing_colour_counts = Counter(
        colour
        for row in rows
        for colour in row.get("missing_feature_colours") or []
    )
    extra_colour_counts = Counter(
        colour
        for row in rows
        for colour in row.get("extra_visual_colours") or []
    )
    result = {
        "schema": SCHEMA,
        "schema_version": 1,
        "status": "colour_authority_complete",
        "authority_policy": {
            "feature_colour_sequence": "S-57/S-52 feature predicates from semantic_brief.required_colours",
            "visual_colour_sequence": "ordered CSS fill tokens from the selected generated Helm SVG; stroke tokens are used when no fill tokens exist",
            "pattern_orientation_rule": "If S-57/S-52 semantics require horizontal, vertical, diagonal, checkered, or border pattern evidence, the selected SVG must carry matching data-pattern evidence before runtime eligibility.",
            "renderer_rule": (
                "Preserve feature predicates for audit/crosswalks. Use render_colour_authority "
                "to decide which colour sequence a renderer may bake for a generated visual recipe."
            ),
            "s101_witness_rule": "S-101 witnesses may support shape/rule evidence but are not colour-authoritative unless the row contract says so.",
            "fail_closed_rule": "Missing, unresolved, conflicting, unknown, or pattern-incomplete colour authority blocks runtime export.",
            "known_statuses": sorted(PASS_STATUSES | BLOCKED_STATUSES),
            "known_gate_statuses": sorted(KNOWN_GATE_STATUSES),
        },
        "summary": {
            "source_table_rows": len(rows),
            "rows": len(rows),
            "status_counts": dict(sorted(status_counts.items())),
            "gate_status_counts": dict(sorted(gate_counts.items())),
            "missing_feature_colour_counts": dict(sorted(missing_colour_counts.items())),
            "extra_visual_colour_counts": dict(sorted(extra_colour_counts.items())),
            "runtime_blocker_rows": sum(1 for row in rows if row["runtime_blocker"]),
        },
        "rows": sorted(rows, key=lambda row: (row["status"], row["asset"])),
    }
    _write_reports(result)
    return result


def _write_reports(result: dict[str, Any]) -> None:
    _write_json(REPORT_JSON, result)
    lines = [
        "# Colour Authority Contract",
        "",
        "DB-side contract separating feature colour predicates from generated visual colour recipes.",
        "",
        f"- schema: `{result['schema']}`",
        f"- rows: `{result['summary']['rows']}`",
        f"- runtime_blocker_rows: `{result['summary']['runtime_blocker_rows']}`",
        "",
        "## Status Counts",
        "",
        "| Status | Count |",
        "| --- | ---: |",
    ]
    for status, count in result["summary"]["status_counts"].items():
        lines.append(f"| `{status}` | {count} |")
    lines.extend([
        "",
        "## Policy",
        "",
        "- Feature colours remain the S-57/S-52 semantic predicates.",
        "- Visual colours are read from the selected generated Helm SVG/recipe.",
        "- S-101 witness images are not colour-authoritative by default.",
        "- Unresolved or missing colour authority fails closed.",
        "",
        "## Feature/Visual Colour Deltas",
        "",
        "| Asset | Status | Feature colours | Visual colours | Missing feature colours | Extra visual colours | Authority |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ])
    for row in result["rows"]:
        if row["status"] not in {
            "feature_colour_dropped",
            "feature_visual_order_difference",
            "missing_positive_not_colour_bearing_evidence",
            "missing_visual_witness",
            "pattern_orientation_conflict",
            "visual_colour_extra",
        }:
            continue
        feature = ", ".join(row["feature_colour_sequence"]) or "none"
        visual = ", ".join(row["visual_colour_sequence"]) or "none"
        missing = ", ".join(row.get("missing_feature_colours") or []) or "none"
        extra = ", ".join(row.get("extra_visual_colours") or []) or "none"
        lines.append(
            f"| `{row['asset']}` | `{row['status']}` | {feature} | {visual} | "
            f"{missing} | {extra} | `{row['render_colour_authority']}` |"
        )
    REPORT_MD.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path, default=REPORT_JSON)
    parser.add_argument("--markdown", type=Path, default=REPORT_MD)
    args = parser.parse_args()
    result = build()
    if args.json != REPORT_JSON:
        _write_json(args.json, result)
    if args.markdown != REPORT_MD:
        args.markdown.write_text(REPORT_MD.read_text())
    print(json.dumps({
        "status": result["status"],
        "rows": result["summary"]["rows"],
        "status_counts": result["summary"]["status_counts"],
        "runtime_blocker_rows": result["summary"]["runtime_blocker_rows"],
        "json": _display_path(args.json),
        "markdown": _display_path(args.markdown),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
