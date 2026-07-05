"""Export the FORGE-39 electronic Chart 1 DB contract.

This module is intentionally read-only. It turns the DB-backed
`electronic_chart1_entry_v1` view into deterministic JSON/Markdown artifacts for
the later fixture, render-harness, diff, proof-UI, and runtime-promotion tasks.

Run:
  python3 -m forge.electronic_chart1_contract
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = ROOT.parent.parent
DB_PATH = ROOT.parent.parent / "artifacts" / "opencpn_s52_portrayal.sqlite"
CATALOG = ROOT / "catalog"
CONTRACT_JSON = CATALOG / "electronic_chart1_contract.json"
CONTRACT_MD = CATALOG / "electronic_chart1_contract.md"
SCHEMA = "helm.forge.electronic_chart1_contract.v1"


def _json(value: str | None, default: Any) -> Any:
    if value is None or value == "":
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rel(path: Path) -> str:
    """Repo-relative POSIX path so provenance never bakes a build-host absolute path."""
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _connect(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    return con


def _row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "s52_lookup_id": row["s52_lookup_id"],
        "row_key": row["row_key"],
        "chart1_row_id": row["chart1_row_id"],
        "row_taxonomy": row["row_taxonomy"],
        "taxonomy_reason": row["taxonomy_reason"],
        "evidence_status": row["evidence_status"],
        "render_eligibility": row["render_eligibility"],
        "reason_codes": _json(row["reason_codes"], []),
        "s57": {
            "object_class": row["s57_object_class"],
            "attribute_tuple": _json(row["s57_attribute_tuple"], {}),
        },
        "s52": {
            "instruction": row["s52_instruction"],
            "instruction_evidence": _json(row["s52_instruction_evidence"], {}),
        },
        "s101": _json(row["s101_evidence"], {}),
        "helm": {
            "art_path": row["helm_art_path"],
            "art_status": row["helm_art_status"],
            "colour_authority": _json(row["colour_authority"], {}),
            "shape_family_authority": _json(row["shape_family_authority"], {}),
        },
        "human_qa_status": _json(row["human_qa_status"], {}),
        "provenance": _json(row["provenance"], {}),
    }


def build_contract(*, db_path: Path = DB_PATH, limit: int | None = None) -> dict[str, Any]:
    if not db_path.exists():
        raise FileNotFoundError(f"electronic Chart 1 DB missing: {db_path}")
    with _connect(db_path) as con:
        rows_sql = "SELECT * FROM electronic_chart1_entry_v1 ORDER BY s52_lookup_id"
        params: list[Any] = []
        if limit is not None:
            rows_sql += " LIMIT ?"
            params.append(limit)
        rows = [_row(row) for row in con.execute(rows_sql, params)]
        total_rows = con.execute("SELECT COUNT(*) FROM electronic_chart1_entry_v1").fetchone()[0]
        runtime_rows = con.execute("SELECT COUNT(*) FROM runtime_symbol_portrayal_v1").fetchone()[0]
        non_fail_closed = con.execute(
            """
            SELECT COUNT(*)
            FROM electronic_chart1_entry_v1
            WHERE render_eligibility != 'fail_closed_not_runtime_eligible'
            """
        ).fetchone()[0]
        failing_audits = [
            dict(row)
            for row in con.execute(
                """
                SELECT check_name, expected, actual, detail
                FROM s52_s101_import_audit
                WHERE status != 'pass'
                ORDER BY check_name
                """
            )
        ]

    taxonomy_counts = Counter(row["row_taxonomy"] for row in rows)
    status_counts = Counter(row["evidence_status"] for row in rows)
    reason_counts: Counter[str] = Counter()
    for row in rows:
        reason_counts.update(row["reason_codes"])

    return {
        "schema": SCHEMA,
        "status": "contract_ready" if not failing_audits and non_fail_closed == 0 else "contract_blocked",
        "policy": {
            "purpose": "review/proof contract for electronic Chart 1 rows",
            "runtime_promotion_allowed": False,
            "render_eligibility": "fail_closed_not_runtime_eligible",
            "browser_business_logic_allowed": False,
            "clean_room_boundary": "metadata/proof contract only; no bundled IHO/OpenCPN artwork",
        },
        "source": {
            "db_path": _rel(db_path),
            "db_sha256": _sha256(db_path),
            "view": "electronic_chart1_entry_v1",
            "generator": "scripts/augment-opencpn-s52-s101-semantics.py",
        },
        "summary": {
            "rows": len(rows),
            "total_db_rows": total_rows,
            "runtime_symbol_portrayal_rows": runtime_rows,
            "non_fail_closed_rows": non_fail_closed,
            "taxonomy_counts": dict(sorted(taxonomy_counts.items())),
            "evidence_status_counts": dict(sorted(status_counts.items())),
            "top_reason_counts": dict(reason_counts.most_common(20)),
            "failing_audits": failing_audits,
        },
        "rows": rows,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n")


def _markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Electronic Chart 1 Contract",
        "",
        "FORGE-39 DB-backed source-of-truth contract for electronic Chart 1 proof rows.",
        "",
        f"- schema: `{payload['schema']}`",
        f"- status: `{payload['status']}`",
        f"- rows: `{summary['rows']}`",
        f"- runtime_symbol_portrayal_rows: `{summary['runtime_symbol_portrayal_rows']}`",
        f"- non_fail_closed_rows: `{summary['non_fail_closed_rows']}`",
        "",
        "## Policy",
        "",
        "- This is a proof/review contract, not runtime promotion.",
        "- Browser/UI consumers must display backend facts and must not infer symbol meaning.",
        "- OpenCPN/S-52 and S-101 evidence is reference metadata; no external artwork is bundled here.",
        "",
        "## Row Taxonomy",
        "",
        "| Taxonomy | Count |",
        "| --- | ---: |",
    ]
    for name, count in summary["taxonomy_counts"].items():
        lines.append(f"| `{name}` | {count} |")
    lines.extend([
        "",
        "## Evidence Status",
        "",
        "| Status | Count |",
        "| --- | ---: |",
    ])
    for name, count in summary["evidence_status_counts"].items():
        lines.append(f"| `{name}` | {count} |")
    lines.extend([
        "",
        "## Top Reason Codes",
        "",
        "| Reason | Count |",
        "| --- | ---: |",
    ])
    for reason, count in summary["top_reason_counts"].items():
        lines.append(f"| `{reason}` | {count} |")
    return "\n".join(lines) + "\n"


def write_contract(
    *,
    db_path: Path = DB_PATH,
    json_path: Path = CONTRACT_JSON,
    markdown_path: Path = CONTRACT_MD,
) -> dict[str, Any]:
    payload = build_contract(db_path=db_path)
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
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--json", type=Path, default=CONTRACT_JSON)
    parser.add_argument("--markdown", type=Path, default=CONTRACT_MD)
    args = parser.parse_args(argv)
    print(json.dumps(write_contract(db_path=args.db, json_path=args.json, markdown_path=args.markdown), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
