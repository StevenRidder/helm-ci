"""Forge file ownership and generated-artifact policy.

Run:
  python3 -m forge.file_ownership_policy --write
  python3 -m forge.file_ownership_policy --check
  python3 -m forge.file_ownership_policy --check-handoff
  python3 -m forge.file_ownership_policy claim --task-id FORGE-52 --agent-id codex/FORGE-52 --paths pipeline/iconforge/README.md
"""
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path
from typing import Any


# file_ownership_policy.py lives in pipeline/iconforge/forge/.
ROOT = Path(__file__).resolve().parents[3]
ICONFORGE = ROOT / "pipeline" / "iconforge"
CATALOG = ICONFORGE / "catalog"
OUT = ICONFORGE / "out"
REPORT_JSON = CATALOG / "file_ownership_policy.json"
REPORT_MD = CATALOG / "file_ownership_policy.md"
CLAIMS_DIR = OUT / "file_ownership_claims"

SCHEMA = "helm.iconforge.file_ownership_policy.v1"

SOURCE_PATHS = [
    "pipeline/iconforge/README.md",
    "pipeline/iconforge/SPEC-0001-clean-room-symbol-package.md",
    "pipeline/iconforge/AGENT-BRIEF.md",
    "pipeline/iconforge/CONTEXT-THREAD.md",
    "pipeline/iconforge/.gitignore",
    "pipeline/iconforge/forge/**",
    "pipeline/iconforge/fixtures/**",
    "pipeline/iconforge/pilots/**",
    "pipeline/iconforge/stylepacks/**",
    "scripts/augment-opencpn-s52-s101-semantics.py",
]

GENERATED_TRACKED_PATHS = [
    "pipeline/iconforge/assets/svg/**",
    "pipeline/iconforge/catalog/**",
    "pipeline/iconforge/generated/**",
    "pipeline/iconforge/proof/**",
    "pipeline/iconforge/registry/**",
    "pipeline/iconforge/samples/**",
    "pipeline/iconforge/symbols.yaml",
    "artifacts/opencpn_s52_portrayal.schema.sql",
    "artifacts/opencpn_s52_portrayal.sqlite",
]

REFERENCE_TRACKED_PATHS = [
    "pipeline/iconforge/reference_sources/**",
]

REVIEW_ONLY_OUTPUT_PATHS = [
    "pipeline/iconforge/out/**",
]

AGENT_PRIVATE_PATHS = [
    "pipeline/iconforge/.cache/**",
    "pipeline/iconforge/.agent-scratch/**",
    "pipeline/iconforge/tmp/**",
]

TRACKED_ROOTS = [
    "pipeline/iconforge",
    "artifacts/opencpn_s52_portrayal.schema.sql",
    "artifacts/opencpn_s52_portrayal.sqlite",
    "scripts/augment-opencpn-s52-s101-semantics.py",
]


def _stable_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _repo_rel(path: str | Path) -> str:
    text = Path(path).as_posix()
    if text.startswith("./"):
        text = text[2:]
    return text


def _matches(path: str, patterns: list[str]) -> bool:
    return any(fnmatch(path, pattern) for pattern in patterns)


def classify_path(path: str | Path) -> dict[str, Any]:
    rel = _repo_rel(path)
    if _matches(rel, AGENT_PRIVATE_PATHS):
        return {
            "path": rel,
            "class": "agent_private_scratch",
            "disposition": "ignored",
            "owner": "one agent/session only",
            "claim_required": False,
            "tracked_allowed": False,
        }
    if _matches(rel, REVIEW_ONLY_OUTPUT_PATHS):
        return {
            "path": rel,
            "class": "review_only_output",
            "disposition": "ignored_or_archived",
            "owner": "producing task only; cite summaries in board evidence",
            "claim_required": True,
            "tracked_allowed": False,
        }
    if _matches(rel, REFERENCE_TRACKED_PATHS):
        return {
            "path": rel,
            "class": "reference_evidence_tracked",
            "disposition": "tracked_reference_only",
            "owner": "source-intake/provenance tasks",
            "claim_required": True,
            "tracked_allowed": True,
        }
    if _matches(rel, GENERATED_TRACKED_PATHS):
        return {
            "path": rel,
            "class": "generated_tracked",
            "disposition": "tracked_with_reprovenance",
            "owner": "named generator/audit task",
            "claim_required": True,
            "tracked_allowed": True,
        }
    if _matches(rel, SOURCE_PATHS):
        return {
            "path": rel,
            "class": "source_contract",
            "disposition": "tracked_source",
            "owner": "task that owns the code/doc contract",
            "claim_required": True,
            "tracked_allowed": True,
        }
    return {
        "path": rel,
        "class": "unknown",
        "disposition": "ambiguous",
        "owner": "unclaimed",
        "claim_required": True,
        "tracked_allowed": False,
    }


