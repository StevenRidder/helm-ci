"""FORGE-47 runtime promotion gate for Electronic Chart 1 proof rows.

This module is the latch between the backend proof bundle and any runtime
symbol package. It intentionally defaults to zero runtime rows. A row may be
exported only when the proof bundle, authority trace, S-101 trace, render
evidence, clean-room provenance, and human/QA gates all agree.

Run:
  python3 -m forge.electronic_chart1_runtime_promotion_gate
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
DEFAULT_PROOF_DIR = ROOT / "out" / "electronic_chart1_proof_bundle"
DEFAULT_JSON = CATALOG / "electronic_chart1_runtime_promotion_gate.json"
DEFAULT_MD = CATALOG / "electronic_chart1_runtime_promotion_gate.md"

SCHEMA = "helm.forge.electronic_chart1_runtime_promotion_gate.v1"
RUNTIME_EXPORT_SCHEMA = "helm.runtime.electronic_chart1_symbol_export.v1"
READY_S101_CLASSES = {"direct", "rule_derived", "catalogue_rule", "documented_deviation"}
PALETTES = ("day", "dusk", "night")


REMEDIATION_HINTS = {
    "proof_bundle:hard_pile": "Repair missing proof inputs before runtime review.",
    "visual_gate": "Repair Helm visual output and rerun the visual diff engine.",
    "semantic_gate": "Repair authority, S-57, S-101, or recipe semantics and rerun proof.",
    "proof_gate": "Clear proof-bundle blockers before runtime review.",
    "runtime_gate:runtime_eligible_false": "Set runtime eligibility only from the DB promotion contract after every gate passes.",
    "runtime_gate:promotion_not_allowed": "Keep runtime promotion blocked until the backend gate explicitly allows it.",
    "runtime_gate:fail_closed": "Resolve the fail-closed runtime gate in the DB contract.",
    "authority_status": "Complete backend authority text and source-language evidence.",
    "human_review_status": "Record final QA/human approval outside the proof UI.",
    "review_controls": "Repair proof UI controls; UI review cannot grant runtime eligibility.",
    "s101_trace": "Repair S-101 resolver trace, DB backing, rule evidence, or mapping classification.",
    "s101_rule": "Attach deterministic S-101 rule/catalogue evidence for rule-derived rows.",
    "render_trace": "Regenerate render outputs with source paths and sha256 hashes.",
    "clean_room": "Attach backend clean-room provenance text.",
}


def _canonical_json(payload: Any) -> str:
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
    if not path.exists():
        raise FileNotFoundError(f"required proof artifact is missing: {path}")
    return json.loads(path.read_text())


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _reason_hint(reason: str) -> str:
    for prefix, hint in REMEDIATION_HINTS.items():
        if reason.startswith(prefix):
            return hint
    return "Repair the source evidence that produced this blocker and rerun the proof chain."


def _add_reason(reasons: list[str], reason: str) -> None:
    if reason and reason not in reasons:
        reasons.append(reason)


def _gate_value(row: dict[str, Any], gate_name: str) -> str | None:
    return (((row.get("gates") or {}).get(gate_name) or {}).get("gate"))


def _s101_trace(row: dict[str, Any]) -> dict[str, Any]:
    return (((row.get("standards") or {}).get("s101") or {}).get("trace") or {})


def _media_source_hashes(row: dict[str, Any]) -> dict[str, dict[str, dict[str, str | None]]]:
    hashes: dict[str, dict[str, dict[str, str | None]]] = {}
    for palette in PALETTES:
        palette_media = ((row.get("media") or {}).get(palette) or {})
        hashes[palette] = {}
        for role in ("opencpn", "helm_s57", "helm_s101", "visual_diff"):
            media = palette_media.get(role) or {}
            hashes[palette][role] = {
                "source_path": media.get("source_path"),
                "source_sha256": media.get("source_sha256"),
                "bundle_sha256": media.get("bundle_sha256"),
            }
    return hashes


def _render_trace_missing(row: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    s101_present = (((row.get("standards") or {}).get("s101") or {}).get("present") is True)
    required_roles = ["opencpn", "helm_s57", "visual_diff"]
    if s101_present:
        required_roles.append("helm_s101")
    for palette in PALETTES:
        palette_media = ((row.get("media") or {}).get(palette) or {})
        for role in required_roles:
            media = palette_media.get(role) or {}
            if not media.get("source_path"):
                missing.append(f"render_trace:{palette}:{role}:source_path_missing")
            if not media.get("source_sha256"):
                missing.append(f"render_trace:{palette}:{role}:source_sha256_missing")
    return missing


def _promotion_decision(row: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    status = row.get("status")
    if status != "proof_row":
        _add_reason(reasons, "proof_bundle:hard_pile")
        for reason in row.get("reason_codes") or []:
            _add_reason(reasons, f"proof_bundle:{reason}")

    for gate_name in ("visual", "semantic", "proof"):
        gate = _gate_value(row, gate_name)
        if gate != "green":
            _add_reason(reasons, f"{gate_name}_gate:{gate or 'missing'}")
            for reason in (((row.get("gates") or {}).get(gate_name) or {}).get("reason_codes") or []):
                _add_reason(reasons, f"{gate_name}_gate:{reason}")

    runtime_gate = ((row.get("gates") or {}).get("runtime") or {})
    if runtime_gate.get("runtime_eligible") is not True:
        _add_reason(reasons, "runtime_gate:runtime_eligible_false")
    if runtime_gate.get("runtime_promotion_allowed") is not True:
        _add_reason(reasons, "runtime_gate:promotion_not_allowed")
    if runtime_gate.get("fail_closed") is not False:
        _add_reason(reasons, "runtime_gate:fail_closed")

    authority_status = ((row.get("gates") or {}).get("authority_status"))
    if authority_status != "authority_text_ready":
        _add_reason(reasons, f"authority_status:{authority_status or 'missing'}")

    review_status = ((row.get("gates") or {}).get("human_review_status"))
    if review_status != "approved":
        _add_reason(reasons, f"human_review_status:{review_status or 'missing'}")

    review_controls = row.get("review_controls") or {}
    if not review_controls:
        _add_reason(reasons, "review_controls:missing")
    if review_controls.get("runtime_approval_allowed") is True:
        _add_reason(reasons, "review_controls:ui_runtime_approval_forbidden")

    s101 = (row.get("standards") or {}).get("s101") or {}
    trace = _s101_trace(row)
    trace_class = trace.get("classification")
    if s101.get("present") is not True:
        _add_reason(reasons, "s101_trace:missing")
    if trace_class not in READY_S101_CLASSES:
        _add_reason(reasons, f"s101_trace:{trace_class or 'missing_classification'}")
    if trace.get("filename_only_match"):
        _add_reason(reasons, "s101_trace:filename_only_match_forbidden")
    if trace_class in READY_S101_CLASSES and trace.get("db_backed") is not True:
        _add_reason(reasons, "s101_trace:db_backing_missing")
    if trace_class in {"rule_derived", "catalogue_rule", "documented_deviation"}:
        if not trace.get("rule_file") and not trace.get("rule_instruction_refs"):
            _add_reason(reasons, "s101_rule:rule_evidence_missing")

    for reason in _render_trace_missing(row):
        _add_reason(reasons, reason)

    clean_room_boundary = (((row.get("display") or {}).get("helm_interpretation") or {}).get("clean_room_boundary"))
    if not clean_room_boundary:
        _add_reason(reasons, "clean_room:boundary_missing")

    reasons = sorted(set(reasons))
    return {
        "eligible": not reasons,
        "reason_codes": reasons,
        "remediation_hints": sorted(set(_reason_hint(reason) for reason in reasons)),
    }


def _runtime_row(row: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    trace = _s101_trace(row)
    return {
        "chart1_row_id": row["chart1_row_id"],
        "row_key": row["row_key"],
        "s52_lookup_id": row["s52_lookup_id"],
        "row_taxonomy": row["row_taxonomy"],
        "section": row.get("section"),
        "s52": (row.get("standards") or {}).get("s52") or {},
        "s57": (row.get("standards") or {}).get("s57") or {},
        "s101_trace": {
            "classification": trace.get("classification"),
            "mapping_type": trace.get("mapping_type"),
            "resolver_status": trace.get("resolver_status"),
            "feature_type": trace.get("feature_type"),
            "rule_file": trace.get("rule_file"),
            "attributes": trace.get("attributes") or {},
            "db_backed": trace.get("db_backed"),
            "filename_only_match": trace.get("filename_only_match"),
        },
        "render_trace": _media_source_hashes(row),
        "source_hashes": source,
        "clean_room_boundary": "OpenCPN is comparison evidence only; Helm runtime rows use generated-owned render outputs.",
    }


def _blocked_row(row: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    trace = _s101_trace(row)
    return {
        "chart1_row_id": row.get("chart1_row_id"),
        "row_key": row.get("row_key"),
        "s52_lookup_id": row.get("s52_lookup_id"),
        "row_taxonomy": row.get("row_taxonomy"),
        "section": row.get("section"),
        "status": row.get("status"),
        "gates": row.get("gates") or {},
        "s101_trace": {
            "classification": trace.get("classification"),
            "mapping_type": trace.get("mapping_type"),
            "resolver_status": trace.get("resolver_status"),
            "feature_type": trace.get("feature_type"),
            "rule_file": trace.get("rule_file"),
            "db_backed": trace.get("db_backed"),
            "filename_only_match": trace.get("filename_only_match"),
        },
        "source_hashes": _media_source_hashes(row),
        "reason_codes": decision["reason_codes"],
        "remediation_hints": decision["remediation_hints"],
    }


def _load_proof_bundle(proof_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], dict[str, str]]:
    manifest_path = proof_dir / "manifest.json"
    rows_path = proof_dir / "rows.json"
    hard_pile_path = proof_dir / "hard-pile.json"
    manifest = _load_json(manifest_path)
    rows_payload = _load_json(rows_path)
    hard_pile_payload = _load_json(hard_pile_path)
    rows = rows_payload.get("rows") or []
    hard_pile = hard_pile_payload.get("rows") or []
    coverage = manifest.get("coverage") or {}
    expected = coverage.get("authority_rows")
    if expected is not None and expected != len(rows) + len(hard_pile):
        raise ValueError(
            f"proof bundle row count mismatch: coverage authority_rows={expected}, "
            f"rows+hard_pile={len(rows) + len(hard_pile)}"
        )
    row_keys = [row.get("row_key") for row in rows + hard_pile]
    if len(row_keys) != len(set(row_keys)):
        raise ValueError("proof bundle contains duplicate row_key values")
    source_hashes = {
        "manifest": _sha256(manifest_path),
        "rows": _sha256(rows_path),
        "hard_pile": _sha256(hard_pile_path),
    }
    return manifest, rows, hard_pile, source_hashes


def _summary(
    *,
    manifest: dict[str, Any],
    promoted: list[dict[str, Any]],
    blocked: list[dict[str, Any]],
) -> dict[str, Any]:
    coverage = manifest.get("coverage") or {}
    reason_counts: Counter[str] = Counter()
    hint_counts: Counter[str] = Counter()
    for row in blocked:
        reason_counts.update(row["reason_codes"])
        hint_counts.update(row["remediation_hints"])
    return {
        "authority_rows": coverage.get("authority_rows"),
        "proof_rows": coverage.get("proof_rows"),
        "hard_pile_rows": coverage.get("hard_pile_rows"),
        "backend_runtime_eligible_rows": coverage.get("runtime_eligible_rows"),
        "backend_runtime_promotion_allowed_rows": coverage.get("runtime_promotion_allowed_rows"),
        "runtime_export_rows": len(promoted),
        "blocked_rows": len(blocked),
        "promotion_candidate_rows": len(promoted),
        "status": "fail_closed" if not promoted else "contains_runtime_rows",
        "reason_counts": dict(sorted(reason_counts.items())),
        "remediation_hint_counts": dict(sorted(hint_counts.items())),
    }


def build_promotion_gate(*, proof_dir: Path = DEFAULT_PROOF_DIR) -> dict[str, Any]:
    manifest, rows, hard_pile, proof_hashes = _load_proof_bundle(proof_dir)
    source = {
        "proof_bundle": {
            "path": _display_path(proof_dir),
            "schema": manifest.get("schema"),
            "sha256": proof_hashes["manifest"],
        },
        "proof_rows": {
            "path": _display_path(proof_dir / "rows.json"),
            "sha256": proof_hashes["rows"],
        },
        "proof_hard_pile": {
            "path": _display_path(proof_dir / "hard-pile.json"),
            "sha256": proof_hashes["hard_pile"],
        },
        "upstream_sources": manifest.get("source") or {},
    }
    runtime_rows: list[dict[str, Any]] = []
    blocked_rows: list[dict[str, Any]] = []
    source_hashes = {
        "proof_manifest_sha256": proof_hashes["manifest"],
        "proof_rows_sha256": proof_hashes["rows"],
        "proof_hard_pile_sha256": proof_hashes["hard_pile"],
    }
    for row in rows + hard_pile:
        decision = _promotion_decision(row)
        if decision["eligible"]:
            runtime_rows.append(_runtime_row(row, source_hashes))
        else:
            blocked_rows.append(_blocked_row(row, decision))

    summary = _summary(manifest=manifest, promoted=runtime_rows, blocked=blocked_rows)
    return {
        "schema": SCHEMA,
        "status": summary["status"],
        "policy": {
            "default_fail_closed": True,
            "ui_status_can_promote": False,
            "filename_only_s101_match_can_promote": False,
            "runtime_export_must_match_backend_state": True,
            "required_green_gates": ["visual", "semantic", "proof"],
            "required_runtime_gate": {
                "runtime_eligible": True,
                "runtime_promotion_allowed": True,
                "fail_closed": False,
            },
            "required_s101_classes": sorted(READY_S101_CLASSES),
            "required_review_status": "approved",
            "required_authority_status": "authority_text_ready",
            "required_render_trace": "source_path and source_sha256 for day/dusk/night render evidence",
            "clean_room_boundary": "OpenCPN comparison evidence and S-101 standards vocabulary do not become Helm source artwork.",
        },
        "source": source,
        "summary": summary,
        "runtime_export": {
            "schema": RUNTIME_EXPORT_SCHEMA,
            "status": summary["status"],
            "rows": runtime_rows,
            "source_hashes": source_hashes,
        },
        "blocked_rows": blocked_rows,
    }


def _markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Electronic Chart 1 Runtime Promotion Gate",
        "",
        "FORGE-47 fail-closed runtime/package eligibility contract.",
        "",
        f"- schema: `{payload['schema']}`",
        f"- status: `{payload['status']}`",
        f"- authority_rows: `{summary['authority_rows']}`",
        f"- proof_rows: `{summary['proof_rows']}`",
        f"- hard_pile_rows: `{summary['hard_pile_rows']}`",
        f"- runtime_export_rows: `{summary['runtime_export_rows']}`",
        f"- blocked_rows: `{summary['blocked_rows']}`",
        f"- backend_runtime_eligible_rows: `{summary['backend_runtime_eligible_rows']}`",
        f"- backend_runtime_promotion_allowed_rows: `{summary['backend_runtime_promotion_allowed_rows']}`",
        "",
        "## Policy",
        "",
        "- Runtime export defaults to fail-closed.",
        "- UI feedback/status cannot promote an icon.",
        "- Filename-only S-101 matches cannot promote an icon.",
        "- Promotion requires green visual, semantic, and proof gates.",
        "- Promotion requires authority text, DB-backed S-101 trace, render source hashes, clean-room provenance, and final QA approval.",
        "- OpenCPN remains comparison evidence only; Helm runtime output uses generated-owned render evidence.",
        "",
        "## Top Blockers",
        "",
        "| Reason | Count |",
        "| --- | ---: |",
    ]
    for reason, count in list(summary["reason_counts"].items())[:40]:
        lines.append(f"| `{reason}` | {count} |")
    lines.extend(["", "## Remediation Hints", "", "| Hint | Count |", "| --- | ---: |"])
    for hint, count in list(summary["remediation_hint_counts"].items())[:25]:
        lines.append(f"| {hint} | {count} |")
    return "\n".join(lines) + "\n"


def write_promotion_gate(
    *,
    proof_dir: Path = DEFAULT_PROOF_DIR,
    json_path: Path = DEFAULT_JSON,
    markdown_path: Path = DEFAULT_MD,
) -> dict[str, Any]:
    payload = build_promotion_gate(proof_dir=proof_dir)
    _write_json(json_path, payload)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(_markdown(payload))
    return {
        "status": "runtime_promotion_gate_written",
        "json": _display_path(json_path),
        "markdown": _display_path(markdown_path),
        "summary": payload["summary"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--proof-dir", type=Path, default=DEFAULT_PROOF_DIR)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MD)
    args = parser.parse_args(argv)
    result = write_promotion_gate(
        proof_dir=args.proof_dir,
        json_path=args.json,
        markdown_path=args.markdown,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
