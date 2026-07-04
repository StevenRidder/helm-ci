"""Build the clean-room symbol package manifest from DB-backed Forge evidence.

FORGE-16 is the package/manifest gate. It does not approve artwork and it does
not turn comparison references into source assets. The manifest records the
generated Helm assets/recipes that exist today and keeps missing or ambiguous
rows explicit for review and hard-pile handling.

Run:
  python3 -m forge.cleanroom_symbol_manifest
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from . import db_review_api, runtime_promotion_gate


ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = ROOT.parent.parent
REGISTRY_DIR = ROOT / "registry"
SYMBOLS_JSON = REGISTRY_DIR / "symbols.json"
SYMBOLS_YAML = REGISTRY_DIR / "symbols.yaml"
SCHEMA_JSON = REGISTRY_DIR / "symbol.schema.json"

SCHEMA = "helm.symbol.cleanroom-registry.v1"
MANIFEST_VERSION = "0.1.0"
RENDER_TARGETS = [
    "OpenCPN/Vulkan",
    "Helm C++",
    "iOS/native",
    "WebGPU",
    "SVG",
    "atlas PNG",
]


def _stable_text(value: Any) -> str:
    return str(value or "").strip()


def _short_label(*values: Any) -> str:
    for value in values:
        text = _stable_text(value)
        if text:
            return text[:64]
    return "Unnamed symbol"


def _kind(row: dict[str, Any]) -> str:
    geometry = _stable_text((row.get("s57") or {}).get("geometry")).lower()
    if geometry == "line":
        return "chart-line"
    if geometry == "area":
        return "chart-area-pattern"
    return "chart-symbol"


def _category(row: dict[str, Any]) -> str:
    object_class = _stable_text((row.get("s57") or {}).get("object_class"))
    if object_class:
        return object_class
    symbol_id = _stable_text(row.get("symbol_id"))
    if symbol_id:
        return re.sub(r"[^A-Za-z]+", "", symbol_id) or "unknown"
    return "unknown"


def _reason_index(runtime_payload: dict[str, Any]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for row in runtime_payload.get("hard_pile") or []:
        row_key = _stable_text(row.get("row_key"))
        if row_key:
            out[row_key] = [str(reason) for reason in row.get("reason_codes") or []]
    return out


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _repo_path(value: Any) -> Any:
    if not isinstance(value, str) or not value:
        return value
    path = Path(value)
    if not path.is_absolute():
        return value
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return value


def _portable_source(source: dict[str, Any]) -> dict[str, Any]:
    return {
        key: _repo_path(value)
        for key, value in source.items()
    }


def _visual_capable(row: dict[str, Any]) -> bool:
    helm = row.get("helm") or {}
    images = ((row.get("images") or {}).get("helm") or {})
    return bool(images.get("canonical_svg")) or bool(helm.get("recipe"))


def _qa_status(row: dict[str, Any], reason_codes: list[str]) -> str:
    qa = row.get("qa") or {}
    if qa.get("runtime_eligible") and not reason_codes:
        return "accepted"
    if qa.get("blocking_gate_count") or "helm_candidate_svg_missing" in (qa.get("missing_evidence") or []):
        return "blocked"
    return "needs_review"


def _semantic_status(row: dict[str, Any]) -> str:
    helm = row.get("helm") or {}
    s52 = row.get("s52") or {}
    if helm.get("interpretation_status") == "helm_interpretation_ready" and s52.get("ast_status") in {"parsed", "complete"}:
        return "accepted"
    if helm.get("interpretation_status") in {"missing", ""}:
        return "blocked"
    return "needs_review"


def _visual_status(row: dict[str, Any]) -> str:
    for gate in (row.get("qa") or {}).get("gates") or []:
        if gate.get("name") == "visual_approval":
            status = gate.get("status")
            if status == "pass":
                return "accepted"
            if status == "blocked":
                return "blocked"
            return "needs_review"
    return "needs_review"


def _source_refs(row: dict[str, Any]) -> dict[str, Any]:
    s57 = row.get("s57") or {}
    s52 = row.get("s52") or {}
    s101 = row.get("s101") or {}
    opencpn = row.get("opencpn") or {}
    return {
        "s57": {
            "object_class": s57.get("object_class"),
            "geometry": s57.get("geometry"),
            "attribute_tuple": s57.get("attribute_tuple") or {},
            "authority": "standards_vocabulary",
        },
        "s52": {
            "symbol_id": row.get("symbol_id"),
            "instruction": s52.get("instruction"),
            "ast_status": s52.get("ast_status"),
            "display_category": opencpn.get("display_category"),
            "display_priority": opencpn.get("display_priority"),
            "authority": "standards_vocabulary_and_local_lookup",
        },
        "s101": {
            "resolver_status": s101.get("resolver_status"),
            "mapping_type": s101.get("mapping_type"),
            "crosswalk_class": s101.get("crosswalk_class"),
            "feature_type": s101.get("feature_type"),
            "rule_file": s101.get("rule_file"),
            "direct_symbol_id": s101.get("direct_symbol_id"),
            "attributes": s101.get("attributes") or {},
            "unresolved_reasons": s101.get("unresolved_reasons") or [],
            "authority": "reference_evidence_only",
        },
        "opencpn": {
            "role": "comparison_target_only",
            "description": opencpn.get("description"),
            "instruction": opencpn.get("instruction"),
            "lookup_table": opencpn.get("lookup_table"),
        },
    }


def _symbol_record(row: dict[str, Any], reason_codes: list[str]) -> dict[str, Any]:
    symbol_id = _stable_text(row.get("symbol_id"))
    row_key = _stable_text(row.get("row_key"))
    description = _stable_text((row.get("opencpn") or {}).get("description"))
    images = ((row.get("images") or {}).get("helm") or {})
    helm = row.get("helm") or {}
    qa_status = _qa_status(row, reason_codes)
    return {
        "id": row_key,
        "symbol_id": symbol_id or None,
        "helm_catalog_id": row.get("helm_catalog_id"),
        "name": _short_label(description, symbol_id, row_key),
        "tier": "chart-artifact",
        "type": _kind(row),
        "category": _category(row),
        "aliases": [value for value in [symbol_id, row.get("helm_catalog_id")] if value],
        "source_refs": _source_refs(row),
        "assets": {
            "canonical_svg": images.get("canonical_svg"),
            "palette_resolved_svg": images.get("palette_resolved_svg") or {},
            "backend_url": images.get("backend_url"),
            "origin": (helm.get("candidate") or {}).get("origin") or "generated-owned-artwork",
        },
        "rendering": {
            "recipe_status": helm.get("recipe_status"),
            "recipe": helm.get("recipe") or {},
            "style_contract": (helm.get("candidate") or {}).get("style_contract"),
        },
        "accessibility": {
            "label": _short_label(description, symbol_id, row_key),
            "short_label": _short_label(symbol_id, (row.get("s57") or {}).get("object_class"), description),
            "spoken": _short_label(description, symbol_id, row_key),
        },
        "comparison_evidence": {
            "opencpn": ((row.get("images") or {}).get("opencpn") or {}),
            "s101": ((row.get("images") or {}).get("s101") or {}),
            "role": "comparison_and_rule_evidence_only_not_source_artwork",
        },
        "qa": {
            "status": qa_status,
            "semantic_review": _semantic_status(row),
            "visual_parity": _visual_status(row),
            "runtime_eligible": bool((row.get("qa") or {}).get("runtime_eligible")),
            "candidate_status": row.get("status"),
            "blocking_gate_count": (row.get("qa") or {}).get("blocking_gate_count", 0),
            "pending_gate_count": (row.get("qa") or {}).get("pending_gate_count", 0),
            "warning_gate_count": (row.get("qa") or {}).get("warning_gate_count", 0),
            "missing_evidence": (row.get("qa") or {}).get("missing_evidence") or [],
            "reason_codes": reason_codes,
            "gates": [
                {
                    "name": gate.get("name"),
                    "status": gate.get("status"),
                    "severity": gate.get("severity"),
                    "detail": gate.get("detail"),
                }
                for gate in (row.get("qa") or {}).get("gates") or []
            ],
        },
        "provenance": {
            "status": "generated_owned" if qa_status != "blocked" else "requires_review",
            "origin": "generated-owned-artwork-or-generated-recipe",
            "implementation": "Helm Icon Forge clean-room pipeline",
            "generated_from": [
                "artifacts/opencpn_s52_portrayal.sqlite",
                "pipeline/iconforge/catalog/semantic_evidence_db.json",
                "pipeline/iconforge/proof/manifest.json",
            ],
            "comparison_evidence": [
                "OpenCPN/S-52 render output is comparison target only",
                "S-57/S-52/S-101 names and attributes are standards vocabulary/evidence",
                "S-101 symbol/rule references are not bundled as owned artwork",
                "Chart No.1 evidence is public reference/proof where present",
            ],
            "source_boundary": {
                "generated_outputs_are_source": True,
                "third_party_artwork_is_source": False,
                "runtime_publish_gate": "blocked_until_runtime_promotion_gate_and_human_approval_pass",
            },
        },
    }


def _blocked_candidate(row: dict[str, Any], reason_codes: list[str]) -> dict[str, Any]:
    qa = row.get("qa") or {}
    return {
        "id": row.get("row_key"),
        "symbol_id": row.get("symbol_id") or None,
        "helm_catalog_id": row.get("helm_catalog_id"),
        "object_class": (row.get("s57") or {}).get("object_class"),
        "geometry": (row.get("s57") or {}).get("geometry"),
        "candidate_status": row.get("status"),
        "missing_evidence": qa.get("missing_evidence") or [],
        "reason_codes": reason_codes or ["generated_visual_asset_or_recipe_missing"],
        "disposition": "not_in_symbols_until_generated_svg_or_recipe_exists",
    }


def _schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://helm.local/iconforge/cleanroom-symbol-registry.schema.json",
        "title": "Helm Icon Forge Clean-room Symbol Registry",
        "type": "object",
        "required": ["schema", "manifest_version", "standards_profile", "render_targets", "symbols"],
        "properties": {
            "schema": {"const": SCHEMA},
            "manifest_version": {"type": "string"},
            "standards_profile": {"type": "object"},
            "render_targets": {
                "type": "array",
                "items": {"type": "string"},
                "contains": {"const": "OpenCPN/Vulkan"},
            },
            "symbols": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id", "name", "assets", "accessibility", "qa", "provenance"],
                    "properties": {
                        "id": {"type": "string", "minLength": 1},
                        "symbol_id": {"type": ["string", "null"]},
                        "name": {"type": "string", "minLength": 1},
                        "assets": {
                            "type": "object",
                            "required": ["canonical_svg"],
                            "properties": {
                                "canonical_svg": {"type": "string", "minLength": 1},
                                "palette_resolved_svg": {"type": "object"},
                            },
                        },
                        "qa": {
                            "type": "object",
                            "required": ["status", "semantic_review", "visual_parity", "runtime_eligible"],
                        },
                        "provenance": {
                            "type": "object",
                            "required": ["origin", "implementation", "generated_from", "comparison_evidence"],
                        },
                    },
                },
            },
        },
    }


def _yaml_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def _to_yaml(value: Any, indent: int = 0) -> str:
    pad = " " * indent
    if isinstance(value, dict):
        lines: list[str] = []
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}{key}:")
                lines.append(_to_yaml(item, indent + 2))
            else:
                lines.append(f"{pad}{key}: {_yaml_scalar(item)}")
        return "\n".join(lines)
    if isinstance(value, list):
        if not value:
            return f"{pad}[]"
        lines = []
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}-")
                lines.append(_to_yaml(item, indent + 2))
            else:
                lines.append(f"{pad}- {_yaml_scalar(item)}")
        return "\n".join(lines)
    return f"{pad}{_yaml_scalar(value)}"


def validate_manifest(payload: dict[str, Any]) -> None:
    required_targets = set(RENDER_TARGETS)
    actual_targets = set(payload.get("render_targets") or [])
    missing_targets = sorted(required_targets - actual_targets)
    if missing_targets:
        raise ValueError(f"manifest missing render targets: {missing_targets}")
    ids = [row.get("id") for row in payload.get("symbols") or []]
    if len(ids) != len(set(ids)):
        raise ValueError("manifest contains duplicate symbol ids")
    for row in payload.get("symbols") or []:
        canonical = ((row.get("assets") or {}).get("canonical_svg"))
        recipe = ((row.get("rendering") or {}).get("recipe"))
        if not canonical and not recipe:
            raise ValueError(f"symbol {row.get('id')} lacks generated SVG and recipe")
        if (row.get("provenance") or {}).get("source_boundary", {}).get("third_party_artwork_is_source") is not False:
            raise ValueError(f"symbol {row.get('id')} has unsafe source boundary")
        if (row.get("qa") or {}).get("runtime_eligible") and (row.get("qa") or {}).get("status") != "accepted":
            raise ValueError(f"runtime eligible symbol {row.get('id')} is not accepted")


def build_manifest(*, limit: int = 10000) -> dict[str, Any]:
    review = db_review_api.build_review_payload(limit=limit)
    runtime = runtime_promotion_gate.build_runtime_export(limit=limit)
    reasons = _reason_index(runtime)
    symbols = []
    blocked = []
    for row in review["rows"]:
        row_reasons = reasons.get(_stable_text(row.get("row_key")), [])
        if _visual_capable(row):
            symbols.append(_symbol_record(row, row_reasons))
        else:
            blocked.append(_blocked_candidate(row, row_reasons))

    status_counts = Counter((row.get("qa") or {}).get("status") for row in symbols)
    semantic_counts = Counter((row.get("qa") or {}).get("semantic_review") for row in symbols)
    visual_counts = Counter((row.get("qa") or {}).get("visual_parity") for row in symbols)
    payload = {
        "schema": SCHEMA,
        "manifest_version": MANIFEST_VERSION,
        "status": "provisional_review_package",
        "specification": {
            "label": "SPEC 0001: Clean-room Maritime Symbol Package",
            "role": "package/profile contract",
        },
        "standards_profile": {
            "implementation_goal": "clean-room generated maritime symbol package for Helm/OpenCPN-compatible renderers",
            "source_standards": ["S-52", "S-57", "S-101", "OpenCPN comparison output", "Chart No.1 public reference"],
            "conformance_note": (
                "This is implementation evidence and generated artwork, not official ECDIS certification "
                "and not a redistribution of IHO/OpenCPN source artwork."
            ),
        },
        "render_targets": RENDER_TARGETS,
        "source": _portable_source(review["source"]),
        "source_boundary": {
            "generated_outputs": "Helm Icon Forge SVG assets and normalized render recipes",
            "comparison_references": "OpenCPN/IHO/Chart No.1 are comparison, vocabulary, or rule evidence only",
            "forbidden_source_assets": [
                "OpenCPN GPL raster sprites as owned artwork",
                "IHO S-101 official SVG/Lua/catalogue files as bundled owned artwork",
                "private ENC/S-63/oeSENC data",
            ],
            "publish_gate": "runtime/package default export remains fail-closed until runtime promotion and human approval pass",
        },
        "summary": {
            "db_candidates": review["summary"]["total_candidates"],
            "symbols": len(symbols),
            "blocked_non_symbol_candidates": len(blocked),
            "runtime_rows": runtime["summary"]["runtime_rows"],
            "hard_pile_rows": runtime["summary"]["hard_pile_rows"],
            "qa_status_counts": dict(sorted(status_counts.items())),
            "semantic_review_counts": dict(sorted(semantic_counts.items())),
            "visual_parity_counts": dict(sorted(visual_counts.items())),
        },
        "symbols": symbols,
        "blocked_candidates": blocked,
    }
    validate_manifest(payload)
    return payload


def write_manifest(
    *,
    json_path: Path = SYMBOLS_JSON,
    yaml_path: Path = SYMBOLS_YAML,
    schema_path: Path = SCHEMA_JSON,
) -> dict[str, Any]:
    payload = build_manifest()
    json_path.parent.mkdir(parents=True, exist_ok=True)
    compact = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
    json_path.write_text(compact)
    # JSON is valid YAML 1.2. Keep the committed generated mirror compact so
    # PRs do not become million-line generated diffs.
    yaml_path.write_text(compact)
    schema_path.write_text(json.dumps(_schema(), indent=2, sort_keys=True) + "\n")
    return {
        "status": "cleanroom_symbol_manifest_written",
        "json": _display_path(json_path),
        "yaml": _display_path(yaml_path),
        "schema": _display_path(schema_path),
        "summary": payload["summary"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path, default=SYMBOLS_JSON)
    parser.add_argument("--yaml", type=Path, default=SYMBOLS_YAML)
    parser.add_argument("--schema", type=Path, default=SCHEMA_JSON)
    args = parser.parse_args(argv)
    result = write_manifest(json_path=args.json, yaml_path=args.yaml, schema_path=args.schema)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
