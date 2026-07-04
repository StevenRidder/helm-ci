"""FORGE runtime DB contract proof.

This report is backend-only evidence for CHART/runtime consumers. It proves the
checked-in SQLite DB is structurally valid, that broad/review and strict/runtime
views have explicit invariants, and that the current zero-row runtime export is a
deliberate fail-closed gate state.

Run:
  python3 -m forge.runtime_db_contract
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
REPO = ROOT.parent.parent
DB_PATH = REPO / "artifacts" / "opencpn_s52_portrayal.sqlite"
CATALOG = ROOT / "catalog"
CONTRACT_JSON = CATALOG / "runtime_db_contract.json"
CONTRACT_MD = CATALOG / "runtime_db_contract.md"
SCHEMA = "helm.iconforge.runtime_db_contract.v1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _connect(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    return con


def _scalar(con: sqlite3.Connection, sql: str) -> int:
    return int(con.execute(sql).fetchone()[0])


def _rows(con: sqlite3.Connection, sql: str) -> list[dict[str, Any]]:
    return [dict(row) for row in con.execute(sql)]


def _check(name: str, ok: bool, expected: str, actual: Any, detail: str) -> dict[str, Any]:
    return {
        "name": name,
        "status": "pass" if ok else "fail",
        "expected": expected,
        "actual": actual,
        "detail": detail,
    }


def build_contract(*, db_path: Path = DB_PATH) -> dict[str, Any]:
    if not db_path.exists():
        raise FileNotFoundError(f"runtime DB missing: {db_path}")
    with _connect(db_path) as con:
        integrity = [row[0] for row in con.execute("PRAGMA integrity_check")]
        foreign_key_rows = _rows(con, "PRAGMA foreign_key_check")
        lookup_rows = _scalar(con, "SELECT COUNT(*) FROM s52_portrayal_lookup")
        candidate_rows = _scalar(con, "SELECT COUNT(*) FROM runtime_symbol_candidate_v1")
        portrayal_rows = _scalar(con, "SELECT COUNT(*) FROM runtime_symbol_portrayal_v1")
        eligible_rows = _scalar(
            con,
            "SELECT COUNT(*) FROM runtime_symbol_candidate_v1 WHERE runtime_eligible = 1"
        )
        blocker_rows = _scalar(con, "SELECT COUNT(*) FROM runtime_symbol_blocker_v1")
        visual_pending_rows = _scalar(
            con,
            """
            SELECT COUNT(*)
            FROM runtime_symbol_gate
            WHERE gate_name = 'visual_approval'
              AND gate_status = 'pending'
            """,
        )
        ineligible_without_blockers = _scalar(
            con,
            """
            SELECT COUNT(*)
            FROM runtime_symbol_candidate_v1 c
            WHERE c.runtime_eligible = 0
              AND NOT EXISTS (
                SELECT 1
                FROM runtime_symbol_blocker_v1 b
                WHERE b.s52_lookup_id = c.s52_lookup_id
              )
            """,
        )
        gate_mismatch_rows = _scalar(
            con,
            """
            SELECT COUNT(*)
            FROM runtime_symbol_candidate_v1 c
            WHERE c.runtime_eligible != CASE
              WHEN c.candidate_status = 'runtime_eligible'
               AND c.blocking_gate_count = 0
               AND c.pending_gate_count = 0
               AND NOT EXISTS (
                 SELECT 1
                 FROM runtime_symbol_gate g
                 WHERE g.s52_lookup_id = c.s52_lookup_id
                   AND g.gate_status IN ('blocked', 'pending')
               )
              THEN 1 ELSE 0 END
            """,
        )
        derived_portrayal_rows = _scalar(
            con,
            """
            SELECT COUNT(*)
            FROM runtime_symbol_candidate_v1 c
            WHERE c.runtime_eligible = 1
              AND c.candidate_status = 'runtime_eligible'
              AND c.blocking_gate_count = 0
              AND c.pending_gate_count = 0
              AND NOT EXISTS (
                SELECT 1
                FROM runtime_symbol_gate g
                WHERE g.s52_lookup_id = c.s52_lookup_id
                  AND g.gate_status IN ('blocked', 'pending')
              )
            """,
        )
        leaky_portrayal_rows = _scalar(
            con,
            """
            SELECT COUNT(*)
            FROM runtime_symbol_portrayal_v1 p
            WHERE p.runtime_eligible != 1
               OR p.candidate_status != 'runtime_eligible'
               OR p.blocking_gate_count != 0
               OR p.pending_gate_count != 0
               OR EXISTS (
                 SELECT 1
                 FROM runtime_symbol_gate g
                 WHERE g.s52_lookup_id = p.s52_lookup_id
                   AND g.gate_status IN ('blocked', 'pending')
               )
            """,
        )
        malformed_blockers = _scalar(
            con,
            """
            SELECT COUNT(*)
            FROM runtime_symbol_blocker_v1
            WHERE gate_name = ''
               OR gate_status NOT IN ('blocked', 'pending')
               OR severity = ''
               OR detail = ''
               OR evidence IS NULL
               OR json_valid(evidence) = 0
            """,
        )
        audit_fail_rows = _rows(
            con,
            """
            SELECT check_name, expected, actual, detail
            FROM s52_s101_import_audit
            WHERE status != 'pass'
            ORDER BY check_name
            """,
        )
        candidate_status_counts = {
            row["candidate_status"]: row["count"]
            for row in con.execute(
                """
                SELECT candidate_status, COUNT(*) AS count
                FROM runtime_symbol_candidate_v1
                GROUP BY candidate_status
                ORDER BY candidate_status
                """
            )
        }
        blocker_gate_counts = _rows(
            con,
            """
            SELECT gate_name, gate_status, severity, COUNT(*) AS count
            FROM runtime_symbol_blocker_v1
            GROUP BY gate_name, gate_status, severity
            ORDER BY gate_name, gate_status, severity
            """,
        )

    checks = [
        _check("sqlite_integrity_check", integrity == ["ok"], "ok", integrity, "SQLite pages and indexes are valid."),
        _check("sqlite_foreign_key_check", not foreign_key_rows, "no rows", foreign_key_rows, "Foreign-key graph is intact."),
        _check(
            "runtime_candidate_view_covers_lookup_rows",
            candidate_rows == lookup_rows,
            f"{lookup_rows} rows",
            candidate_rows,
            "runtime_symbol_candidate_v1 is the complete review/browse surface.",
        ),
        _check(
            "runtime_blocker_view_explains_ineligible_rows",
            ineligible_without_blockers == 0 and blocker_rows > 0,
            "0 ineligible rows without blockers",
            {"blocker_rows": blocker_rows, "ineligible_without_blockers": ineligible_without_blockers},
            "runtime_symbol_blocker_v1 exposes queryable blocked/pending reasons.",
        ),
        _check(
            "runtime_portrayal_view_is_strict_gate_clear_surface",
            portrayal_rows == derived_portrayal_rows and leaky_portrayal_rows == 0,
            "view equals derived gate-clear query, with 0 leaky rows",
            {
                "runtime_symbol_portrayal_v1": portrayal_rows,
                "derived_gate_clear_rows": derived_portrayal_rows,
                "leaky_rows": leaky_portrayal_rows,
            },
            "runtime_symbol_portrayal_v1 fails closed from full gate state, not just one flag.",
        ),
        _check(
            "runtime_eligibility_matches_gate_state",
            gate_mismatch_rows == 0,
            "0 mismatches",
            gate_mismatch_rows,
            "candidate_status/runtime_eligible agree with blocking and pending gates.",
        ),
        _check(
            "blocker_rows_are_queryable",
            malformed_blockers == 0,
            "0 malformed blocker rows",
            malformed_blockers,
            "Each blocker row has gate name/status/severity/detail and valid JSON evidence.",
        ),
        _check(
            "zero_runtime_rows_are_deliberate_fail_closed",
            eligible_rows == 0 and portrayal_rows == 0 and visual_pending_rows == lookup_rows,
            "0 eligible and strict rows while visual approval is pending for every lookup row",
            {
                "runtime_eligible_rows": eligible_rows,
                "runtime_symbol_portrayal_v1": portrayal_rows,
                "visual_approval_pending_rows": visual_pending_rows,
            },
            "The empty runtime surface is an approval gate state, not missing DB data.",
        ),
        _check(
            "import_audit_has_no_fail_rows",
            not audit_fail_rows,
            "0 failing audit rows",
            audit_fail_rows,
            "The checked-in import audit has no hidden failures.",
        ),
    ]

    return {
        "schema": SCHEMA,
        "status": "contract_pass" if all(check["status"] == "pass" for check in checks) else "contract_fail",
        "source": {
            "db": str(db_path.relative_to(REPO) if db_path.is_relative_to(REPO) else db_path),
            "db_sha256": _sha256(db_path),
            "generator": "scripts/augment-opencpn-s52-s101-semantics.py",
        },
        "view_invariants": {
            "runtime_symbol_candidate_v1": [
                "one row per OpenCPN s52_portrayal_lookup row",
                "broad browse/review surface; not runtime serving approval",
                "runtime_eligible must agree with candidate_status and blocked/pending gate state",
            ],
            "runtime_symbol_blocker_v1": [
                "one row per blocked or pending runtime_symbol_gate",
                "every ineligible candidate must have at least one blocker row",
                "gate_name, gate_status, severity, detail, and JSON evidence are mandatory",
            ],
            "runtime_symbol_portrayal_v1": [
                "strict runtime serving surface",
                "requires runtime_eligible=1, candidate_status=runtime_eligible, zero blocking gates, zero pending gates",
                "also excludes rows with any blocked or pending runtime_symbol_gate",
            ],
        },
        "summary": {
            "lookup_rows": lookup_rows,
            "candidate_rows": candidate_rows,
            "runtime_symbol_portrayal_rows": portrayal_rows,
            "runtime_eligible_rows": eligible_rows,
            "blocker_rows": blocker_rows,
            "visual_approval_pending_rows": visual_pending_rows,
            "candidate_status_counts": candidate_status_counts,
            "blocker_gate_counts": blocker_gate_counts,
        },
        "checks": checks,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n")


def _markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Runtime DB Contract",
        "",
        "FORGE-50 backend proof for the runtime symbol DB gate contract.",
        "",
        f"- schema: `{payload['schema']}`",
        f"- status: `{payload['status']}`",
        f"- db: `{payload['source']['db']}`",
        f"- lookup_rows: `{payload['summary']['lookup_rows']}`",
        f"- runtime_symbol_portrayal_rows: `{payload['summary']['runtime_symbol_portrayal_rows']}`",
        f"- blocker_rows: `{payload['summary']['blocker_rows']}`",
        "",
        "## View Invariants",
        "",
    ]
    for view, invariants in payload["view_invariants"].items():
        lines.append(f"### `{view}`")
        lines.extend(f"- {item}" for item in invariants)
        lines.append("")
    lines.extend(["## Checks", "", "| Check | Status | Detail |", "| --- | --- | --- |"])
    for check in payload["checks"]:
        lines.append(f"| `{check['name']}` | `{check['status']}` | {check['detail']} |")
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
    result = write_contract(db_path=args.db, json_path=args.json, markdown_path=args.markdown)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
