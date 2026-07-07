#!/usr/bin/env python3
"""Build the full OpenCPN S-52 portrayal proof inventory.

FORGE-5 corrects the public proof package's center of gravity: OpenCPN
`chartsymbols.xml` is the inventory source of truth, and the Helm icon package
is attached to that inventory as one candidate column.  This script is
deliberately DB-first so the static public page and later runtime work read the
same canonical facts.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "artifacts" / "opencpn_s52_portrayal.sqlite"
DEFAULT_SITE_INDEX = ROOT / "pipeline" / "iconforge" / "public" / "proof" / "site-index.json"
DEFAULT_OUT = ROOT / "pipeline" / "iconforge" / "public" / "proof" / "s52-portrayal-inventory.json"
OPENCPN_REPO = "https://github.com/OpenCPN/OpenCPN.git"

SCHEMA = "helm.forge.s52_portrayal_inventory.v1"
LOOKUP_TABLE = "s52_proof_inventory_lookup"
RESOURCE_TABLE = "s52_proof_inventory_resource"
SUMMARY_TABLE = "s52_proof_inventory_summary"


def json_dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def json_loads(value: str | None) -> Any:
    if not value:
        return []
    return json.loads(value)


def norm_id(value: str | None) -> str:
    return "".join(str(value or "").upper().split())


def load_site_index(path: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    if not path.exists():
        return {}, {}
    payload = json.loads(path.read_text())
    symbols = payload.get("symbols") or []
    return payload, {norm_id(row.get("id")): row for row in symbols if row.get("id")}


def current_opencpn_head() -> str | None:
    try:
        proc = subprocess.run(
            ["git", "ls-remote", OPENCPN_REPO, "refs/heads/master"],
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    first = proc.stdout.strip().split()
    return first[0] if first else None


def metadata(conn: sqlite3.Connection) -> dict[str, str]:
    return {key: value for key, value in conn.execute("select key, value from s52_source_metadata")}


def fetch_existing_assets(conn: sqlite3.Connection) -> tuple[set[str], set[str], dict[str, dict[str, Any]]]:
    standard_assets = {norm_id(row[0]) for row in conn.execute("select asset from iconforge_standard_source_row")}
    resolver_assets = {norm_id(row[0]) for row in conn.execute("select asset from iconforge_s101_resolver_row")}
    resolver_rows: dict[str, dict[str, Any]] = {}
    for row in conn.execute(
        """
        select asset, resolver_status, s101_mapping_type, s101_crosswalk_class,
               s101_feature_type, s101_rule_file, s101_direct_symbol_id,
               s101_attributes, unresolved_reasons
        from iconforge_s101_resolver_row
        """
    ):
        resolver_rows[norm_id(row[0])] = {
            "asset": row[0],
            "resolver_status": row[1],
            "mapping_type": row[2],
            "crosswalk_class": row[3],
            "feature_type": row[4],
            "rule_file": row[5],
            "direct_symbol_id": row[6],
            "attributes": json_loads(row[7]),
            "unresolved_reasons": json_loads(row[8]),
        }
    return standard_assets, resolver_assets, resolver_rows


def classify_lookup(row: sqlite3.Row) -> tuple[str, list[str]]:
    object_class = str(row["object_acronym"] or "").upper()
    primitive = row["primitive_type"]
    symbols = json_loads(row["symbol_refs"])
    lines = json_loads(row["line_style_refs"])
    patterns = json_loads(row["pattern_refs"])
    conditionals = json_loads(row["conditional_refs"])
    texts = json_loads(row["text_refs"])
    reasons: list[str] = []

    if object_class.startswith("SOUND") or any(str(ref).upper().startswith("SOUND") for ref in conditionals):
        return "sounding_text", ["sounding_or_depth_text_portrayal"]
    if patterns:
        reasons.append("uses_area_pattern_refs")
        return "area_pattern", reasons
    if lines and not symbols:
        reasons.append("uses_line_style_refs")
        return "line_style", reasons
    if conditionals and not symbols and not lines and not patterns:
        reasons.append("uses_conditional_procedure_only")
        return "conditional_rule", reasons
    if texts and not symbols and not lines and not patterns:
        reasons.append("uses_text_commands_only")
        return "sounding_text", reasons
    if symbols and primitive == "Point":
        reasons.append("point_lookup_with_symbol_refs")
        return "point_symbol", reasons
    if symbols:
        reasons.append(f"{primitive.lower()}_lookup_with_symbol_component_refs")
        return "runtime_composite_portrayal", reasons
    if conditionals:
        reasons.append("uses_conditional_procedure")
        return "conditional_rule", reasons
    reasons.append("no_render_refs_in_lookup_instruction")
    return "runtime_composite_portrayal", reasons


def classify_resource(resource_type: str, name: str, referenced: int) -> tuple[str, list[str]]:
    upper = norm_id(name)
    reasons: list[str] = []
    if resource_type == "line_style":
        return "line_style", ["opencpn_line_style_resource"]
    if resource_type == "pattern":
        return "area_pattern", ["opencpn_area_pattern_resource"]
    if resource_type == "palette_color":
        return "palette_color", ["opencpn_palette_color_resource"]
    if upper.startswith(("SOUNDG", "SOUNDS", "SOUND")):
        return "sounding_text", ["sounding_glyph_resource"]
    if upper.startswith(("TOPMAR", "TOPSHP", "TOPMA", "TMARDEF")):
        return "component_internal_symbol", ["topmark_daymark_component_resource"]
    if upper.startswith(("ADDMRK", "PLNPOS", "DWRTPT")):
        return "component_internal_symbol", ["composite_symbol_component_resource"]
    if referenced == 0:
        return "component_internal_symbol", ["defined_resource_not_directly_referenced_by_lookup"]
    reasons.append("referenced_symbol_resource")
    return "point_symbol", reasons


def status_for_asset(name: str, public: dict[str, Any], standard_assets: set[str], resolver_assets: set[str]) -> dict[str, Any]:
    key = norm_id(name)
    public_row = public.get(key)
    helm_status = "helm_standard_source_present" if key in standard_assets else "missing_helm_candidate"
    s101_status = "s101_resolver_present" if key in resolver_assets else "missing_s101_resolver_row"
    public_status = "public_symbol_present" if public_row else "not_in_public_symbol_catalog"
    return {
        "public_status": public_status,
        "public_id": public_row.get("id") if public_row else None,
        "helm_status": helm_status,
        "s101_status": s101_status,
    }


def build_inventory(
    conn: sqlite3.Connection,
    *,
    site_index: Path,
    upstream_head: str | None,
) -> dict[str, Any]:
    conn.row_factory = sqlite3.Row
    meta = metadata(conn)
    imported_sha = meta.get("source_git_sha")
    source_file = "data/s57data/chartsymbols.xml"
    if upstream_head is None:
        freshness = "unknown_unable_to_check_upstream"
    elif imported_sha == upstream_head:
        freshness = "current"
    else:
        freshness = "stale_against_upstream_master"

    site_payload, public_symbols = load_site_index(site_index)
    public_catalog_rows = len(site_payload.get("symbols") or [])
    standard_assets, resolver_assets, resolver_rows = fetch_existing_assets(conn)

    ref_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for lookup in conn.execute(
        "select primitive_type, symbol_refs, line_style_refs, pattern_refs, conditional_refs from s52_portrayal_lookup"
    ):
        for field, resource_type in (
            ("symbol_refs", "symbol"),
            ("line_style_refs", "line_style"),
            ("pattern_refs", "pattern"),
            ("conditional_refs", "conditional"),
        ):
            for ref in json_loads(lookup[field]):
                ref_counts[norm_id(ref)][resource_type] += 1

    conn.executescript(
        f"""
        drop table if exists {LOOKUP_TABLE};
        drop table if exists {RESOURCE_TABLE};
        drop table if exists {SUMMARY_TABLE};

        create table {LOOKUP_TABLE} (
          s52_lookup_id integer primary key references s52_portrayal_lookup(id) on delete cascade,
          inventory_key text not null unique,
          source_git_sha text not null,
          source_file text not null,
          upstream_master_sha text,
          source_freshness_status text not null,
          object_acronym text not null,
          object_name text,
          primitive_type text not null,
          lookup_table text not null,
          display_category text,
          portrayal_class text not null,
          opencpn_reference_status text not null,
          helm_candidate_status text not null,
          helm_public_status text not null,
          s101_candidate_status text not null,
          s101_mapping_type text,
          s101_feature_type text,
          symbol_refs text not null check (json_valid(symbol_refs)),
          line_style_refs text not null check (json_valid(line_style_refs)),
          pattern_refs text not null check (json_valid(pattern_refs)),
          conditional_refs text not null check (json_valid(conditional_refs)),
          text_refs text not null check (json_valid(text_refs)),
          colour_refs text not null check (json_valid(colour_refs)),
          proof_columns text not null check (json_valid(proof_columns)),
          classification_reasons text not null check (json_valid(classification_reasons)),
          created_at text not null default current_timestamp
        );

        create table {RESOURCE_TABLE} (
          resource_id integer primary key references s52_portrayal_resource(id) on delete cascade,
          source_git_sha text not null,
          source_file text not null,
          upstream_master_sha text,
          source_freshness_status text not null,
          resource_type text not null,
          name text not null,
          normalized_name text not null,
          description text,
          resource_class text not null,
          referenced_by_lookup_count integer not null,
          helm_candidate_status text not null,
          helm_public_status text not null,
          s101_candidate_status text not null,
          proof_columns text not null check (json_valid(proof_columns)),
          classification_reasons text not null check (json_valid(classification_reasons)),
          created_at text not null default current_timestamp
        );

        create table {SUMMARY_TABLE} (
          key text primary key,
          value text not null check (json_valid(value)),
          created_at text not null default current_timestamp
        );

        create index s52_proof_inventory_lookup_class_idx on {LOOKUP_TABLE}(portrayal_class);
        create index s52_proof_inventory_lookup_public_idx on {LOOKUP_TABLE}(helm_public_status);
        create index s52_proof_inventory_resource_class_idx on {RESOURCE_TABLE}(resource_class);
        create index s52_proof_inventory_resource_public_idx on {RESOURCE_TABLE}(helm_public_status);
        """
    )

    lookup_rows: list[dict[str, Any]] = []
    for row in conn.execute("select * from s52_portrayal_lookup order by id"):
        portrayal_class, reasons = classify_lookup(row)
        refs = {
            "symbols": json_loads(row["symbol_refs"]),
            "line_styles": json_loads(row["line_style_refs"]),
            "area_patterns": json_loads(row["pattern_refs"]),
            "conditional_rules": json_loads(row["conditional_refs"]),
            "text": json_loads(row["text_refs"]),
            "colours": json_loads(row["color_refs"]),
        }
        referenced_assets = refs["symbols"] + refs["line_styles"] + refs["area_patterns"] + refs["conditional_rules"]
        statuses = [status_for_asset(ref, public_symbols, standard_assets, resolver_assets) for ref in referenced_assets]
        public_status = "no_discrete_public_symbol_expected"
        helm_status = "non_icon_portrayal_or_composite"
        s101_status = "non_icon_portrayal_or_rule_derived"
        if statuses:
            public_status = (
                "all_referenced_assets_in_public_catalog"
                if all(item["public_status"] == "public_symbol_present" for item in statuses)
                else "some_referenced_assets_missing_from_public_catalog"
            )
            helm_status = (
                "all_referenced_assets_have_helm_source"
                if all(item["helm_status"] == "helm_standard_source_present" for item in statuses)
                else "some_referenced_assets_missing_helm_source"
            )
            s101_status = (
                "all_referenced_assets_have_s101_resolver"
                if all(item["s101_status"] == "s101_resolver_present" for item in statuses)
                else "some_referenced_assets_missing_s101_resolver"
            )
        resolver = None
        for ref in refs["symbols"]:
            resolver = resolver_rows.get(norm_id(ref))
            if resolver:
                break
        opencpn_status = (
            "exact_s52_lookup_instruction"
            if portrayal_class in {"point_symbol", "line_style", "area_pattern"}
            else "explicit_non_thumbnail_portrayal_classification"
        )
        proof_columns = {
            "opencpn": {
                "status": opencpn_status,
                "source": "OpenCPN chartsymbols.xml",
                "instruction": row["instruction"],
                "refs": refs,
            },
            "helm": {
                "status": helm_status,
                "public_status": public_status,
                "referenced_assets": statuses,
            },
            "s101": {
                "status": s101_status,
                "resolver": resolver,
            },
        }
        inventory_key = f"lookup:{row['id']}:{row['object_acronym']}:{row['primitive_type']}:{row['lookup_table']}"
        record = {
            "s52_lookup_id": row["id"],
            "inventory_key": inventory_key,
            "source_git_sha": row["source_git_sha"],
            "source_file": row["source_file"],
            "upstream_master_sha": upstream_head,
            "source_freshness_status": freshness,
            "object_acronym": row["object_acronym"],
            "object_name": row["object_name"],
            "primitive_type": row["primitive_type"],
            "lookup_table": row["lookup_table"],
            "display_category": row["display_category"],
            "portrayal_class": portrayal_class,
            "opencpn_reference_status": opencpn_status,
            "helm_candidate_status": helm_status,
            "helm_public_status": public_status,
            "s101_candidate_status": s101_status,
            "s101_mapping_type": resolver.get("mapping_type") if resolver else None,
            "s101_feature_type": resolver.get("feature_type") if resolver else None,
            "symbol_refs": refs["symbols"],
            "line_style_refs": refs["line_styles"],
            "pattern_refs": refs["area_patterns"],
            "conditional_refs": refs["conditional_rules"],
            "text_refs": refs["text"],
            "colour_refs": refs["colours"],
            "proof_columns": proof_columns,
            "classification_reasons": reasons,
        }
        lookup_rows.append(record)
        conn.execute(
            f"""
            insert into {LOOKUP_TABLE} (
              s52_lookup_id, inventory_key, source_git_sha, source_file,
              upstream_master_sha, source_freshness_status, object_acronym,
              object_name, primitive_type, lookup_table, display_category,
              portrayal_class, opencpn_reference_status, helm_candidate_status,
              helm_public_status, s101_candidate_status, s101_mapping_type,
              s101_feature_type, symbol_refs, line_style_refs, pattern_refs,
              conditional_refs, text_refs, colour_refs, proof_columns,
              classification_reasons
            ) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                record["s52_lookup_id"],
                record["inventory_key"],
                record["source_git_sha"],
                record["source_file"],
                record["upstream_master_sha"],
                record["source_freshness_status"],
                record["object_acronym"],
                record["object_name"],
                record["primitive_type"],
                record["lookup_table"],
                record["display_category"],
                record["portrayal_class"],
                record["opencpn_reference_status"],
                record["helm_candidate_status"],
                record["helm_public_status"],
                record["s101_candidate_status"],
                record["s101_mapping_type"],
                record["s101_feature_type"],
                json_dumps(record["symbol_refs"]),
                json_dumps(record["line_style_refs"]),
                json_dumps(record["pattern_refs"]),
                json_dumps(record["conditional_refs"]),
                json_dumps(record["text_refs"]),
                json_dumps(record["colour_refs"]),
                json_dumps(record["proof_columns"]),
                json_dumps(record["classification_reasons"]),
            ),
        )

    resource_rows: list[dict[str, Any]] = []
    for row in conn.execute("select * from s52_portrayal_resource order by resource_type, resource_order"):
        key = norm_id(row["name"])
        ref_count = sum(ref_counts.get(key, Counter()).values())
        resource_class, reasons = classify_resource(row["resource_type"], row["name"], ref_count)
        asset_status = status_for_asset(row["name"], public_symbols, standard_assets, resolver_assets)
        proof_columns = {
            "opencpn": {
                "status": "resource_definition",
                "source": "OpenCPN chartsymbols.xml",
                "resource_type": row["resource_type"],
                "definition_type": row["definition_type"],
            },
            "helm": {
                "status": asset_status["helm_status"],
                "public_status": asset_status["public_status"],
                "public_id": asset_status["public_id"],
            },
            "s101": {
                "status": asset_status["s101_status"],
                "resolver": resolver_rows.get(key),
            },
        }
        record = {
            "resource_id": row["id"],
            "source_git_sha": row["source_git_sha"],
            "source_file": source_file,
            "upstream_master_sha": upstream_head,
            "source_freshness_status": freshness,
            "resource_type": row["resource_type"],
            "name": row["name"],
            "normalized_name": key,
            "description": row["description"],
            "resource_class": resource_class,
            "referenced_by_lookup_count": ref_count,
            "helm_candidate_status": asset_status["helm_status"],
            "helm_public_status": asset_status["public_status"],
            "s101_candidate_status": asset_status["s101_status"],
            "proof_columns": proof_columns,
            "classification_reasons": reasons,
        }
        resource_rows.append(record)
        conn.execute(
            f"""
            insert into {RESOURCE_TABLE} (
              resource_id, source_git_sha, source_file, upstream_master_sha,
              source_freshness_status, resource_type, name, normalized_name,
              description, resource_class, referenced_by_lookup_count,
              helm_candidate_status, helm_public_status, s101_candidate_status,
              proof_columns, classification_reasons
            ) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                record["resource_id"],
                record["source_git_sha"],
                record["source_file"],
                record["upstream_master_sha"],
                record["source_freshness_status"],
                record["resource_type"],
                record["name"],
                record["normalized_name"],
                record["description"],
                record["resource_class"],
                record["referenced_by_lookup_count"],
                record["helm_candidate_status"],
                record["helm_public_status"],
                record["s101_candidate_status"],
                json_dumps(record["proof_columns"]),
                json_dumps(record["classification_reasons"]),
            ),
        )

    lookup_class_counts = Counter(row["portrayal_class"] for row in lookup_rows)
    resource_type_counts = Counter(row["resource_type"] for row in resource_rows)
    resource_class_counts = Counter(row["resource_class"] for row in resource_rows)
    public_missing_referenced = sorted(
        {
            resource["name"]
            for resource in resource_rows
            if resource["referenced_by_lookup_count"] > 0
            and resource["resource_type"] == "symbol"
            and resource["helm_public_status"] == "not_in_public_symbol_catalog"
        }
    )
    symbol_resource_names = {
        row["normalized_name"] for row in resource_rows if row["resource_type"] == "symbol"
    }
    line_style_names = {
        row["normalized_name"] for row in resource_rows if row["resource_type"] == "line_style"
    }
    area_pattern_names = {
        row["normalized_name"] for row in resource_rows if row["resource_type"] == "pattern"
    }
    summary = {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "repo": meta.get("source_repo", OPENCPN_REPO),
            "imported_git_sha": imported_sha,
            "upstream_master_sha": upstream_head,
            "source_file": source_file,
            "freshness_status": freshness,
        },
        "counts": {
            "lookup_rows": len(lookup_rows),
            "resource_rows": len(resource_rows),
            "symbol_resource_rows": sum(1 for row in resource_rows if row["resource_type"] == "symbol"),
            "distinct_symbol_names": len(symbol_resource_names),
            "distinct_line_styles": len(line_style_names),
            "distinct_area_patterns": len(area_pattern_names),
            "palette_colours": sum(1 for row in resource_rows if row["resource_type"] == "palette_color"),
            "public_catalog_rows": public_catalog_rows,
            "public_distinct_symbol_ids": len(public_symbols),
            "referenced_symbol_resources_missing_public_catalog": len(public_missing_referenced),
        },
        "lookup_class_counts": dict(sorted(lookup_class_counts.items())),
        "resource_type_counts": dict(sorted(resource_type_counts.items())),
        "resource_class_counts": dict(sorted(resource_class_counts.items())),
        "known_gap_resolution": {
            "referenced_symbol_resources_missing_public_catalog": public_missing_referenced,
            "policy": "Missing public icon rows are now explicit inventory classifications, not hidden proof coverage.",
        },
        "proof_gate": {
            "full_s52_proof_claim_allowed": freshness == "current" and len(public_missing_referenced) == 0,
            "blockers": [
                blocker
                for blocker, active in (
                    ("opencpn_source_pin_stale_or_unverified", freshness != "current"),
                    (
                        "referenced_symbol_resources_missing_from_public_catalog",
                        len(public_missing_referenced) > 0,
                    ),
                )
                if active
            ],
        },
    }

    conn.execute(f"insert into {SUMMARY_TABLE}(key, value) values (?, ?)", ("summary", json_dumps(summary)))
    conn.execute(
        f"insert into {SUMMARY_TABLE}(key, value) values (?, ?)",
        (
            "public_missing_referenced_symbols",
            json_dumps({"symbols": public_missing_referenced}),
        ),
    )
    conn.commit()
    return {
        **summary,
        "lookups": lookup_rows,
        "resources": resource_rows,
    }


def write_public_inventory(path: Path, inventory: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(inventory, separators=(",", ":"), sort_keys=False) + "\n")


def update_site_index(path: Path, inventory: dict[str, Any]) -> None:
    if not path.exists():
        return
    payload = json.loads(path.read_text())
    coverage = payload.setdefault("coverage", {})
    coverage["s52_portrayal_inventory"] = {
        "schema": SCHEMA,
        "path": "proof/s52-portrayal-inventory.json",
        "source": inventory["source"],
        "counts": inventory["counts"],
        "lookup_class_counts": inventory["lookup_class_counts"],
        "resource_class_counts": inventory["resource_class_counts"],
        "proof_gate": inventory["proof_gate"],
    }
    path.write_text(json.dumps(payload, separators=(",", ":"), sort_keys=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--site-index", type=Path, default=DEFAULT_SITE_INDEX)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--upstream-head", default=None)
    parser.add_argument("--skip-upstream-check", action="store_true")
    args = parser.parse_args()

    upstream = args.upstream_head
    if not upstream and not args.skip_upstream_check:
        upstream = current_opencpn_head()

    with sqlite3.connect(args.db) as conn:
        conn.row_factory = sqlite3.Row
        inventory = build_inventory(conn, site_index=args.site_index, upstream_head=upstream)

    write_public_inventory(args.output, inventory)
    update_site_index(args.site_index, inventory)
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "db": str(args.db),
                "output": str(args.output),
                "counts": inventory["counts"],
                "proof_gate": inventory["proof_gate"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
