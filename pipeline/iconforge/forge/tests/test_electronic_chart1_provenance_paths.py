"""Verify Electronic Chart 1 source provenance is portable and hash-checked.

Run:
  python3 -m forge.tests.test_electronic_chart1_provenance_paths
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = ROOT.parent.parent
CATALOG = ROOT / "catalog"
FORBIDDEN_PATH_TOKENS = (
    "/private/tmp/",
    "/Users/steveridder/",
)
ARTIFACTS = (
    "electronic_chart1_contract.json",
    "electronic_chart1_authority_corpus.json",
    "electronic_chart1_diff_engine.json",
    "electronic_chart1_proof_bundle.json",
    "electronic_chart1_runtime_promotion_gate.json",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve(path_value: str) -> Path:
    candidate = Path(path_value)
    assert not candidate.is_absolute(), f"absolute provenance path: {path_value}"
    assert not any(token in path_value for token in FORBIDDEN_PATH_TOKENS), path_value
    for base in (REPO_ROOT, ROOT):
        resolved = (base / candidate).resolve()
        if resolved.exists():
            return resolved
    raise AssertionError(f"missing provenance source path: {path_value}")


def _hash_target(path_value: str, resolved: Path) -> Path:
    if resolved.is_dir() and path_value.endswith("out/electronic_chart1_proof_bundle"):
        return resolved / "manifest.json"
    return resolved


def _check_path_hash(path_value: str, expected_sha: str) -> None:
    resolved = _resolve(path_value)
    target = _hash_target(path_value, resolved)
    assert target.is_file(), f"cannot hash provenance source: {path_value}"
    assert _sha256(target) == expected_sha, f"stale provenance hash for {path_value}"


def _walk_source(value: Any) -> None:
    if isinstance(value, dict):
        if "path" in value and "sha256" in value:
            _check_path_hash(str(value["path"]), str(value["sha256"]))
        if "db_path" in value and "db_sha256" in value:
            _check_path_hash(str(value["db_path"]), str(value["db_sha256"]))
        for child in value.values():
            _walk_source(child)
    elif isinstance(value, list):
        for child in value:
            _walk_source(child)


def main() -> None:
    for name in ARTIFACTS:
        payload = json.loads((CATALOG / name).read_text())
        source = payload.get("source") or {}
        if name == "electronic_chart1_runtime_promotion_gate.json":
            proof_bundle_sha256 = source["proof_bundle"]["sha256"]
            runtime_source_hashes = (payload.get("runtime_export") or {}).get("source_hashes") or {}
            assert runtime_source_hashes["proof_manifest_sha256"] == proof_bundle_sha256
            source = {
                "proof_bundle": source["proof_bundle"],
                "upstream_sources": source["upstream_sources"],
            }
        _walk_source(source)

    print("electronic Chart 1 provenance paths: OK")


if __name__ == "__main__":
    main()
