"""Build the FORGE-48 stale-audit reconciliation ledger.

This is not a runtime contract generator. It records how each finding from the
2026-07-04 stale FORGE-24/25 audit compares with the current origin/main DB and
Icon Forge code.

Run:
  python3 -m forge.forge48_audit_ledger
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
REPO = ROOT.parent.parent
CATALOG = ROOT / "catalog"
DB = REPO / "artifacts" / "opencpn_s52_portrayal.sqlite"
OUT_JSON = CATALOG / "forge48_current_findings_ledger.json"
OUT_MD = CATALOG / "forge48_current_findings_ledger.md"
SOURCE_AUDIT = Path(
    "/Users/steveridder/.codex/attachments/6d3507bb-f434-4256-a5f2-d25a61a865f5/pasted-text.txt"
)
SOURCE_AUDIT_SHA256 = "03292c7fcc01ca5d9b1a86b32a4ffe15b7c037aca95088526ec6575bf9fa73a3"


FINDINGS_TEXT = """
57|CRITICAL|semantic tuple normalizer|Free-text description outranks authoritative S-57 object_class in _category: isolated-danger row claimed as lateral aid with zero unresolved reasons
64|MAJOR|semantic tuple normalizer|Unknown attribute codes yield sentinel strings but tuple_status stays 'complete'; valid S-57 COLPAT code 6 missing from table
71|MAJOR|semantic tuple normalizer|Authoritative BCNSHP beacon-shape codes silently ignored; identical codes produce divergent shapes from free text
78|MAJOR|semantic tuple normalizer|Condition prefixes silently dropped from tuple; dangerous vs non-dangerous wrecks produce identical semantic tuples
85|MAJOR|semantic tuple normalizer|Text-sniffed colour_sequence emitted in hardcoded alias order and deduplicated
92|MAJOR|semantic tuple normalizer|Smoke test exercises none of the risky paths and pins the category bug
99|MINOR|semantic tuple normalizer|Substring heuristics without word boundaries misfire
106|MINOR|semantic tuple normalizer|Bare COLOUR condition falls through to description sniffing and is marked complete
113|INFO|semantic tuple normalizer|build() crashes with bare ValueError when --input is outside the repo root
125|MAJOR|S-101 equivalence resolver|Text-keyword category overrides authoritative object class: BOYISD isolated-danger classified as BuoyLateral
132|MAJOR|S-101 equivalence resolver|Rows with missing required evidence are classified acceptable_deviation
139|MAJOR|S-101 equivalence resolver|Line-style rows with hazard object classes bypass the semantic_only fence
146|MAJOR|S-101 equivalence resolver|Duplicated divergent resolver implementations contradict runtime DB rows
153|MINOR|S-101 equivalence resolver|Test enshrines BOYSPP lookup as BuoyLateral misclassification
160|MINOR|S-101 equivalence resolver|semantic_only branch drops tuple missing-data reasons
172|MAJOR|proof bundle|Unresolved palette tokens are silently masked instead of failing the build
179|MINOR|proof bundle|Test checks only the alphabetically-first SVG per palette for unresolved tokens
186|MINOR|proof bundle|No test that day/dusk/night exports actually differ
193|MINOR|proof bundle|Manifest has no content hashes or file inventory; --no-clean can leave stale files
205|MAJOR|three-way colour authority|Alignment check ignores colour_pattern: orientation conflict labelled aligned
212|MAJOR|three-way colour authority|Visual witness fabricated from feature colours when no standard-source row joins
219|MAJOR|three-way colour authority|Colour-conflict warn does not block runtime eligibility
226|MAJOR|three-way colour authority|Rebuilt DB ships with failing audit check and nothing fails loudly
233|MAJOR|three-way colour authority|Colour-bearing rows labelled not_colour_bearing and gate-passed with zero colour evidence
240|INFO|three-way proof|false_gap metric is degenerate
247|INFO|three-way proof|HTML render crashes with TypeError if proof row has null s52_symbol_id
259|MAJOR|DB augment script|Audit failures never fail the build
265|MAJOR|DB augment script|colour_authority warn does not affect runtime eligibility
271|MAJOR|DB augment script|render_colour_authority=s52_symbol_visual_witness backed by templated semantic_brief
277|MINOR|DB augment script|visual_colour_sequence fabricated by copying feature colours when no witness exists
283|MINOR|DB augment script|In-place rebuild can leave a gutted but valid-looking artifact
294|MAJOR|DB contract|Strict runtime view trusts stored runtime_eligible column with no enforcement tying it to gate rows
301|MAJOR|DB contract|Shipped DB contains a failing audit check and audit() never fails the build
308|MAJOR|DB contract|Working-tree rebuild stale lineage deletes origin/main s52_instruction_ast parser gate
315|MINOR|DB contract|Unresolved feature-vs-visual colour conflicts are only non-blocking warnings
322|MINOR|DB contract|s101_crosswalk_evidence gate passes on any resolved linked asset
328|MINOR|DB contract|authority_status aligned asserted for rows with no independent visual witness
334|MINOR|DB contract|schema.sql contains sqlite_sequence DDL
340|INFO|DB contract|Referential and gate-set integrity relies on per-connection PRAGMA foreign_keys
351|CRITICAL|docs honesty|Entire day's work built on stale base behind canonical origin/main
357|MAJOR|docs honesty|Rebuilt runtime DB ships failing import-audit check while script exits 0
363|MAJOR|docs honesty|colour_authority warn is non-blocking for unresolved correct rendering colour
369|MAJOR|docs honesty|Counsel-review distribution gate and forbidden-source list removed from provenance manifest
375|MINOR|docs honesty|FORGE-22/23 classify BOYSPP special-purpose buoy as lateral
381|MINOR|docs honesty|Committed runtime DB built from uncommitted /private/tmp approval root
387|INFO|docs honesty|Part 2 verification: no new import-time cairosvg dependency; determinism guards intact
398|CRITICAL|plan-board acceptance|Branch is stale parallel lineage that regresses merged FORGE-25 runtime DB contract
404|MAJOR|plan-board acceptance|Rebuilt DB ships failing audit while build exits 0
410|MAJOR|plan-board acceptance|Untracked files collide with newer origin/main files
416|MAJOR|plan-board acceptance|Untracked proof bundle is stale scaffold-era bundle
422|MAJOR|plan-board acceptance|Colour-authority classifier masks rows with no colour evidence as not_colour_bearing
428|MINOR|plan-board acceptance|colour_authority_gate falls through to pass for unhandled status
434|MINOR|plan-board acceptance|Board-claimed colour_authority_warnings.html review page absent
440|MINOR|plan-board acceptance|DB rebuild silently degrades when /private/tmp approval root is missing
446|MINOR|plan-board acceptance|FORGE-24 accepted deliverables not on main; second three-way-proof implementation
452|INFO|plan-board acceptance|Board status of reviewed tasks
""".strip()


@dataclass(frozen=True)
class Finding:
    source_line: int
    severity: str
    area: str
    title: str


def _findings() -> list[Finding]:
    findings: list[Finding] = []
    for raw in FINDINGS_TEXT.splitlines():
        source_line, severity, area, title = raw.split("|", 3)
        findings.append(Finding(int(source_line), severity, area, title))
    return findings


def _run(*args: str) -> str:
    return subprocess.check_output(args, cwd=REPO, text=True).strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _scalar(conn: sqlite3.Connection, sql: str) -> Any:
    return conn.execute(sql).fetchone()[0]


def _pairs(conn: sqlite3.Connection, sql: str) -> dict[str, int]:
    return {str(key): int(count) for key, count in conn.execute(sql).fetchall()}


def _triples(conn: sqlite3.Connection, sql: str) -> dict[str, int]:
    return {"|".join(str(part) for part in row[:-1]): int(row[-1]) for row in conn.execute(sql).fetchall()}


def _current_snapshot() -> dict[str, Any]:
    with sqlite3.connect(DB) as conn:
        return {
            "db": str(DB.relative_to(REPO)),
            "db_sha256": _sha256(DB),
            "integrity_check": _scalar(conn, "PRAGMA integrity_check"),
            "foreign_key_violations": len(conn.execute("PRAGMA foreign_key_check").fetchall()),
            "audit_status_counts": _pairs(
                conn, "SELECT status, count(*) FROM s52_s101_import_audit GROUP BY status ORDER BY status"
            ),
            "runtime_symbol_portrayal_v1_rows": _scalar(conn, "SELECT count(*) FROM runtime_symbol_portrayal_v1"),
            "runtime_candidate_counts": _triples(
                conn,
                """
                SELECT candidate_status, runtime_eligible, count(*)
                FROM runtime_symbol_candidate_v1
                GROUP BY candidate_status, runtime_eligible
                ORDER BY candidate_status, runtime_eligible
                """,
            ),
            "runtime_gate_counts": _triples(
                conn,
                """
                SELECT gate_name, gate_status, count(*)
                FROM runtime_symbol_gate
                GROUP BY gate_name, gate_status
                ORDER BY gate_name, gate_status
                """,
            ),
            "s52_instruction_ast_counts": _pairs(
                conn, "SELECT parse_status, count(*) FROM s52_instruction_ast GROUP BY parse_status ORDER BY parse_status"
            ),
            "source_metadata": {
                row[0]: row[1]
                for row in conn.execute(
                    """
                    SELECT key, value
                    FROM s52_source_metadata
                    WHERE key IN (
                      'source_git_sha',
                      'chartsymbols_sha256',
                      'runtime_contract',
                      's101_mapping_type_counts',
                      'semantic_tuple_status_counts',
                      's52_instruction_ast_status_counts'
                    )
                    ORDER BY key
                    """
                ).fetchall()
            },
            "spot_checks": {
                "BOYISD_BOYCON77": conn.execute(
                    """
                    SELECT object_class, s52_symbol_id, s101_feature_type, s101_attributes
                    FROM runtime_symbol_candidate_v1
                    WHERE row_key LIKE 'BOYISD_BOYCON77%'
                    LIMIT 1
                    """
                ).fetchone(),
                "BOYSPP_BOYCAN60": conn.execute(
                    """
                    SELECT object_class, s52_symbol_id, s101_feature_type, s101_attributes
                    FROM runtime_symbol_candidate_v1
                    WHERE row_key LIKE 'BOYSPP_BOYCAN60%'
                    LIMIT 1
                    """
                ).fetchone(),
            },
        }


def _classify(finding: Finding) -> dict[str, str]:
    line = finding.source_line
    title = finding.title.lower()

    if line <= 160:
        if "boyisd" in title or "boyssp" in title or "boysp" in title or "lateral" in title:
            return {
                "classification": "already_fixed_current_main",
                "current_status": "not reproduced in current runtime DB",
                "evidence": "Current DB maps BOYISD/BOYCON77 to BuoyIsolatedDanger and BOYSPP/BOYCAN60 to BuoySpecialPurposeGeneral; stale semantic_tuple_normalizer.py and s101_equivalence_resolver.py are not present on origin/main.",
                "next_action": "none for the stale module; keep validating through the runtime DB/electronic Chart 1 proof.",
            }
        return {
            "classification": "superseded_by_current_main",
            "current_status": "stale module finding",
            "evidence": "Current origin/main uses scripts/augment-opencpn-s52-s101-semantics.py plus runtime DB gates; the reviewed semantic_tuple_normalizer.py/s101_equivalence_resolver.py lineage is absent.",
            "next_action": "do not revive stale module; express any remaining semantic issue as a DB gate/audit test.",
        }

    if line in {172, 179, 186, 193}:
        return {
            "classification": "still_current_followup",
            "current_status": "proof-bundle hardening remains useful",
            "evidence": "Current proof_bundle.py still leaves unresolved CSS var() tokens unchanged and the manifest still lacks per-file content hashes.",
            "next_action": "carry into clean-public-package/proof-bundle hardening: fail unresolved palette tokens, test all exports, add sha256 inventory.",
        }

    if line in {205, 315, 322, 328, 422, 428}:
        return {
            "classification": "partially_current_hardening",
            "current_status": "runtime remains blocked; contract can be stricter",
            "evidence": "Current authority_trace_gate blocks all 3057 runtime rows, but colour_authority_contract still has warning/pass classes that should be resolved before runtime promotion.",
            "next_action": "tighten FORGE runtime promotion/colour-authority gates so warn or missing witness cannot become runtime eligible without recorded resolution.",
        }

    if line in {212, 233, 271, 277}:
        return {
            "classification": "already_fixed_or_replaced",
            "current_status": "old DB-layer mechanism replaced",
            "evidence": "Current colour_authority_contract reads generated SVG recipes directly and has explicit unresolved/pending cases for missing SVG or missing visual sequence; authority_trace still blocks runtime.",
            "next_action": "keep authority trace as the runtime blocker; add focused tests for rows with no independent witness.",
        }

    if line in {219, 265, 363}:
        return {
            "classification": "partially_current_hardening",
            "current_status": "not a current runtime escape, but policy needs tightening",
            "evidence": "runtime_symbol_portrayal_v1 has 0 rows and authority_trace blocks every runtime row; however warn is still an allowed colour-authority gate value in promotion code.",
            "next_action": "make runtime promotion require explicit colour-authority resolution, not pass-or-warn.",
        }

    if line in {226, 259, 301, 357, 404}:
        return {
            "classification": "already_fixed_current_main",
            "current_status": "current DB audit is green",
            "evidence": "Current artifacts/opencpn_s52_portrayal.sqlite has s52_s101_import_audit pass|27 and runtime_symbol_portrayal_v1 count 0.",
            "next_action": "keep audit all-pass in CI; do not merge stale DB artifacts.",
        }

    if line in {240, 247, 446}:
        return {
            "classification": "superseded_by_current_main",
            "current_status": "old three_way_proof path replaced",
            "evidence": "Current main uses standards_three_way_proof.py and DB-backed review surfaces; stale three_way_proof.py is absent.",
            "next_action": "do not reintroduce the old three_way_proof.py path.",
        }

    if line in {283, 294, 334, 340, 381, 440}:
        return {
            "classification": "still_current_followup",
            "current_status": "tooling/contract hardening still relevant",
            "evidence": "Current augment script writes the DB in place, schema.sql includes sqlite_sequence, and the default approval root remains /private/tmp based.",
            "next_action": "build DB through atomic temp output, enforce required evidence roots, and make replayable schema artifacts clean.",
        }

    if line in {308, 351, 398, 410, 416}:
        return {
            "classification": "confirmed_source_context_not_current_main",
            "current_status": "true of stale source checkout, not fresh FORGE-48 branch",
            "evidence": "FORGE-48 was created from fresh origin/main; the stale source branch was behind and dirty, but this worktree starts from current main evidence.",
            "next_action": "leave stale branch unmerged; use this ledger as the reconciliation artifact.",
        }

    if line in {369}:
        return {
            "classification": "requires_policy_followup",
            "current_status": "not resolved by this ledger",
            "evidence": "Clean-IP/counsel boundary is policy-critical and should be audited against the public package contract, not inferred from stale branch diffs.",
            "next_action": "include explicit clean-IP forbidden-source and counsel-review gates in the public symbol package checklist.",
        }

    if line in {375}:
        return {
            "classification": "already_fixed_current_main",
            "current_status": "not reproduced in current runtime DB",
            "evidence": "BOYSPP/BOYCAN60 is currently rule-derived as BuoySpecialPurposeGeneral with category_of_special_purpose_mark evidence, not BuoyLateral.",
            "next_action": "none beyond keeping the DB spot check in future conformance tests.",
        }

    if line in {387, 452}:
        return {
            "classification": "informational",
            "current_status": "context recorded",
            "evidence": "No code defect asserted in this finding; keep as lineage and environment context.",
            "next_action": "none.",
        }

    if line == 434:
        return {
            "classification": "already_fixed_or_replaced",
            "current_status": "current backend review pages include colour authority fields",
            "evidence": "human_review_page.py and db_review_api.py expose colour_authority and authority_trace from backend payloads; no static colour_authority_warnings.html is needed.",
            "next_action": "continue the backend-first Tabler cleanup rather than restoring a stale static page.",
        }

    return {
        "classification": "reviewed_no_separate_action",
        "current_status": "covered by adjacent current finding",
        "evidence": "This stale-audit item duplicates another source finding and is addressed by the same current disposition.",
        "next_action": "track the grouped action, not a duplicate task.",
    }


def _payload() -> dict[str, Any]:
    findings = _findings()
    snapshot = _current_snapshot()
    rows = []
    for index, finding in enumerate(findings, start=1):
        row = {
            "id": f"F48-{index:03d}",
            "source_line": finding.source_line,
            "source_severity": finding.severity,
            "area": finding.area,
            "title": finding.title,
        }
        row.update(_classify(finding))
        rows.append(row)

    counts = Counter(row["classification"] for row in rows)
    head, origin_main = _run("git", "rev-parse", "HEAD", "origin/main").splitlines()
    ahead, behind = _run("git", "rev-list", "--left-right", "--count", "HEAD...origin/main").split()
    source_sha = _sha256(SOURCE_AUDIT) if SOURCE_AUDIT.exists() else SOURCE_AUDIT_SHA256
    return {
        "schema": "helm.iconforge.forge48_current_findings_ledger.v1",
        "task": "FORGE-48",
        "status": "current_findings_ledger_ready",
        "source_audit": {
            "path": str(SOURCE_AUDIT),
            "sha256": source_sha,
            "line_count": len(SOURCE_AUDIT.read_text().splitlines()) if SOURCE_AUDIT.exists() else None,
        },
        "git": {
            "branch": _run("git", "branch", "--show-current"),
            "head": head,
            "origin_main": origin_main,
            "ahead": int(ahead),
            "behind": int(behind),
        },
        "current_snapshot": snapshot,
        "summary": {
            "finding_count": len(rows),
            "classification_counts": dict(sorted(counts.items())),
            "strict_runtime_rows": snapshot["runtime_symbol_portrayal_v1_rows"],
            "db_audit_status_counts": snapshot["audit_status_counts"],
        },
        "findings": rows,
    }


def _md(payload: dict[str, Any]) -> str:
    lines = [
        "# FORGE-48 current findings ledger",
        "",
        "This reconciles the stale FORGE-24/25 audit against the current fresh `origin/main` runtime DB.",
        "",
        "## Current evidence",
        "",
        f"- Source audit sha256: `{payload['source_audit']['sha256']}`",
        f"- Branch: `{payload['git']['branch']}`",
        f"- HEAD: `{payload['git']['head']}`",
        f"- origin/main: `{payload['git']['origin_main']}`",
        f"- Ahead/behind origin/main at generation: `{payload['git']['ahead']}/{payload['git']['behind']}`",
        f"- DB integrity: `{payload['current_snapshot']['integrity_check']}`",
        f"- DB foreign-key violations: `{payload['current_snapshot']['foreign_key_violations']}`",
        f"- DB audit statuses: `{json.dumps(payload['current_snapshot']['audit_status_counts'], sort_keys=True)}`",
        f"- Strict runtime rows: `{payload['current_snapshot']['runtime_symbol_portrayal_v1_rows']}`",
        f"- S-52 instruction AST: `{json.dumps(payload['current_snapshot']['s52_instruction_ast_counts'], sort_keys=True)}`",
        f"- Runtime candidates: `{json.dumps(payload['current_snapshot']['runtime_candidate_counts'], sort_keys=True)}`",
        "",
        "## Summary",
        "",
    ]
    for key, value in payload["summary"]["classification_counts"].items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(
        [
            "",
            "## Ledger",
            "",
            "| ID | Source | Severity | Area | Current classification | Finding | Evidence | Next action |",
            "| --- | ---: | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in payload["findings"]:
        lines.append(
            "| {id} | {source_line} | {source_severity} | {area} | `{classification}` | {title} | {evidence} | {next_action} |".format(
                **{k: str(v).replace("|", "\\|").replace("\n", " ") for k, v in row.items()}
            )
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    CATALOG.mkdir(parents=True, exist_ok=True)
    payload = _payload()
    OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    OUT_MD.write_text(_md(payload))
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
