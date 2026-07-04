"""Build CHART-8 OpenCPN baseline comparison manifests.

This support harness joins Forge fixture renders, OpenCPN reference renders,
visual-diff metrics, proof-bundle state, and human approval state. OpenCPN
pixels remain reference/comparison evidence only; they are never canonical Helm
artwork or runtime promotion evidence by themselves.

Run:
  python3 -m forge.electronic_chart1_opencpn_baseline
  python3 -m forge.tests.test_electronic_chart1_opencpn_baseline
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
PROOF = ROOT / "proof"

DIFF_JSON = CATALOG / "electronic_chart1_diff_engine.json"
OPENCPN_JSON = CATALOG / "electronic_chart1_opencpn_reference.json"
HELM_S57_JSON = CATALOG / "electronic_chart1_helm_s57_render.json"
PROOF_DATA_JSON = PROOF / "package-proof-data.json"
BASELINE_JSON = CATALOG / "electronic_chart1_opencpn_baseline.json"
BASELINE_MD = CATALOG / "electronic_chart1_opencpn_baseline.md"

SCHEMA = "helm.forge.electronic_chart1_opencpn_baseline.v1"
PALETTES = ("day", "dusk", "night")

CHECK_THRESHOLDS = {
    "wrong_palette": {
        "metric": "mean_rgba_delta",
        "max": "diff_engine.yellow_mean_rgba_delta_max",
        "failure_reason": "palette_or_colour_delta_exceeds_review_tolerance",
    },
    "wrong_symbol_class": {
        "metric": "alpha_iou",
        "min": "diff_engine.yellow_alpha_iou_min",
        "failure_reason": "silhouette_overlap_below_review_tolerance",
    },
    "wrong_anchor": {
        "metric": "bbox_iou",
        "min": 0.60,
        "failure_reason": "alpha_bbox_alignment_below_anchor_tolerance",
    },
    "blank_render": {
        "metric": "nonblank",
        "expected": True,
        "failure_reason": "reference_or_candidate_render_blank",
    },
}


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n"


def _write_json(path: Path, payload: Any) -> None:
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


def _index_rows(payload: dict[str, Any], *buckets: str) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for bucket in buckets:
        for row in payload.get(bucket) or []:
            row_key = row.get("row_key")
            if row_key:
                rows[str(row_key)] = row
    return rows


def _proof_index(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return _index_rows(payload, "rows")


def _thresholds_for(row_taxonomy: str, diff_payload: dict[str, Any]) -> dict[str, float]:
    thresholds = diff_payload["thresholds"].get(row_taxonomy)
    if thresholds is None:
        return {}
    return {
        "alpha_iou_min": float(thresholds["yellow_alpha_iou_min"]),
        "mean_rgba_delta_max": float(thresholds["yellow_mean_rgba_delta_max"]),
        "bbox_iou_min": float(CHECK_THRESHOLDS["wrong_anchor"]["min"]),
    }


def _render_meta(row: dict[str, Any] | None, palette: str) -> dict[str, Any]:
    if row is None:
        return {}
    return ((row.get("palette_outputs") or {}).get(palette) or {})


def _asset_payload(meta: dict[str, Any], *, role: str) -> dict[str, Any]:
    return {
        "role": role,
        "path": meta.get("path"),
        "sha256": meta.get("sha256"),
        "exists": bool(meta.get("path")),
        "nonblank": meta.get("nonblank"),
        "alpha_bbox": meta.get("alpha_bbox"),
    }


def _check(status: str, *, metric: str, threshold: Any, observed: Any, reason: str | None = None) -> dict[str, Any]:
    payload = {
        "status": status,
        "metric": metric,
        "threshold": threshold,
        "observed": observed,
    }
    if reason:
        payload["reason"] = reason
    return payload


def _palette_checks(
    *,
    palette_diff: dict[str, Any],
    opencpn_meta: dict[str, Any],
    helm_meta: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, dict[str, Any]]:
    metrics = palette_diff["metrics"]
    palette_max = thresholds["mean_rgba_delta_max"]
    alpha_min = thresholds["alpha_iou_min"]
    bbox_min = thresholds["bbox_iou_min"]
    opencpn_nonblank = opencpn_meta.get("nonblank") is True
    helm_nonblank = helm_meta.get("nonblank") is True
    return {
        "wrong_palette": _check(
            "pass" if metrics["mean_rgba_delta"] <= palette_max else "needs-review",
            metric="mean_rgba_delta",
            threshold={"max": palette_max},
            observed=metrics["mean_rgba_delta"],
            reason=None if metrics["mean_rgba_delta"] <= palette_max else CHECK_THRESHOLDS["wrong_palette"]["failure_reason"],
        ),
        "wrong_symbol_class": _check(
            "pass" if metrics["alpha_iou"] >= alpha_min else "needs-review",
            metric="alpha_iou",
            threshold={"min": alpha_min},
            observed=metrics["alpha_iou"],
            reason=None if metrics["alpha_iou"] >= alpha_min else CHECK_THRESHOLDS["wrong_symbol_class"]["failure_reason"],
        ),
        "wrong_anchor": _check(
            "pass" if metrics["bbox_iou"] >= bbox_min else "needs-review",
            metric="bbox_iou",
            threshold={"min": bbox_min},
            observed=metrics["bbox_iou"],
            reason=None if metrics["bbox_iou"] >= bbox_min else CHECK_THRESHOLDS["wrong_anchor"]["failure_reason"],
        ),
        "blank_render": _check(
            "pass" if opencpn_nonblank and helm_nonblank else "needs-review",
            metric="nonblank",
            threshold={"opencpn": True, "helm_candidate": True},
            observed={"opencpn": opencpn_nonblank, "helm_candidate": helm_nonblank},
            reason=None if opencpn_nonblank and helm_nonblank else CHECK_THRESHOLDS["blank_render"]["failure_reason"],
        ),
    }


def _palette_manifest(
    *,
    diff_row: dict[str, Any],
    opencpn_row: dict[str, Any] | None,
    helm_row: dict[str, Any] | None,
    diff_payload: dict[str, Any],
) -> dict[str, Any]:
    thresholds = _thresholds_for(diff_row["row_taxonomy"], diff_payload)
    palette_diffs = {item["palette"]: item for item in diff_row["palette_diffs"]}
    palettes: dict[str, Any] = {}
    for palette in PALETTES:
        palette_diff = palette_diffs[palette]
        opencpn_meta = _render_meta(opencpn_row, palette)
        helm_meta = _render_meta(helm_row, palette)
        visual_diff = palette_diff.get("diff_output") or {}
        checks = _palette_checks(
            palette_diff=palette_diff,
            opencpn_meta=opencpn_meta,
            helm_meta=helm_meta,
            thresholds=thresholds,
        )
        palettes[palette] = {
            "palette": palette,
            "opencpn_reference": _asset_payload(opencpn_meta, role="reference_comparison_only"),
            "helm_fixture_render": _asset_payload(helm_meta, role="generated_owned_candidate"),
            "visual_diff": {
                "role": "comparison_diagnostic_only",
                "path": visual_diff.get("path"),
                "sha256": visual_diff.get("sha256"),
                "exists": bool(visual_diff.get("path")),
            },
            "metrics": palette_diff["metrics"],
            "diff_gate": palette_diff["gate"],
            "tolerance_checks": checks,
            "status": "pass" if all(check["status"] == "pass" for check in checks.values()) else "needs-review",
        }
    return palettes


def _human_approval(proof_row: dict[str, Any] | None, diff_row: dict[str, Any]) -> dict[str, Any]:
    gates = (proof_row or {}).get("gates") or {}
    human_review_status = gates.get("human_review_status") or "needs_human_review"
    return {
        "status": human_review_status,
        "final_approved": human_review_status == "approved",
        "runtime_promotion_allowed": bool(
            ((proof_row or {}).get("runtime") or {}).get("promotion_allowed")
            or ((diff_row.get("runtime_gate") or {}).get("runtime_promotion_allowed"))
        ),
        "source": "proof/package-proof-data.json" if proof_row else "diff_engine_default_fail_closed",
    }


def _comparison_status(palettes: dict[str, Any], diff_row: dict[str, Any]) -> str:
    if any(palette["status"] != "pass" for palette in palettes.values()):
        return "needs-review"
    if diff_row["visual_gate"]["gate"] != "green":
        return "needs-review"
    if diff_row["semantic_gate"]["gate"] != "green":
        return "needs-review"
    return "pass"


def _baseline_row(
    *,
    diff_row: dict[str, Any],
    opencpn_row: dict[str, Any] | None,
    helm_row: dict[str, Any] | None,
    proof_row: dict[str, Any] | None,
    diff_payload: dict[str, Any],
) -> dict[str, Any]:
    palettes = _palette_manifest(
        diff_row=diff_row,
        opencpn_row=opencpn_row,
        helm_row=helm_row,
        diff_payload=diff_payload,
    )
    status = _comparison_status(palettes, diff_row)
    return {
        "chart1_row_id": diff_row["chart1_row_id"],
        "s52_lookup_id": diff_row["s52_lookup_id"],
        "row_key": diff_row["row_key"],
        "row_taxonomy": diff_row["row_taxonomy"],
        "symbol_id": (proof_row or {}).get("symbol_id"),
        "comparison_status": status,
        "status_reason_codes": sorted(set(
            [f"visual_gate:{diff_row['visual_gate']['gate']}"]
            + [f"semantic_gate:{diff_row['semantic_gate']['gate']}"]
            + [reason for palette in palettes.values() for check in palette["tolerance_checks"].values() for reason in [check.get("reason")] if reason]
        )),
        "roles": {
            "opencpn": "reference_comparison_only",
            "helm_fixture_render": "generated_owned_candidate",
            "visual_diff": "comparison_diagnostic_only",
        },
        "palettes": palettes,
        "visual_gate": diff_row["visual_gate"],
        "semantic_gate": diff_row["semantic_gate"],
        "proof_gate": diff_row["proof_gate"],
        "human_approval": _human_approval(proof_row, diff_row),
        "proof_bundle": {
            "proof_data_path": "proof/package-proof-data.json",
            "comparison_page": "proof/compare-opencpn.html",
            "row_key": diff_row["row_key"],
            "proof_row_present": proof_row is not None,
            "proof_status": (proof_row or {}).get("status"),
        },
        "runtime_gate": {
            "runtime_eligible": False,
            "runtime_promotion_allowed": False,
            "comparison_promotes_runtime": False,
        },
    }


def _not_comparable_row(
    *,
    hard_row: dict[str, Any],
    opencpn_row: dict[str, Any] | None,
    helm_row: dict[str, Any] | None,
    proof_row: dict[str, Any] | None,
) -> dict[str, Any]:
    palettes: dict[str, Any] = {}
    for palette in PALETTES:
        opencpn_meta = _render_meta(opencpn_row, palette)
        helm_meta = _render_meta(helm_row, palette)
        palettes[palette] = {
            "palette": palette,
            "opencpn_reference": _asset_payload(opencpn_meta, role="reference_comparison_only"),
            "helm_fixture_render": _asset_payload(helm_meta, role="generated_owned_candidate"),
            "visual_diff": {
                "role": "comparison_diagnostic_only",
                "path": None,
                "sha256": None,
                "exists": False,
            },
            "metrics": None,
            "diff_gate": "not-comparable",
            "tolerance_checks": {
                name: _check(
                    "not-comparable",
                    metric=str(rule["metric"]),
                    threshold={key: value for key, value in rule.items() if key in {"min", "max", "expected"}},
                    observed=None,
                    reason="missing_or_unsupported_comparison_input",
                )
                for name, rule in CHECK_THRESHOLDS.items()
            },
            "status": "not-comparable",
        }
    return {
        "chart1_row_id": hard_row["chart1_row_id"],
        "s52_lookup_id": hard_row["s52_lookup_id"],
        "row_key": hard_row["row_key"],
        "row_taxonomy": hard_row["row_taxonomy"],
        "symbol_id": (proof_row or {}).get("symbol_id"),
        "comparison_status": "not-comparable",
        "status_reason_codes": hard_row.get("reason_codes") or [],
        "roles": {
            "opencpn": "reference_comparison_only",
            "helm_fixture_render": "generated_owned_candidate",
            "visual_diff": "comparison_diagnostic_only",
        },
        "palettes": palettes,
        "visual_gate": {"gate": "not-comparable", "reason_codes": hard_row.get("reason_codes") or []},
        "semantic_gate": hard_row.get("semantic_gate") or {},
        "proof_gate": {
            "gate": "not-comparable",
            "reason_codes": hard_row.get("reason_codes") or [],
            "runtime_promoted": False,
            "runtime_promotion_allowed": False,
        },
        "human_approval": {
            "status": ((proof_row or {}).get("gates") or {}).get("human_review_status") or "needs_human_review",
            "final_approved": False,
            "runtime_promotion_allowed": False,
            "source": "proof/package-proof-data.json" if proof_row else "diff_engine_default_fail_closed",
        },
        "proof_bundle": {
            "proof_data_path": "proof/package-proof-data.json",
            "comparison_page": "proof/compare-opencpn.html",
            "row_key": hard_row["row_key"],
            "proof_row_present": proof_row is not None,
            "proof_status": (proof_row or {}).get("status"),
        },
        "runtime_gate": {
            "runtime_eligible": False,
            "runtime_promotion_allowed": False,
            "comparison_promotes_runtime": False,
        },
    }


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts = Counter(row["comparison_status"] for row in rows)
    taxonomy_counts = Counter(row["row_taxonomy"] for row in rows)
    palette_status_counts: Counter[str] = Counter()
    check_status_counts: Counter[str] = Counter()
    check_failure_counts: Counter[str] = Counter()
    human_counts = Counter(row["human_approval"]["status"] for row in rows)
    rows_with_all_refs = 0
    for row in rows:
        row_has_all_refs = True
        for palette in row["palettes"].values():
            palette_status_counts[palette["status"]] += 1
            if not palette["opencpn_reference"]["path"]:
                row_has_all_refs = False
            for check_name, check in palette["tolerance_checks"].items():
                check_status_counts[f"{check_name}:{check['status']}"] += 1
                if check.get("reason"):
                    check_failure_counts[f"{check_name}:{check['reason']}"] += 1
        if row_has_all_refs:
            rows_with_all_refs += 1
    return {
        "rows": len(rows),
        "status_counts": dict(sorted(status_counts.items())),
        "row_taxonomy_counts": dict(sorted(taxonomy_counts.items())),
        "palette_status_counts": dict(sorted(palette_status_counts.items())),
        "check_status_counts": dict(sorted(check_status_counts.items())),
        "check_failure_counts": dict(check_failure_counts.most_common(40)),
        "human_approval_status_counts": dict(sorted(human_counts.items())),
        "rows_with_all_opencpn_palette_refs": rows_with_all_refs,
        "runtime_promotion_allowed_rows": 0,
    }


def build_baseline(
    *,
    diff_path: Path = DIFF_JSON,
    opencpn_path: Path = OPENCPN_JSON,
    helm_s57_path: Path = HELM_S57_JSON,
    proof_data_path: Path = PROOF_DATA_JSON,
) -> dict[str, Any]:
    diff = _load_json(diff_path)
    opencpn = _load_json(opencpn_path)
    helm_s57 = _load_json(helm_s57_path)
    proof_data = _load_json(proof_data_path)
    opencpn_rows = _index_rows(opencpn, "rows", "hard_pile")
    helm_rows = _index_rows(helm_s57, "rows", "hard_pile")
    proof_rows = _proof_index(proof_data)
    rows = [
        _baseline_row(
            diff_row=diff_row,
            opencpn_row=opencpn_rows.get(diff_row["row_key"]),
            helm_row=helm_rows.get(diff_row["row_key"]),
            proof_row=proof_rows.get(diff_row["row_key"]),
            diff_payload=diff,
        )
        for diff_row in diff.get("rows") or []
    ]
    rows.extend(
        _not_comparable_row(
            hard_row=hard_row,
            opencpn_row=opencpn_rows.get(hard_row["row_key"]),
            helm_row=helm_rows.get(hard_row["row_key"]),
            proof_row=proof_rows.get(hard_row["row_key"]),
        )
        for hard_row in diff.get("hard_pile") or []
    )
    rows.sort(key=lambda row: (row["chart1_row_id"], row["row_key"]))
    return {
        "schema": SCHEMA,
        "status": "opencpn_baseline_comparison_ready",
        "policy": {
            "backend_generated": True,
            "opencpn_role": "reference_comparison_only",
            "helm_outputs_role": "generated_owned_candidate",
            "visual_diff_role": "comparison_diagnostic_only",
            "runtime_promotion_allowed": False,
            "comparison_pixels_are_source_artwork": False,
            "missing_or_unsupported_rows_status": "not-comparable",
        },
        "source": {
            "diff_engine": {"path": str(diff_path), "schema": diff["schema"], "sha256": _sha256(diff_path)},
            "opencpn_reference": {"path": str(opencpn_path), "schema": opencpn["schema"], "sha256": _sha256(opencpn_path)},
            "helm_s57_render": {"path": str(helm_s57_path), "schema": helm_s57["schema"], "sha256": _sha256(helm_s57_path)},
            "proof_data": {"path": str(proof_data_path), "schema": proof_data["schema"], "sha256": _sha256(proof_data_path)},
        },
        "tolerance_checks": CHECK_THRESHOLDS,
        "summary": _summary(rows),
        "rows": rows,
    }


def _markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Electronic Chart 1 OpenCPN Baseline Comparison",
        "",
        "CHART-8 manifest joining Forge renders to OpenCPN day/dusk/night reference outputs.",
        "",
        f"- schema: `{payload['schema']}`",
        f"- status: `{payload['status']}`",
        f"- rows: `{summary['rows']}`",
        f"- runtime_promotion_allowed_rows: `{summary['runtime_promotion_allowed_rows']}`",
        "",
        "## Source Boundary",
        "",
        "- OpenCPN render paths are reference/comparison only.",
        "- Helm fixture renders are generated-owned candidates.",
        "- Visual diffs and tolerance checks are QA diagnostics, not runtime promotion.",
        "",
        "## Comparison Status",
        "",
        "| Status | Count |",
        "| --- | ---: |",
    ]
    for status, count in summary["status_counts"].items():
        lines.append(f"| `{status}` | {count} |")
    lines.extend(["", "## Tolerance Checks", "", "| Check/status | Count |", "| --- | ---: |"])
    for status, count in summary["check_status_counts"].items():
        lines.append(f"| `{status}` | {count} |")
    lines.extend(["", "## Human Approval", "", "| State | Count |", "| --- | ---: |"])
    for status, count in summary["human_approval_status_counts"].items():
        lines.append(f"| `{status}` | {count} |")
    return "\n".join(lines) + "\n"


def write_baseline(
    *,
    diff_path: Path = DIFF_JSON,
    opencpn_path: Path = OPENCPN_JSON,
    helm_s57_path: Path = HELM_S57_JSON,
    proof_data_path: Path = PROOF_DATA_JSON,
    json_path: Path = BASELINE_JSON,
    markdown_path: Path = BASELINE_MD,
) -> dict[str, Any]:
    payload = build_baseline(
        diff_path=diff_path,
        opencpn_path=opencpn_path,
        helm_s57_path=helm_s57_path,
        proof_data_path=proof_data_path,
    )
    _write_json(json_path, payload)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(_markdown(payload))
    return {
        "status": payload["status"],
        "summary": payload["summary"],
        "json": str(json_path),
        "markdown": str(markdown_path),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diff", type=Path, default=DIFF_JSON)
    parser.add_argument("--opencpn-reference", type=Path, default=OPENCPN_JSON)
    parser.add_argument("--helm-s57-render", type=Path, default=HELM_S57_JSON)
    parser.add_argument("--proof-data", type=Path, default=PROOF_DATA_JSON)
    parser.add_argument("--json", type=Path, default=BASELINE_JSON)
    parser.add_argument("--markdown", type=Path, default=BASELINE_MD)
    args = parser.parse_args(argv)
    print(json.dumps(
        write_baseline(
            diff_path=args.diff,
            opencpn_path=args.opencpn_reference,
            helm_s57_path=args.helm_s57_render,
            proof_data_path=args.proof_data,
            json_path=args.json,
            markdown_path=args.markdown,
        ),
        indent=2,
        sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
