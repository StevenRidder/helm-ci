"""Smoke Standard Repair Batch 39.

Run:  python3 -m forge.tests.test_standard_repair_batch39
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch39


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch47.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch39.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 20
    assert not result["blockers"]
    assert {row["asset"] for row in result["symbols"]} == set(standard_repair_batch39.REPAIRS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}

    assert 'data-repair-batch="standard-repair-batch39"' in _svg("TOPSHP00", result)
    assert '<rect x="18" y="11" width="28" height="42" fill="var(--red)"' in _svg("TOPSHP00", result)
    assert '<rect x="24" y="18" width="16" height="28" fill="var(--white)"' in _svg("TOPSHP01", result)
    assert 'fill="var(--black)"' in _svg("TOPSHP02", result)
    assert 'points="15,16 49,16 32,54"' in _svg("TOPSHP05", result)
    assert 'points="32,10 15,48 49,48"' in _svg("TOPSHP08", result)
    assert 'clip_TOPSHP09_TE_s' in _svg("TOPSHP09;TE('%s'", result)
    assert '>T</text>' in _svg("TOPSHP15;TE('%s'", result)
    assert 'fill="var(--green)"' in _svg("TOPSHP09;TE('%s'", result)
    assert 'fill="var(--yellow)"' in _svg("TOPSHP15;TE('%s'", result)
    assert 'fill="var(--orange)"' in _svg("TOPSHP17", result)
    assert 'fill="var(--yellow)"' in _svg("TOPSHP18", result)
    assert '<rect x="19" y="12" width="26" height="40" fill="var(--white)"' in _svg("TOPSHP21", result)

    for asset in standard_repair_batch39.REPAIRS:
        svg = _svg(asset, result)
        assert "data-repair-batch=\"standard-repair-batch39\"" in svg
        assert "generated-owned-artwork" in svg

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 20
    assert (ROOT / "catalog" / "owned_repair_batch47.md").exists()
    print("standard repair batch 39: OK")


if __name__ == "__main__":
    main()
