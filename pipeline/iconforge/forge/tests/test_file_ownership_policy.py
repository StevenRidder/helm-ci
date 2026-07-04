"""Smoke the Forge file ownership policy.

Run:  python3 -m forge.tests.test_file_ownership_policy
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from .. import file_ownership_policy


def _class(path: str) -> str:
    return file_ownership_policy.classify_path(path)["class"]


def main() -> None:
    payload = file_ownership_policy.build_policy()
    assert payload["schema"] == "helm.iconforge.file_ownership_policy.v1"
    assert payload["summary"]["tracked_files"] > 1000
    assert payload["unknown_tracked_files"] == []
    assert "source_contract" in payload["summary"]["classes"]
    assert "generated_tracked" in payload["summary"]["classes"]
    assert "reference_evidence_tracked" in payload["summary"]["classes"]
    assert "review_only_output" in payload["summary"]["classes"]

    assert _class("pipeline/iconforge/forge/file_ownership_policy.py") == "source_contract"
    assert _class("pipeline/iconforge/catalog/runtime_evidence_snapshot.json") == "generated_tracked"
    assert _class("pipeline/iconforge/proof/index.html") == "generated_tracked"
    assert (
        _class("pipeline/iconforge/reference_sources/openbridge_webcomponents/svg/beacon-default.svg")
        == "reference_evidence_tracked"
    )
    assert _class("pipeline/iconforge/out/human_review/icon_review.html") == "review_only_output"
    assert _class("pipeline/iconforge/.agent-scratch/FORGE-52/tmp.json") == "agent_private_scratch"
    assert _class("pipeline/iconforge/random-new-output.json") == "unknown"

    with tempfile.TemporaryDirectory() as tmp:
        old_claims_dir = file_ownership_policy.CLAIMS_DIR
        try:
            file_ownership_policy.CLAIMS_DIR = Path(tmp) / "claims"
            claim = file_ownership_policy.write_claim(
                task_id="FORGE-52",
                agent_id="codex/FORGE-52-file-ownership",
                paths=[
                    "pipeline/iconforge/README.md",
                    "pipeline/iconforge/catalog/file_ownership_policy.json",
                ],
            )
        finally:
            file_ownership_policy.CLAIMS_DIR = old_claims_dir
    assert claim["schema"] == "helm.iconforge.file_write_claim.v1"
    assert claim["status"] == "claimed"
    assert {row["class"] for row in claim["paths"]} == {"source_contract", "generated_tracked"}

    try:
        file_ownership_policy.validate_tracked_coverage(payload)
    except SystemExit as exc:
        raise AssertionError(str(exc)) from exc

    print("file ownership policy: OK")


if __name__ == "__main__":
    main()
