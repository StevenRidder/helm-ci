#!/usr/bin/env python3
"""Audit OpenCPN S-52 symbol resources not represented as public Helm IDs."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INVENTORY = ROOT / "pipeline" / "iconforge" / "public" / "proof" / "s52-portrayal-inventory.json"
DEFAULT_SITE_INDEX = ROOT / "pipeline" / "iconforge" / "public" / "proof" / "site-index.json"
DEFAULT_JSON = ROOT / "pipeline" / "iconforge" / "public" / "proof" / "s52-public-symbol-gap-audit.json"
DEFAULT_MD = ROOT / "pipeline" / "iconforge" / "public" / "proof" / "s52-public-symbol-gap-audit.txt"


def normalized(value: str | None) -> str:
    return re.sub(r"[^A-Z0-9]", "", (value or "").upper())


def prefix(value: str) -> str:
    match = re.match(r"^[A-Z]+", value)
    return match.group(0) if match else value


def load_json(path: Path) -> dict:
    with path.open() as handle:
        return json.load(handle)


def representative_symbol_resources(inventory: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for resource in inventory.get("resources", []):
        if resource.get("resource_type") != "symbol":
            continue
        key = normalized(resource.get("normalized_name") or resource.get("name"))
        if not key:
            continue
        current = out.get(key)
        if current is None or resource.get("referenced_by_lookup_count", 0) > current.get("referenced_by_lookup_count", 0):
            out[key] = resource
    return out


def public_symbols(site_index: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for symbol in site_index.get("symbols", []):
        key = normalized(symbol.get("id"))
        if key:
            out[key] = symbol
    return out


def action_bucket(resource: dict) -> str:
    resource_class = resource.get("resource_class")
    referenced = resource.get("referenced_by_lookup_count", 0) > 0
    if resource_class == "sounding_text":
        return "text_sounding_rule"
    if resource_class == "component_internal_symbol" and referenced:
        return "render_as_component_asset"
    if resource_class == "component_internal_symbol":
        return "component_or_conditional_usage_audit"
    if resource_class == "point_symbol":
        return "render_as_public_icon"
    return "manual_classification_required"


def compact_resource(resource: dict) -> dict:
    return {
        "name": resource.get("name"),
        "description": resource.get("description"),
        "resource_class": resource.get("resource_class"),
        "referenced_by_lookup_count": resource.get("referenced_by_lookup_count"),
        "action": action_bucket(resource),
        "helm_public_status": resource.get("helm_public_status"),
        "s101_candidate_status": resource.get("s101_candidate_status"),
        "classification_reasons": resource.get("classification_reasons", []),
    }


def build_audit(inventory: dict, site_index: dict) -> dict:
    resources = representative_symbol_resources(inventory)
    public = public_symbols(site_index)
    opencpn_names = set(resources)
    public_names = set(public)
    shared = sorted(opencpn_names & public_names)
    opencpn_only_names = sorted(opencpn_names - public_names)
    public_only_names = sorted(public_names - opencpn_names)
    opencpn_only = [resources[name] for name in opencpn_only_names]

    action_counts = Counter(action_bucket(resource) for resource in opencpn_only)
    class_counts = Counter(resource.get("resource_class") for resource in opencpn_only)
    class_reference_counts = Counter(
        (
            resource.get("resource_class"),
            "referenced" if resource.get("referenced_by_lookup_count", 0) > 0 else "unreferenced",
        )
        for resource in opencpn_only
    )
    prefix_counts_by_action: dict[str, dict[str, int]] = {}
    for action in sorted(action_counts):
        prefix_counts_by_action[action] = dict(
            Counter(prefix(resource.get("name") or "") for resource in opencpn_only if action_bucket(resource) == action).most_common()
        )

    return {
        "schema": "helm.forge.s52_public_symbol_gap_audit.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "inventory": "proof/s52-portrayal-inventory.json",
            "site_index": "proof/site-index.json",
            "opencpn_source": inventory.get("source", {}),
        },
        "set_math": {
            "opencpn_distinct_symbol_resource_names": len(opencpn_names),
            "helm_public_distinct_symbol_ids": len(public_names),
            "shared_names": len(shared),
            "opencpn_only_names": len(opencpn_only_names),
            "helm_public_only_names": len(public_only_names),
            "net_count_delta": len(opencpn_names) - len(public_names),
            "interpretation": (
                "The net delta is not a missing-icon count. It equals OpenCPN-only names minus "
                "Helm-public-only names; use action_counts for render work."
            ),
        },
        "action_counts": dict(sorted(action_counts.items())),
        "resource_class_counts": dict(sorted(class_counts.items())),
        "resource_class_reference_counts": {f"{cls}:{ref}": count for (cls, ref), count in sorted(class_reference_counts.items())},
        "render_conclusion": {
            "normal_point_symbols_missing": action_counts.get("render_as_public_icon", 0),
            "component_assets_to_render_first": action_counts.get("render_as_component_asset", 0),
            "text_or_sounding_rules_to_model_not_render_as_icons": action_counts.get("text_sounding_rule", 0),
            "component_or_conditional_resources_to_audit_before_rendering": action_counts.get("component_or_conditional_usage_audit", 0),
        },
        "prefix_counts_by_action": prefix_counts_by_action,
        "opencpn_only": [compact_resource(resource) for resource in opencpn_only],
        "helm_public_only": [
            {
                "id": public[name].get("id"),
                "name": public[name].get("name"),
                "family": public[name].get("family"),
                "category": public[name].get("category"),
                "object_class": public[name].get("object_class"),
            }
            for name in public_only_names
        ],
    }


def write_markdown(audit: dict, path: Path) -> None:
    render = audit["render_conclusion"]
    lines = [
        "# S-52 Public Symbol Gap Audit",
        "",
        "This audit explains the apparent gap between OpenCPN S-52 symbol resource names and Helm public symbol IDs.",
        "",
        "## Set Math",
        "",
        f"- OpenCPN distinct symbol resource names: `{audit['set_math']['opencpn_distinct_symbol_resource_names']}`",
        f"- Helm public distinct symbol IDs: `{audit['set_math']['helm_public_distinct_symbol_ids']}`",
        f"- Shared names: `{audit['set_math']['shared_names']}`",
        f"- OpenCPN-only names: `{audit['set_math']['opencpn_only_names']}`",
        f"- Helm-public-only names: `{audit['set_math']['helm_public_only_names']}`",
        f"- Net count delta: `{audit['set_math']['net_count_delta']}`",
        "",
        "The net delta is not a missing-icon count. It is OpenCPN-only names minus Helm-public-only names.",
        "",
        "## Render Conclusion",
        "",
        f"- Normal point symbols missing from the public package: `{render['normal_point_symbols_missing']}`",
        f"- Component assets to render first: `{render['component_assets_to_render_first']}`",
        f"- Text/sounding rules to model instead of icon-render: `{render['text_or_sounding_rules_to_model_not_render_as_icons']}`",
        f"- Component/conditional resources to audit before rendering: `{render['component_or_conditional_resources_to_audit_before_rendering']}`",
        "",
        "## Action Counts",
        "",
    ]
    for action, count in audit["action_counts"].items():
        lines.append(f"- `{action}`: `{count}`")
    lines.extend(["", "## Component Assets To Render First", ""])
    for resource in audit["opencpn_only"]:
        if resource["action"] == "render_as_component_asset":
            lines.append(
                f"- `{resource['name']}`: {resource.get('description') or ''} "
                f"(referenced by `{resource['referenced_by_lookup_count']}` lookup rows)"
            )
    lines.extend(["", "## Top Prefixes By Action", ""])
    for action, counts in audit["prefix_counts_by_action"].items():
        top = ", ".join(f"{name}={count}" for name, count in list(counts.items())[:12])
        lines.append(f"- `{action}`: {top}")
    lines.append("")
    path.write_text("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--site-index", type=Path, default=DEFAULT_SITE_INDEX)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    audit = build_audit(load_json(args.inventory), load_json(args.site_index))
    args.json_output.write_text(json.dumps(audit, sort_keys=True, separators=(",", ":")) + "\n")
    write_markdown(audit, args.markdown_output)
    print(json.dumps({"set_math": audit["set_math"], "render_conclusion": audit["render_conclusion"]}, indent=2))


if __name__ == "__main__":
    main()
