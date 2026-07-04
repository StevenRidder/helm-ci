"""Smoke Standard Repair Batch 42.

Run:  python3 -m forge.tests.test_standard_repair_batch42
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch42


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch50.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch42.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == len(standard_repair_batch42.REPAIRS)
    assert result["summary"]["failed_repaired"] == 27
    assert not result["blockers"]
    assert {row["asset"] for row in result["symbols"]} == set(standard_repair_batch42.REPAIRS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}

    assert 'data-repair-batch="standard-repair-batch42"' in _svg("TOPSHP76", result)
    assert 'points="24,10 52,18 40,54 12,46"' in _svg("TOPSHP76", result)
    assert 'clip_TOPSHP76' in _svg("TOPSHP76", result)
    assert 'fill="var(--yellow)"' in _svg("TOPSHP78", result)
    assert 'fill="var(--orange)"' in _svg("TOPSHP79", result)
    assert 'fill="var(--black)"' in _svg("TOPSHP82", result)
    assert 'y="32.0"' in _svg("TOPSHP84", result)
    assert 'clip_TOPSHP81_TE_s' in _svg("TOPSHP81;TE('%s'", result)
    assert '>T</text>' in _svg("TOPSHP89;TE('%s'", result)
    assert '<polygon points="27,15 47,21 37,49 17,43" fill="none" stroke="var(--white)"' in _svg("TOPSHP90", result)
    assert 'fill="var(--green)"' in _svg("TOPSHP93", result)
    assert 'fill="var(--yellow)"' in _svg("TOPSHP96", result)
    assert 'fill="var(--black)"' in _svg("TOPSHPA1", result)
    assert 'fill="var(--green)"' in _svg("TOPSHPA3", result)

    for asset in standard_repair_batch42.REPAIRS:
        svg = _svg(asset, result)
        assert "data-repair-batch=\"standard-repair-batch42\"" in svg
        assert "generated-owned-artwork" in svg

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 27
    assert (ROOT / "catalog" / "owned_repair_batch50.md").exists()
    print("standard repair batch 42: OK")


if __name__ == "__main__":
    main()
