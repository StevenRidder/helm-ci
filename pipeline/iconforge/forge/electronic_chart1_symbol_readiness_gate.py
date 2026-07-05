"""Build the CHART-10 end-to-end symbol readiness release gate.

This report aggregates the existing FORGE/CHART/ADAPTER evidence into one
release decision. It is intentionally conservative: passing support checks do
not imply chartplotter readiness while human approval, visual parity, hard-pile,
or runtime export gates remain blocked.

Run:
  python3 -m forge.electronic_chart1_symbol_readiness_gate
  python3 -m forge.tests.test_electronic_chart1_symbol_readiness_gate
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = ROOT.parent.parent
CATALOG = ROOT / "catalog"
PROOF = ROOT / "proof"

S101_AUDIT_JSON = CATALOG / "s101_mapping_audit.json"
RUNTIME_DB_JSON = CATALOG / "runtime_db_contract.json"
RUNTIME_EVIDENCE_JSON = CATALOG / "runtime_evidence_snapshot.json"
RUNTIME_GATE_JSON = CATALOG / "electronic_chart1_runtime_promotion_gate.json"
BASELINE_JSON = CATALOG / "electronic_chart1_opencpn_baseline.json"
PROOF_MANIFEST_JSON = PROOF / "manifest.json"
PROOF_DATA_JSON = PROOF / "package-proof-data.json"
REGISTRY_JSON = ROOT / "registry" / "symbols.json"
FIXTURES_JSON = REPO_ROOT / "engine" / "test" / "fixtures" / "symbol-selection" / "fixtures.json"
VULKAN_FIXTURE_MANIFEST = REPO_ROOT / "engine" / "test" / "fixtures" / "vulkan-render" / "symbol-selection" / "manifest.json"

DEFAULT_JSON = CATALOG / "electronic_chart1_symbol_readiness_gate.json"
DEFAULT_MD = CATALOG / "electronic_chart1_symbol_readiness_gate.md"

SCHEMA = "helm.forge.electronic_chart1_symbol_readiness_gate.v1"
PALETTES = ("day", "dusk", "night")


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_canonical_json(payload))


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _repo_path(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _source(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": _repo_path(path),
        "schema": payload.get("schema"),
        "status": payload.get("status"),
        "sha256": _sha256(path),
    }


def _status(pass_condition: bool) -> str:
    return "pass" if pass_condition else "blocked"


def _gate(name: str, status: str, summary: dict[str, Any], evidence: list[str], blockers: list[str] | None = None) -> dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "summary": summary,
        "evidence": evidence,
        "blockers": blockers or [],
    }


def _proof_data_counts(proof_data: dict[str, Any]) -> dict[str, Any]:
    rows = proof_data.get("rows") or []
    status_counts = Counter(row.get("status") for row in rows)
    final_approved = 0
    runtime_eligible = 0
    runtime_promotion_allowed = 0
    human_status = Counter()
    for row in rows:
        runtime = row.get("runtime") or {}
        gates = row.get("gates") or {}
        if ((row.get("human_approval") or {}).get("final_approved") is True
                or ((row.get("qa") or {}).get("final_approved") is True)):
            final_approved += 1
        if runtime.get("eligible") is True:
            runtime_eligible += 1
        if runtime.get("promotion_allowed") is True:
            runtime_promotion_allowed += 1
        human_status[gates.get("human_review_status") or "needs_human_review"] += 1
    return {
        "rows": len(rows),
        "status_counts": dict(sorted((str(k), v) for k, v in status_counts.items())),
        "final_approved_rows": final_approved,
        "runtime_eligible_rows": runtime_eligible,
        "runtime_promotion_allowed_rows": runtime_promotion_allowed,
        "human_review_status_counts": dict(sorted(human_status.items())),
    }


def _fixture_summary(fixtures: dict[str, Any]) -> dict[str, Any]:
    rows = fixtures.get("fixtures") or []
    return {
        "fixtures": len(rows),
        "coverage_classes": sorted({row.get("coverage_class") for row in rows}),
        "palette_tokens": fixtures.get("palette_tokens") or [],
        "all_default_render_blocked": all(((row.get("expected") or {}).get("default_render_allowed") is False) for row in rows),
    }


def _vulkan_fixture_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    expected_images = manifest.get("expected_images") or []
    capture_matrix = manifest.get("capture_matrix") or []
    return {
        "fixture_id": manifest.get("fixture_id"),
        "palette_images": sorted({item.get("palette") for item in expected_images if item.get("palette")}),
        "capture_palettes": sorted({item.get("palette") for item in capture_matrix if item.get("palette")}),
        "expected_hashes_present": bool(manifest.get("expected_hashes")),
        "semantic_assertions": manifest.get("semantic_assertions") or [],
    }


def _top_counts(counts: dict[str, int], limit: int = 12) -> dict[str, int]:
    return dict(Counter(counts).most_common(limit))


def _validation_commands() -> list[dict[str, str]]:
    return [
        {
            "name": "mapping audit",
            "command": "PYTHONPATH=pipeline/iconforge python3 -m forge.tests.test_s101_mapping_audit",
        },
        {
            "name": "runtime DB contract",
            "command": "PYTHONPATH=pipeline/iconforge python3 -m forge.tests.test_runtime_db_contract",
        },
        {
            "name": "C++ loader validates package",
            "command": "engine/test-symbol-package-loader.sh",
        },
        {
            "name": "attribute fixture suite",
            "command": "engine/test-symbol-selection-fixtures.sh",
        },
        {
            "name": "runtime eligibility gate",
            "command": "engine/test-symbol-runtime-gate.sh",
        },
        {
            "name": "Vulkan/VSG day-dusk-night fixture smoke",
            "command": "engine/test-vulkan-symbol-selection-render.sh",
        },
        {
            "name": "OpenCPN baseline comparison report",
            "command": "PYTHONPATH=pipeline/iconforge python3 -m forge.tests.test_electronic_chart1_opencpn_baseline",
        },
        {
            "name": "OpenCPN-native/Helm offscreen handoff",
            "command": "engine/test-symbol-render-handoff.sh",
        },
    ]


def build_gate(
    *,
    s101_path: Path = S101_AUDIT_JSON,
    runtime_db_path: Path = RUNTIME_DB_JSON,
    runtime_evidence_path: Path = RUNTIME_EVIDENCE_JSON,
    runtime_gate_path: Path = RUNTIME_GATE_JSON,
    baseline_path: Path = BASELINE_JSON,
    proof_manifest_path: Path = PROOF_MANIFEST_JSON,
    proof_data_path: Path = PROOF_DATA_JSON,
    registry_path: Path = REGISTRY_JSON,
    fixtures_path: Path = FIXTURES_JSON,
    vulkan_fixture_path: Path = VULKAN_FIXTURE_MANIFEST,
) -> dict[str, Any]:
    s101 = _load_json(s101_path)
    runtime_db = _load_json(runtime_db_path)
    runtime_evidence = _load_json(runtime_evidence_path)
    runtime_gate = _load_json(runtime_gate_path)
    baseline = _load_json(baseline_path)
    proof_manifest = _load_json(proof_manifest_path)
    proof_data = _load_json(proof_data_path)
    registry = _load_json(registry_path)
    fixtures = _load_json(fixtures_path)
    vulkan_fixture = _load_json(vulkan_fixture_path)

    proof_counts = _proof_data_counts(proof_data)
    fixture_counts = _fixture_summary(fixtures)
    vulkan_counts = _vulkan_fixture_summary(vulkan_fixture)
    s101_coverage = s101["coverage"]
    runtime_summary = runtime_gate["summary"]
    proof_coverage = proof_manifest["coverage"]
    baseline_summary = baseline["summary"]
    registry_summary = registry["summary"]
    runtime_db_summary = runtime_db["summary"]
    runtime_evidence_summary = runtime_evidence["summary"]

    checks = [
        _gate(
            "mapping_audit",
            _status(s101.get("status") == "pass" and s101_coverage.get("all_rows_classified") and s101_coverage.get("unresolved") == 0),
            {
                "scoped_rows": s101_coverage["rows"],
                "all_rows_classified": s101_coverage["all_rows_classified"],
                "unresolved_rows": s101_coverage["unresolved"],
                "non_s101_or_extension_rows": s101_coverage["non_s101_or_extension"],
                "s101_feature_equivalent_rows": s101_coverage["s101_feature_equivalent"],
            },
            [_repo_path(s101_path)],
        ),
        _gate(
            "proof_gallery_and_human_signoff",
            _status(proof_counts["final_approved_rows"] > 0 and runtime_summary["runtime_export_rows"] > 0),
            {
                "proof_rows": proof_coverage["status_counts"].get("proof_row", 0),
                "hard_pile_rows": proof_coverage["status_counts"].get("proof_hard_pile", 0),
                "registry_semantic_accepted_rows": registry_summary["semantic_review_counts"].get("accepted", 0),
                "final_approved_rows": proof_counts["final_approved_rows"],
                "human_review_status_counts": proof_counts["human_review_status_counts"],
            },
            [_repo_path(proof_manifest_path), _repo_path(proof_data_path), "pipeline/iconforge/proof/compare-opencpn.html"],
            ["human_review_pending", "final_approved_rows_zero", "runtime_export_rows_zero"],
        ),
        _gate(
            "cxx_loader_validates_package",
            _status(
                runtime_db.get("status") == "contract_pass"
                and runtime_evidence_summary.get("matches_runtime_promotion_gate") is True
                and (REPO_ROOT / "engine/test-symbol-package-loader.sh").exists()
            ),
            {
                "runtime_db_status": runtime_db.get("status"),
                "candidate_rows": runtime_db_summary["candidate_rows"],
                "runtime_eligible_rows": runtime_db_summary["runtime_eligible_rows"],
                "matches_runtime_promotion_gate": runtime_evidence_summary["matches_runtime_promotion_gate"],
            },
            [_repo_path(runtime_db_path), _repo_path(runtime_evidence_path), "engine/test-symbol-package-loader.sh"],
        ),
        _gate(
            "attribute_fixture_suite",
            _status(
                fixture_counts["fixtures"] >= 7
                and set(PALETTES) == set(fixture_counts["palette_tokens"])
                and fixture_counts["all_default_render_blocked"]
            ),
            fixture_counts,
            [_repo_path(fixtures_path), "engine/test-symbol-selection-fixtures.sh"],
        ),
        _gate(
            "vulkan_day_dusk_night_smoke",
            _status(set(PALETTES) == set(vulkan_counts["palette_images"]) and vulkan_counts["expected_hashes_present"]),
            vulkan_counts,
            [_repo_path(vulkan_fixture_path), "engine/test-vulkan-symbol-selection-render.sh"],
        ),
        _gate(
            "opencpn_baseline_comparison",
            _status(baseline.get("status") == "opencpn_baseline_comparison_ready"),
            {
                "rows": baseline_summary["rows"],
                "status_counts": baseline_summary["status_counts"],
                "rows_with_all_opencpn_palette_refs": baseline_summary["rows_with_all_opencpn_palette_refs"],
                "runtime_promotion_allowed_rows": baseline_summary["runtime_promotion_allowed_rows"],
            },
            [_repo_path(baseline_path)],
        ),
        _gate(
            "runtime_eligibility_gate",
            _status(runtime_summary["runtime_export_rows"] == 0 and runtime_summary["blocked_rows"] == runtime_summary["authority_rows"]),
            {
                "authority_rows": runtime_summary["authority_rows"],
                "runtime_export_rows": runtime_summary["runtime_export_rows"],
                "blocked_rows": runtime_summary["blocked_rows"],
                "backend_runtime_eligible_rows": runtime_summary["backend_runtime_eligible_rows"],
            },
            [_repo_path(runtime_gate_path), "engine/test-symbol-runtime-gate.sh"],
        ),
        _gate(
            "adapter_handoff",
            _status(
                (REPO_ROOT / "engine/vendor/cli/helm_symbol_render_handoff.cpp").exists()
                and (REPO_ROOT / "engine/vendor/cli/helm_symbol_render_handoff_smoke.cpp").exists()
            ),
            {
                "schema": "helm.symbol.render_handoff.v1",
                "consumers": ["opencpn_native", "helm_offscreen"],
                "default_render_stays_fail_closed": True,
            },
            [
                "engine/vendor/cli/helm_symbol_render_handoff.cpp",
                "engine/vendor/cli/helm_symbol_render_handoff_smoke.cpp",
                "engine/test-symbol-render-handoff.sh",
                "docs/VULKAN-RENDER-ADAPTERS.md",
            ],
        ),
    ]

    blocked_checks = [check["name"] for check in checks if check["status"] != "pass"]
    release_ready = not blocked_checks and runtime_summary["runtime_export_rows"] > 0
    remaining_blockers = {
        "gate_blockers": proof_coverage.get("gate_blockers") or [],
        "runtime_reason_counts": _top_counts(runtime_summary["reason_counts"]),
        "runtime_remediation_hint_counts": _top_counts(runtime_summary["remediation_hint_counts"], limit=10),
        "runtime_db_blocker_gate_counts": runtime_db_summary["blocker_gate_counts"],
    }
    return {
        "schema": SCHEMA,
        "status": "release_ready" if release_ready else "release_blocked",
        "release_ready": release_ready,
        "decision": {
            "may_mark_all_symbols_ready": False,
            "reason": (
                "Runtime export remains zero and human/visual/runtime gates are blocked; "
                "CHART-10 records the current fail-closed release state."
            ),
        },
        "source": {
            "s101_mapping_audit": _source(s101_path, s101),
            "runtime_db_contract": _source(runtime_db_path, runtime_db),
            "runtime_evidence_snapshot": _source(runtime_evidence_path, runtime_evidence),
            "runtime_promotion_gate": _source(runtime_gate_path, runtime_gate),
            "opencpn_baseline": _source(baseline_path, baseline),
            "proof_manifest": _source(proof_manifest_path, proof_manifest),
            "proof_data": _source(proof_data_path, proof_data),
            "registry": _source(registry_path, registry),
            "symbol_selection_fixtures": _source(fixtures_path, fixtures),
            "vulkan_fixture_manifest": _source(vulkan_fixture_path, vulkan_fixture),
        },
        "summary": {
            "release_status": "release_ready" if release_ready else "release_blocked",
            "total_release_rows": proof_coverage["total_rows"],
            "registry_symbols": proof_coverage["registry_symbols"],
            "registry_semantic_accepted_rows": registry_summary["semantic_review_counts"].get("accepted", 0),
            "final_approved_rows": proof_counts["final_approved_rows"],
            "runtime_export_rows": runtime_summary["runtime_export_rows"],
            "runtime_blocked_rows": runtime_summary["blocked_rows"],
            "hard_pile_rows": proof_coverage["status_counts"].get("proof_hard_pile", 0),
            "unsupported_extension_profile_rows": proof_coverage["s101_classification_counts"].get("non_s101_or_extension_profile", 0),
            "scoped_mapping_rows": s101_coverage["rows"],
            "scoped_mapping_unresolved_rows": s101_coverage["unresolved"],
            "checks_passed": sum(1 for check in checks if check["status"] == "pass"),
            "checks_blocked": len(blocked_checks),
            "blocked_checks": blocked_checks,
        },
        "checks": checks,
        "remaining_blockers": remaining_blockers,
        "validation_commands": _validation_commands(),
    }


def _markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Electronic Chart 1 Symbol Readiness Gate",
        "",
        "CHART-10 release/verifier gate for Forge symbols in chartplotter render paths.",
        "",
        f"- schema: `{payload['schema']}`",
        f"- status: `{payload['status']}`",
        f"- release_ready: `{str(payload['release_ready']).lower()}`",
        f"- total_release_rows: `{summary['total_release_rows']}`",
        f"- registry_symbols: `{summary['registry_symbols']}`",
        f"- registry_semantic_accepted_rows: `{summary['registry_semantic_accepted_rows']}`",
        f"- final_approved_rows: `{summary['final_approved_rows']}`",
        f"- runtime_export_rows: `{summary['runtime_export_rows']}`",
        f"- hard_pile_rows: `{summary['hard_pile_rows']}`",
        f"- unsupported_extension_profile_rows: `{summary['unsupported_extension_profile_rows']}`",
        "",
        "## Decision",
        "",
        payload["decision"]["reason"],
        "",
        "## Checks",
        "",
        "| Check | Status | Evidence |",
        "| --- | --- | --- |",
    ]
    for check in payload["checks"]:
        evidence = "<br>".join(f"`{item}`" for item in check["evidence"])
        lines.append(f"| `{check['name']}` | `{check['status']}` | {evidence} |")
    lines.extend(["", "## Remaining Blockers", "", "| Reason | Count |", "| --- | ---: |"])
    for reason, count in payload["remaining_blockers"]["runtime_reason_counts"].items():
        lines.append(f"| `{reason}` | {count} |")
    lines.extend(["", "## Validation Commands", ""])
    for item in payload["validation_commands"]:
        lines.append(f"- `{item['command']}`")
    return "\n".join(lines) + "\n"


def write_gate(
    *,
    json_path: Path = DEFAULT_JSON,
    markdown_path: Path = DEFAULT_MD,
) -> dict[str, Any]:
    payload = build_gate()
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
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MD)
    args = parser.parse_args(argv)
    print(json.dumps(write_gate(json_path=args.json, markdown_path=args.markdown), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
