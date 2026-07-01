#!/usr/bin/env python3
"""Validate Helm's HELMC++ runtime inventory.

This is intentionally a small stdlib-only guard. It does not prove the C++ port
is complete; it prevents the opposite mistake: silently classifying a Python
daemon as required boat-side runtime.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


DEFAULT_INVENTORY = Path("docs/runtime-inventory.json")
ALLOWED_CLASSIFICATIONS = {
    "required-runtime",
    "transitional-reference",
    "dev-tooling",
    "fixture/test",
    "offline-bake",
    "optional-non-safety",
    "removed",
}
PYTHON_RUNTIME_RE = re.compile(r"\b(python3?|uvicorn|fastapi|FastAPI)\b")


def fail(errors: list[str], entry_id: str, message: str) -> None:
    errors.append(f"{entry_id}: {message}")


def as_bool(value: Any) -> bool:
    return bool(value) if isinstance(value, bool) else False


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def path_matches(repo_root: Path, pattern: str) -> list[Path]:
    if any(ch in pattern for ch in "*?["):
        return [Path(p) for p in glob.glob(str(repo_root / pattern))]
    p = repo_root / pattern
    return [p] if p.exists() else []


def validate_entry(repo_root: Path, entry: dict[str, Any], errors: list[str]) -> None:
    entry_id = str(entry.get("id", "<missing-id>"))
    classification = entry.get("classification")
    status = entry.get("status")
    language = str(entry.get("language", ""))
    required_runtime = as_bool(entry.get("required_runtime"))
    final_required = as_bool(entry.get("final_acceptance_required"))
    starts_python = as_bool(entry.get("starts_python_daemon"))
    python_allowed = as_bool(entry.get("python_allowed"))
    launch = [str(x) for x in as_list(entry.get("launch"))]
    paths = [str(x) for x in as_list(entry.get("paths"))]

    if not entry.get("id"):
        fail(errors, entry_id, "missing id")
    if classification not in ALLOWED_CLASSIFICATIONS:
        fail(errors, entry_id, f"invalid classification {classification!r}")
    if status not in {"implemented", "planned", "removed"}:
        fail(errors, entry_id, f"invalid status {status!r}")
    if not paths:
        fail(errors, entry_id, "must list at least one path")
    for pattern in paths:
        if not path_matches(repo_root, pattern):
            fail(errors, entry_id, f"path pattern does not match anything: {pattern}")

    launch_text = "\n".join(launch)
    launch_mentions_python = bool(PYTHON_RUNTIME_RE.search(launch_text))
    language_mentions_python = "python" in language.lower() or "fastapi" in language.lower()

    if required_runtime and classification != "required-runtime":
        fail(errors, entry_id, "required_runtime entries must use classification=required-runtime")
    if classification == "required-runtime" and status == "implemented":
        if not required_runtime:
            fail(errors, entry_id, "implemented required-runtime entries must set required_runtime=true")
        if "c++" not in language.lower() and "cpp" not in language.lower():
            fail(errors, entry_id, "implemented required runtime must be C++")
        if starts_python or python_allowed or launch_mentions_python or language_mentions_python:
            fail(errors, entry_id, "required runtime must not launch or allow Python/FastAPI/uvicorn")
    if classification == "required-runtime" and status == "planned":
        if not final_required:
            fail(errors, entry_id, "planned required runtime must set final_acceptance_required=true")
        if not entry.get("cxx_exit_task"):
            fail(errors, entry_id, "planned required runtime must name the C++ exit task")

    python_surface = starts_python or language_mentions_python or launch_mentions_python
    if python_surface:
        if classification == "required-runtime":
            fail(errors, entry_id, "Python/FastAPI/uvicorn surface cannot be required-runtime")
        if not python_allowed:
            fail(errors, entry_id, "Python surface must set python_allowed=true with a reason")
        if not entry.get("allowed_python_reason"):
            fail(errors, entry_id, "Python surface must explain allowed_python_reason")
        if classification == "transitional-reference" and not entry.get("cxx_exit_task"):
            fail(errors, entry_id, "transitional Python reference must name cxx_exit_task")
        if classification == "optional-non-safety" and not as_bool(entry.get("optional_non_safety")):
            fail(errors, entry_id, "optional Python service must set optional_non_safety=true")

    if final_required and classification != "required-runtime":
        fail(errors, entry_id, "final_acceptance_required is only valid for required-runtime entries")
    if classification == "removed" and status != "removed":
        fail(errors, entry_id, "removed classification must use status=removed")
    if not as_list(entry.get("feeds_helmcxx")):
        fail(errors, entry_id, "must list which HELMC++ task(s) consume this entry")


def validate_inventory(repo_root: Path, inventory_path: Path) -> tuple[list[str], dict[str, Any]]:
    data = json.loads(inventory_path.read_text(encoding="utf-8"))
    errors: list[str] = []

    if data.get("schema") != "helm.runtime_inventory.v1":
        errors.append("inventory: schema must be helm.runtime_inventory.v1")
    declared = set(as_list(data.get("classifications")))
    if declared != ALLOWED_CLASSIFICATIONS:
        errors.append(
            "inventory: classifications must match "
            + ", ".join(sorted(ALLOWED_CLASSIFICATIONS))
        )
    entries = as_list(data.get("entries"))
    if not entries:
        errors.append("inventory: entries must be a non-empty list")

    seen: set[str] = set()
    required_implemented = 0
    python_non_required = 0
    for raw_entry in entries:
        if not isinstance(raw_entry, dict):
            errors.append("inventory: every entry must be an object")
            continue
        entry_id = str(raw_entry.get("id", "<missing-id>"))
        if entry_id in seen:
            errors.append(f"{entry_id}: duplicate id")
        seen.add(entry_id)
        validate_entry(repo_root, raw_entry, errors)
        if raw_entry.get("classification") == "required-runtime" and raw_entry.get("status") == "implemented":
            required_implemented += 1
        if as_bool(raw_entry.get("starts_python_daemon")) and raw_entry.get("classification") != "required-runtime":
            python_non_required += 1

    if required_implemented == 0:
        errors.append("inventory: must include at least one implemented required-runtime entry")
    if python_non_required == 0:
        errors.append("inventory: expected explicit non-required Python classifications")

    return errors, data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--inventory",
        default=str(DEFAULT_INVENTORY),
        help="inventory path relative to the repo root (default: docs/runtime-inventory.json)",
    )
    args = parser.parse_args()

    repo_root = Path.cwd()
    inventory_path = repo_root / args.inventory
    if not inventory_path.exists():
        print(f"runtime inventory missing: {inventory_path}", file=sys.stderr)
        return 2

    try:
        errors, data = validate_inventory(repo_root, inventory_path)
    except json.JSONDecodeError as exc:
        print(f"invalid JSON in {inventory_path}: {exc}", file=sys.stderr)
        return 2

    if errors:
        print("HELMC++ runtime inventory guard: FAIL", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    entries = data.get("entries", [])
    required = [
        e for e in entries
        if e.get("classification") == "required-runtime" and e.get("status") == "implemented"
    ]
    transitional = [e for e in entries if e.get("classification") == "transitional-reference"]
    optional = [e for e in entries if e.get("classification") == "optional-non-safety"]
    print("HELMC++ runtime inventory guard: PASS")
    print(f"  entries: {len(entries)}")
    print(f"  implemented required C++ runtime: {len(required)}")
    print(f"  transitional references/oracles: {len(transitional)}")
    print(f"  optional non-safety services: {len(optional)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