def _git_lines(args: list[str]) -> list[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return [line for line in result.stdout.splitlines() if line]


def tracked_files() -> list[str]:
    return _git_lines(["ls-files", *TRACKED_ROOTS])


def untracked_files() -> list[str]:
    out: list[str] = []
    for line in _git_lines(["status", "--porcelain", "--", *TRACKED_ROOTS]):
        if line.startswith("?? "):
            out.append(line[3:])
    return out


def build_policy() -> dict[str, Any]:
    tracked = tracked_files()
    rows = [classify_path(path) for path in tracked]
    unknown = [row for row in rows if row["class"] == "unknown"]
    untracked = untracked_files()
    return {
        "schema": SCHEMA,
        "status": "blocked" if unknown or untracked else "pass",
        "policy": {
            "source_contract": SOURCE_PATHS,
            "generated_tracked": GENERATED_TRACKED_PATHS,
            "reference_evidence_tracked": REFERENCE_TRACKED_PATHS,
            "review_only_output": REVIEW_ONLY_OUTPUT_PATHS,
            "agent_private_scratch": AGENT_PRIVATE_PATHS,
        },
        "rules": [
            "Every Forge worker must claim intended write paths before modifying tracked generated or source-contract files.",
            "Review-only outputs under pipeline/iconforge/out/ are ignored by Git; summarize them in board evidence or promote them through an explicit generator if they must be tracked.",
            "Generated tracked artifacts must be reproducible from a named forge module or carry provenance in an adjacent JSON/Markdown report.",
            "Reference-source assets are comparison/provenance evidence only and must not become canonical Helm artwork without a clean-IP task.",
            "A handoff must not contain untracked files under Forge-controlled roots; stage intentional files, ignore scratch outputs, or delete them before complete_claim.",
        ],
        "summary": {
            "tracked_files": len(tracked),
            "unknown_tracked_files": len(unknown),
            "untracked_handoff_files": len(untracked),
            "classes": {
                name: sum(1 for row in rows if row["class"] == name)
                for name in sorted({row["class"] for row in rows})
            },
        },
        "unknown_tracked_files": unknown,
        "untracked_handoff_files": [
            {**classify_path(path), "handoff_issue": "untracked_file_under_forge_controlled_root"}
            for path in untracked
        ],
    }


def write_reports(payload: dict[str, Any]) -> None:
    CATALOG.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(_stable_json(payload))
    lines = [
        "# Forge File Ownership Policy",
        "",
        f"- schema: `{payload['schema']}`",
        f"- status: `{payload['status']}`",
        f"- tracked files classified: `{payload['summary']['tracked_files']}`",
        f"- unknown tracked files: `{payload['summary']['unknown_tracked_files']}`",
        f"- untracked handoff files: `{payload['summary']['untracked_handoff_files']}`",
        "",
        "## Classes",
        "",
        "| Class | Count | Disposition |",
        "| --- | ---: | --- |",
    ]
    dispositions = {
        "agent_private_scratch": "ignored",
        "generated_tracked": "tracked with reproducible/provenance evidence",
        "reference_evidence_tracked": "tracked reference-only evidence",
        "review_only_output": "ignored or archived outside the handoff",
        "source_contract": "tracked source",
        "unknown": "blocked",
    }
    for name, count in payload["summary"]["classes"].items():
        lines.append(f"| `{name}` | {count} | {dispositions.get(name, 'blocked')} |")
    lines.extend([
        "",
        "## Rules",
        "",
    ])
    lines.extend(f"- {rule}" for rule in payload["rules"])
    REPORT_MD.write_text("\n".join(lines) + "\n")


def write_claim(*, task_id: str, agent_id: str, paths: list[str]) -> dict[str, Any]:
    rows = [classify_path(path) for path in paths]
    claim = {
        "schema": "helm.iconforge.file_write_claim.v1",
        "task_id": task_id,
        "agent_id": agent_id,
        "claimed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "paths": rows,
        "status": "blocked" if any(row["class"] == "unknown" for row in rows) else "claimed",
    }
    CLAIMS_DIR.mkdir(parents=True, exist_ok=True)
    safe_task = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in task_id)
    (CLAIMS_DIR / f"{safe_task}.json").write_text(_stable_json(claim))
    return claim


def validate_tracked_coverage(payload: dict[str, Any]) -> None:
    if payload["unknown_tracked_files"]:
        paths = ", ".join(row["path"] for row in payload["unknown_tracked_files"][:10])
        raise SystemExit(f"unclassified tracked Forge files: {paths}")


def validate_handoff(payload: dict[str, Any]) -> None:
    validate_tracked_coverage(payload)
    if payload["untracked_handoff_files"]:
        paths = ", ".join(row["path"] for row in payload["untracked_handoff_files"][:10])
        raise SystemExit(f"untracked Forge handoff files must be staged, ignored, or removed: {paths}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write catalog/file_ownership_policy reports")
    parser.add_argument("--check", action="store_true", help="fail if tracked Forge files are unclassified")
    parser.add_argument("--check-handoff", action="store_true", help="also fail on untracked Forge-controlled files")
    sub = parser.add_subparsers(dest="command")
    claim = sub.add_parser("claim", help="record a pre-write path claim under out/file_ownership_claims/")
    claim.add_argument("--task-id", required=True)
    claim.add_argument("--agent-id", required=True)
    claim.add_argument("--paths", nargs="+", required=True)
    args = parser.parse_args(argv)

    if args.command == "claim":
        payload = write_claim(task_id=args.task_id, agent_id=args.agent_id, paths=args.paths)
        print(_stable_json(payload), end="")
        return 0 if payload["status"] == "claimed" else 2

    payload = build_policy()
    if args.write:
        write_reports(payload)
    if args.check_handoff:
        validate_handoff(payload)
    elif args.check:
        validate_tracked_coverage(payload)
    print(_stable_json({
        "status": payload["status"],
        "summary": payload["summary"],
        "json": REPORT_JSON.relative_to(ICONFORGE).as_posix(),
        "markdown": REPORT_MD.relative_to(ICONFORGE).as_posix(),
    }), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
