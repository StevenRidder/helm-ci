"""Smoke Standard Repair Batch 24.

Run:  python3 -m forge.tests.test_standard_repair_batch24
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch24


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch32.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch24.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 11
    assert not result["blockers"]

    repaired = {row["asset"] for row in result["symbols"]}
    assert repaired == set(standard_repair_batch24.REPAIRS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}
    assert {row["qa"]["final_approved"] for row in result["symbols"]} == {False}

    default = _svg("BCNDEF13", result)
    assert "var(--gray)" in default
    assert ">?</text>" in default
    assert '<rect x="15" y="8"' in default

    pile = _svg("BCNGEN01", result)
    assert "M31 10 V50" in pile
    assert "var(--blue)" in pile
    assert ">?</text>" not in pile

    pile_question = _svg("BCNGEN03", result)
    assert "M31 10 V50" in pile_question
    assert ">?</text>" in pile_question

    isolated = _svg("BCNISD21", result)
    assert isolated.count("<circle") == 2
    assert "var(--red)" in isolated

    lattice = _svg("BCNLTC01", result)
    assert "M17 54 L24 13 H40 L47 54 Z" in lattice
    assert "M23 20 L41 28" in lattice

    safe_major = _svg("BCNSAW13", result)
    assert '<rect x="22" y="8"' in safe_major
    assert "var(--black)" in safe_major
    assert "var(--blue)" in safe_major

    safe_minor = _svg("BCNSAW21", result)
    assert '<rect x="27" y="10" width="10"' in safe_minor
    assert "var(--blue)" in safe_minor

    special_major = _svg("BCNSPP13", result)
    assert "var(--yellow)" in special_major
    assert '<rect x="20" y="10"' in special_major

    special_minor = _svg("BCNSPP21", result)
    assert "var(--yellow)" in special_minor
    assert '<rect x="27" y="10" width="11"' in special_minor

    stake = _svg("BCNSTK02", result)
    assert "M32 12 V53 M18 53 H46" in stake

    tower = _svg("BCNTOW01", result)
    assert "M17 55 L25 13 H39 L47 55" in tower
    assert '<circle cx="32" cy="55"' in tower

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 11
    assert (ROOT / "catalog" / "owned_repair_batch32.md").exists()
    print("standard repair batch 24: OK")


if __name__ == "__main__":
    main()
