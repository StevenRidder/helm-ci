"""Build FORGE-45 visual and semantic diffs for electronic Chart 1 rows.

This proof artifact compares OpenCPN/S-52 reference renders with Helm S-57
candidate renders, joins S-101 trace and authority text, and emits row-level
visual/semantic gates. It never promotes runtime output.

Run:
  python3 -m forge.electronic_chart1_diff_engine
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageStat


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
OPENCPN_JSON = CATALOG / "electronic_chart1_opencpn_reference.json"
HELM_S57_JSON = CATALOG / "electronic_chart1_helm_s57_render.json"
HELM_S101_JSON = CATALOG / "electronic_chart1_helm_s101_render.json"
AUTHORITY_JSON = CATALOG / "electronic_chart1_authority_corpus.json"
DIFF_JSON = CATALOG / "electronic_chart1_diff_engine.json"
DIFF_MD = CATALOG / "electronic_chart1_diff_engine.md"
OUT_DIR = ROOT / "out" / "electronic_chart1_diff_engine"
SCHEMA = "helm.forge.electronic_chart1_diff_engine.v1"
PALETTES = ("day", "dusk", "night")

THRESHOLDS = {
    "point_symbol": {
        "green_alpha_iou_min": 0.72,
        "yellow_alpha_iou_min": 0.45,
        "green_mean_rgba_delta_max": 34.0,
        "yellow_mean_rgba_delta_max": 78.0,
    },
    "conditional_rule": {
        "green_alpha_iou_min": 0.68,
        "yellow_alpha_iou_min": 0.38,
        "green_mean_rgba_delta_max": 42.0,
        "yellow_mean_rgba_delta_max": 88.0,
    },
    "line_style": {
        "green_alpha_iou_min": 0.48,
        "yellow_alpha_iou_min": 0.20,
        "green_mean_rgba_delta_max": 58.0,
        "yellow_mean_rgba_delta_max": 104.0,
    },
    "area_fill": {
        "green_alpha_iou_min": 0.62,
        "yellow_alpha_iou_min": 0.30,
        "green_mean_rgba_delta_max": 54.0,
        "yellow_mean_rgba_delta_max": 105.0,
    },
    "text_rule": {
        "green_alpha_iou_min": 0.35,
        "yellow_alpha_iou_min": 0.12,
        "green_mean_rgba_delta_max": 72.0,
        "yellow_mean_rgba_delta_max": 118.0,
    },
}


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_canonical_json(payload))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _index_all(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for bucket in ("rows", "hard_pile"):
        for row in payload.get(bucket, []) or []:
            rows[row["row_key"]] = row
    return rows


def _index_rows(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["row_key"]: row for row in payload.get("rows", []) or []}


def _safe(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in value).strip("_")
    return safe or "unnamed"


def _image_path(metadata: dict[str, Any]) -> Path:
    return ROOT / metadata["path"]


def _artifact_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _open_rgba(path: Path) -> Image.Image:
    return Image.open(path).convert("RGBA")


def _bbox_iou(a: tuple[int, int, int, int] | None, b: tuple[int, int, int, int] | None) -> float:
    if a is None and b is None:
        return 1.0
    if a is None or b is None:
        return 0.0
    left = max(a[0], b[0])
    top = max(a[1], b[1])
    right = min(a[2], b[2])
    bottom = min(a[3], b[3])
    inter = max(0, right - left) * max(0, bottom - top)
    area_a = max(0, a[2] - a[0]) * max(0, a[3] - a[1])
    area_b = max(0, b[2] - b[0]) * max(0, b[3] - b[1])
    union = area_a + area_b - inter
    return inter / union if union else 0.0


def _alpha_iou(a: Image.Image, b: Image.Image) -> float:
    alpha_a = a.getchannel("A").point(lambda px: 255 if px else 0)
    alpha_b = b.getchannel("A").point(lambda px: 255 if px else 0)
    intersection = ImageChops.logical_and(alpha_a.convert("1"), alpha_b.convert("1"))
    union = ImageChops.logical_or(alpha_a.convert("1"), alpha_b.convert("1"))
    inter_count = sum(intersection.convert("L").histogram()[1:])
    union_count = sum(union.convert("L").histogram()[1:])
    return inter_count / union_count if union_count else 0.0


def _mean_rgba_delta(diff: Image.Image) -> float:
    stat = ImageStat.Stat(diff)
    return sum(stat.mean) / len(stat.mean)


def _changed_ratio(diff: Image.Image) -> float:
    gray = diff.convert("L")
    nonzero = sum(gray.point(lambda px: 255 if px else 0).histogram()[1:])
    return nonzero / float(gray.width * gray.height)


def _diff_image(diff: Image.Image) -> Image.Image:
    return diff.point(lambda px: min(255, px * 3))


def _metric_gate(row_taxonomy: str, alpha_iou: float, mean_delta: float) -> str:
    thresholds = THRESHOLDS[row_taxonomy]
    if (
        alpha_iou >= thresholds["green_alpha_iou_min"]
        and mean_delta <= thresholds["green_mean_rgba_delta_max"]
    ):
        return "green"
    if (
        alpha_iou >= thresholds["yellow_alpha_iou_min"]
        and mean_delta <= thresholds["yellow_mean_rgba_delta_max"]
    ):
        return "yellow"
    return "red"


def _compare_palette(
    *,
    row_key: str,
    chart1_row_id: str,
    palette: str,
    row_taxonomy: str,
    opencpn_meta: dict[str, Any],
    helm_meta: dict[str, Any],
    out_dir: Path,
) -> dict[str, Any]:
    opencpn_path = _image_path(opencpn_meta)
    helm_path = _image_path(helm_meta)
    opencpn_img = _open_rgba(opencpn_path)
    helm_img = _open_rgba(helm_path)
    if opencpn_img.size != helm_img.size:
        helm_img = helm_img.resize(opencpn_img.size, Image.Resampling.LANCZOS)
    diff = ImageChops.difference(opencpn_img, helm_img)
    out_dir.mkdir(parents=True, exist_ok=True)
    diff_path = out_dir / f"{chart1_row_id}__{_safe(row_key)}__{palette}__opencpn_vs_helm.png"
    _diff_image(diff).save(diff_path)
    opencpn_bbox = opencpn_img.getchannel("A").getbbox()
    helm_bbox = helm_img.getchannel("A").getbbox()
    alpha_iou = _alpha_iou(opencpn_img, helm_img)
    mean_delta = _mean_rgba_delta(diff)
    changed = _changed_ratio(diff)
    gate = _metric_gate(row_taxonomy, alpha_iou, mean_delta)
    return {
        "palette": palette,
        "gate": gate,
        "metrics": {
            "alpha_iou": round(alpha_iou, 6),
            "bbox_iou": round(_bbox_iou(opencpn_bbox, helm_bbox), 6),
            "changed_pixel_ratio": round(changed, 6),
            "mean_rgba_delta": round(mean_delta, 6),
        },
        "inputs": {
            "opencpn_path": opencpn_meta["path"],
            "opencpn_sha256": opencpn_meta["sha256"],
            "helm_path": helm_meta["path"],
            "helm_sha256": helm_meta["sha256"],
        },
        "diff_output": {
            "path": _artifact_path(diff_path),
            "sha256": _sha256(diff_path),
        },
    }


def _visual_gate(palette_diffs: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(item["gate"] for item in palette_diffs)
    if counts.get("red"):
        gate = "red"
    elif counts.get("yellow"):
        gate = "yellow"
    else:
        gate = "green"
    return {
        "gate": gate,
        "palette_gate_counts": dict(sorted(counts.items())),
        "reason_codes": [] if gate == "green" else [f"visual_palette:{item['palette']}:{item['gate']}" for item in palette_diffs if item["gate"] != "green"],
    }


def _semantic_gate(
    authority_row: dict[str, Any],
    s101_row: dict[str, Any] | None,
    helm_s57_row: dict[str, Any],
    opencpn_row: dict[str, Any],
) -> dict[str, Any]:
    reasons: list[str] = []
    authority_status = authority_row["helm_interpretation"]["status"]
    if authority_status != "authority_text_ready":
        reasons.append(f"authority:{authority_status}")
    if s101_row is None:
        reasons.append("s101_trace:missing")
    else:
        trace = s101_row["s101_trace"]
        if trace.get("classification") in {"unresolved", "semantic_only_manual", "non_s101_or_extension_profile", "non_s101_runtime_construct"}:
            reasons.append(f"s101_trace:{trace.get('classification')}")
        if not trace.get("db_backed"):
            reasons.append("s101_trace:db_backing_missing")
    recipe = (helm_s57_row.get("helm_trace") or {}).get("recipe") or {}
    if recipe.get("status") != "recipe_ready":
        reasons.append(f"helm_recipe:{recipe.get('status') or 'missing'}")
    opencpn_refs = set((opencpn_row.get("reference_trace") or {}).get("opencpn_refs_used") or [])
    helm_sources = set((helm_s57_row.get("helm_trace") or {}).get("render_sources") or [])
    if not opencpn_refs:
        reasons.append("opencpn_reference_refs:missing")
    if not helm_sources:
        reasons.append("helm_render_sources:missing")
    gate = "green" if not reasons else "yellow"
    if any(
        reason.startswith("s101_trace:unresolved")
        or reason.endswith(":missing")
        or reason.endswith("_missing")
        for reason in reasons
    ):
        gate = "red"
    return {
        "gate": gate,
        "reason_codes": sorted(set(reasons)),
        "authority_status": authority_status,
        "s101_classification": (s101_row or {}).get("s101_trace", {}).get("classification"),
        "helm_recipe_status": recipe.get("status"),
    }


def _proof_gate(visual: dict[str, Any], semantic: dict[str, Any], authority_row: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    if visual["gate"] != "green":
        reasons.append(f"visual_gate:{visual['gate']}")
    if semantic["gate"] != "green":
        reasons.append(f"semantic_gate:{semantic['gate']}")
    if not authority_row["runtime_gate"].get("runtime_eligible"):
        reasons.append("runtime_gate:fail_closed")
    if authority_row["helm_interpretation"].get("review_status") != "approved":
        reasons.append("human_qa:pending")
    if visual["gate"] == "red" or semantic["gate"] == "red":
        gate = "red"
    elif reasons:
        gate = "yellow"
    else:
        gate = "green"
    return {
        "gate": gate,
        "reason_codes": sorted(set(reasons)),
        "runtime_promoted": False,
        "runtime_promotion_allowed": False,
    }


def _hard_pile_row(
    authority_row: dict[str, Any],
    opencpn_row: dict[str, Any] | None,
    helm_s57_row: dict[str, Any] | None,
    s101_row: dict[str, Any] | None,
    reasons: list[str],
) -> dict[str, Any]:
    return {
        "chart1_row_id": authority_row["chart1_row_id"],
        "s52_lookup_id": authority_row["s52_lookup_id"],
        "row_key": authority_row["row_key"],
        "row_taxonomy": authority_row["row_taxonomy"],
        "status": "diff_hard_pile",
        "reason_codes": sorted(set(reasons)),
        "available_inputs": {
            "opencpn_reference": opencpn_row is not None,
            "helm_s57_render": helm_s57_row is not None,
            "helm_s101_trace": s101_row is not None,
            "authority": True,
        },
        "semantic_gate": {
            "authority_status": authority_row["helm_interpretation"]["status"],
            "source_language_gaps": authority_row.get("source_language_gaps") or [],
        },
        "runtime_gate": {
            "runtime_eligible": False,
            "fail_closed": True,
            "runtime_promotion_allowed": False,
        },
    }


def _build_row(
    authority_row: dict[str, Any],
    opencpn_row: dict[str, Any],
    helm_s57_row: dict[str, Any],
    s101_row: dict[str, Any] | None,
    out_dir: Path,
) -> dict[str, Any]:
    row_taxonomy = authority_row["row_taxonomy"]
    palette_diffs = []
    for palette in PALETTES:
        palette_diffs.append(_compare_palette(
            row_key=authority_row["row_key"],
            chart1_row_id=authority_row["chart1_row_id"],
            palette=palette,
            row_taxonomy=row_taxonomy,
            opencpn_meta=opencpn_row["palette_outputs"][palette],
            helm_meta=helm_s57_row["palette_outputs"][palette],
            out_dir=out_dir,
        ))
    visual = _visual_gate(palette_diffs)
    semantic = _semantic_gate(authority_row, s101_row, helm_s57_row, opencpn_row)
    proof = _proof_gate(visual, semantic, authority_row)
    return {
        "chart1_row_id": authority_row["chart1_row_id"],
        "s52_lookup_id": authority_row["s52_lookup_id"],
        "row_key": authority_row["row_key"],
        "row_taxonomy": row_taxonomy,
        "status": "diff_verdict",
        "visual_gate": visual,
        "semantic_gate": semantic,
        "proof_gate": proof,
        "palette_diffs": palette_diffs,
        "authority": {
            "status": authority_row["helm_interpretation"]["status"],
            "source_language_gaps": authority_row.get("source_language_gaps") or [],
            "text_sha256": authority_row["helm_interpretation"]["text_sha256"],
        },
        "s101_trace": {
            "present": s101_row is not None,
            "classification": (s101_row or {}).get("s101_trace", {}).get("classification"),
            "rule_file": (s101_row or {}).get("s101_trace", {}).get("rule_file"),
        },
        "runtime_gate": {
            "runtime_eligible": False,
            "fail_closed": True,
            "runtime_promotion_allowed": False,
        },
    }


def build_diff(
    *,
    opencpn_path: Path = OPENCPN_JSON,
    helm_s57_path: Path = HELM_S57_JSON,
    helm_s101_path: Path = HELM_S101_JSON,
    authority_path: Path = AUTHORITY_JSON,
    out_dir: Path = OUT_DIR,
    limit: int | None = None,
) -> dict[str, Any]:
    opencpn = _load_json(opencpn_path)
    helm_s57 = _load_json(helm_s57_path)
    helm_s101 = _load_json(helm_s101_path)
    authority = _load_json(authority_path)
    opencpn_rows = _index_rows(opencpn)
    helm_s57_rows = _index_rows(helm_s57)
    helm_s101_rows = _index_all(helm_s101)
    rows: list[dict[str, Any]] = []
    hard_pile: list[dict[str, Any]] = []
    for authority_row in authority["rows"][:limit]:
        reasons: list[str] = []
        row_taxonomy = authority_row["row_taxonomy"]
        opencpn_row = opencpn_rows.get(authority_row["row_key"])
        helm_s57_row = helm_s57_rows.get(authority_row["row_key"])
        s101_row = helm_s101_rows.get(authority_row["row_key"])
        if row_taxonomy not in THRESHOLDS:
            reasons.append(f"diff:unsupported_taxonomy:{row_taxonomy}")
        if opencpn_row is None:
            reasons.append("diff:opencpn_reference_missing")
        if helm_s57_row is None:
            reasons.append("diff:helm_s57_render_missing")
        if opencpn_row is not None and set(opencpn_row.get("palette_outputs") or {}) != set(PALETTES):
            reasons.append("diff:opencpn_palette_set_incomplete")
        if helm_s57_row is not None and set(helm_s57_row.get("palette_outputs") or {}) != set(PALETTES):
            reasons.append("diff:helm_s57_palette_set_incomplete")
        if reasons:
            hard_pile.append(_hard_pile_row(authority_row, opencpn_row, helm_s57_row, s101_row, reasons))
            continue
        rows.append(_build_row(authority_row, opencpn_row, helm_s57_row, s101_row, out_dir))

    summary = _summary(opencpn, helm_s57, helm_s101, authority, rows, hard_pile, limit)
    return {
        "schema": SCHEMA,
        "status": "electronic_chart1_diff_engine_ready" if summary["accounted_authority_rows"] == summary["authority_rows"] else "electronic_chart1_diff_engine_blocked",
        "policy": {
            "backend_generated": True,
            "browser_business_logic_allowed": False,
            "static_json_fallback_allowed": False,
            "runtime_promotion_allowed": False,
            "visual_diff_is_runtime_promotion": False,
            "missing_or_unsupported_rows_fail_closed": True,
            "clean_room_boundary": "OpenCPN renders are comparison references; Helm renders are generated-owned candidates.",
        },
        "thresholds": THRESHOLDS,
        "source": {
            "opencpn_reference": {"path": str(opencpn_path), "schema": opencpn["schema"], "sha256": _sha256(opencpn_path)},
            "helm_s57_render": {"path": str(helm_s57_path), "schema": helm_s57["schema"], "sha256": _sha256(helm_s57_path)},
            "helm_s101_trace": {"path": str(helm_s101_path), "schema": helm_s101["schema"], "sha256": _sha256(helm_s101_path)},
            "authority_corpus": {"path": str(authority_path), "schema": authority["schema"], "sha256": _sha256(authority_path)},
            "diff_output_dir": _artifact_path(out_dir),
        },
        "summary": summary,
        "rows": rows,
        "hard_pile": hard_pile,
    }


def _summary(
    opencpn: dict[str, Any],
    helm_s57: dict[str, Any],
    helm_s101: dict[str, Any],
    authority: dict[str, Any],
    rows: list[dict[str, Any]],
    hard_pile: list[dict[str, Any]],
    limit: int | None,
) -> dict[str, Any]:
    visual_counts = Counter(row["visual_gate"]["gate"] for row in rows)
    semantic_counts = Counter(row["semantic_gate"]["gate"] for row in rows)
    proof_counts = Counter(row["proof_gate"]["gate"] for row in rows)
    taxonomy_counts = Counter(row["row_taxonomy"] for row in rows)
    hard_reasons: Counter[str] = Counter()
    for row in hard_pile:
        hard_reasons.update(row["reason_codes"])
    palette_counts: Counter[str] = Counter()
    for row in rows:
        for diff in row["palette_diffs"]:
            palette_counts[diff["gate"]] += 1
    authority_rows = len(authority["rows"][:limit])
    return {
        "authority_rows": authority_rows,
        "diff_verdict_rows": len(rows),
        "diff_hard_pile_rows": len(hard_pile),
        "accounted_authority_rows": len(rows) + len(hard_pile),
        "opencpn_reference_rows": len(opencpn.get("rows") or []),
        "helm_s57_render_rows": len(helm_s57.get("rows") or []),
        "helm_s101_trace_rows": len(helm_s101.get("rows") or []),
        "helm_s101_fail_closed_rows": len(helm_s101.get("hard_pile") or []),
        "authority_text_ready_rows": authority["summary"]["status_counts"]["authority_text_ready"],
        "runtime_eligible_rows": 0,
        "diff_pngs": sum(len(row["palette_diffs"]) for row in rows),
        "visual_gate_counts": dict(sorted(visual_counts.items())),
        "semantic_gate_counts": dict(sorted(semantic_counts.items())),
        "proof_gate_counts": dict(sorted(proof_counts.items())),
        "palette_gate_counts": dict(sorted(palette_counts.items())),
        "row_taxonomy_counts": dict(sorted(taxonomy_counts.items())),
        "hard_pile_reason_counts": dict(hard_reasons.most_common(40)),
    }


def _markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Electronic Chart 1 Diff Engine",
        "",
        "FORGE-45 visual and semantic diff gates for Electronic Chart 1 rows.",
        "",
        f"- schema: `{payload['schema']}`",
        f"- status: `{payload['status']}`",
        f"- authority_rows: `{summary['authority_rows']}`",
        f"- diff_verdict_rows: `{summary['diff_verdict_rows']}`",
        f"- diff_hard_pile_rows: `{summary['diff_hard_pile_rows']}`",
        f"- diff_pngs: `{summary['diff_pngs']}`",
        f"- runtime_eligible_rows: `{summary['runtime_eligible_rows']}`",
        "",
        "## Policy",
        "",
        "- OpenCPN renders are comparison references, not Helm source artwork.",
        "- Helm renders are generated-owned candidates.",
        "- Unsupported or missing rows stay in hard-pile with reason codes.",
        "- Visual/semantic diff gates never promote runtime output by themselves.",
        "",
        "## Visual Gates",
        "",
        "| Gate | Count |",
        "| --- | ---: |",
    ]
    for gate, count in summary["visual_gate_counts"].items():
        lines.append(f"| `{gate}` | {count} |")
    lines.extend(["", "## Semantic Gates", "", "| Gate | Count |", "| --- | ---: |"])
    for gate, count in summary["semantic_gate_counts"].items():
        lines.append(f"| `{gate}` | {count} |")
    lines.extend(["", "## Proof Gates", "", "| Gate | Count |", "| --- | ---: |"])
    for gate, count in summary["proof_gate_counts"].items():
        lines.append(f"| `{gate}` | {count} |")
    lines.extend(["", "## Hard Pile Reasons", "", "| Reason | Count |", "| --- | ---: |"])
    for reason, count in summary["hard_pile_reason_counts"].items():
        lines.append(f"| `{reason}` | {count} |")
    return "\n".join(lines) + "\n"


def write_diff(
    *,
    opencpn_path: Path = OPENCPN_JSON,
    helm_s57_path: Path = HELM_S57_JSON,
    helm_s101_path: Path = HELM_S101_JSON,
    authority_path: Path = AUTHORITY_JSON,
    json_path: Path = DIFF_JSON,
    markdown_path: Path = DIFF_MD,
    out_dir: Path = OUT_DIR,
    limit: int | None = None,
) -> dict[str, Any]:
    payload = build_diff(
        opencpn_path=opencpn_path,
        helm_s57_path=helm_s57_path,
        helm_s101_path=helm_s101_path,
        authority_path=authority_path,
        out_dir=out_dir,
        limit=limit,
    )
    _write_json(json_path, payload)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(_markdown(payload))
    return {
        "status": payload["status"],
        "summary": payload["summary"],
        "json": str(json_path),
        "markdown": str(markdown_path),
        "out_dir": str(out_dir),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--opencpn-reference", type=Path, default=OPENCPN_JSON)
    parser.add_argument("--helm-s57-render", type=Path, default=HELM_S57_JSON)
    parser.add_argument("--helm-s101-trace", type=Path, default=HELM_S101_JSON)
    parser.add_argument("--authority-corpus", type=Path, default=AUTHORITY_JSON)
    parser.add_argument("--json", type=Path, default=DIFF_JSON)
    parser.add_argument("--markdown", type=Path, default=DIFF_MD)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args(argv)
    print(json.dumps(
        write_diff(
            opencpn_path=args.opencpn_reference,
            helm_s57_path=args.helm_s57_render,
            helm_s101_path=args.helm_s101_trace,
            authority_path=args.authority_corpus,
            json_path=args.json,
            markdown_path=args.markdown,
            out_dir=args.out_dir,
            limit=args.limit,
        ),
        indent=2,
        sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
