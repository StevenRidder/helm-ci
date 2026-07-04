"""Smoke Standard Repair Batch 58.

Run:  python3 -m forge.tests.test_standard_repair_batch58
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch58


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch66.json"


def _svg(result: dict) -> str:
    return (ROOT / result["symbols"][0]["after_svg"]).read_text()


def main():
    result = standard_repair_batch58.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 1
    assert not result["blockers"]
    assert result["symbols"][0]["asset"] == "TOPSHQ31"
    assert result["symbols"][0]["source_judge"] == "catalog/standard_judge_batch_064_rerun.json"
    assert len(result["symbols"][0]["after_renders"]) == 3

    svg = _svg(result)
    assert 'data-repair-batch="standard-repair-batch58"' in svg
    assert 'points="32,10 45,24 32,38 19,24"' in svg
    assert 'data-shape="lozenge-top"' in svg
    assert '<circle cx="32" cy="45" r="12"' in svg
    assert 'data-shape="lower-circle"' in svg
    assert "generated-owned-artwork" in svg

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 1
    assert (ROOT / "catalog" / "owned_repair_batch66.md").exists()
    print("standard repair batch 58: OK")


if __name__ == "__main__":
    main()
