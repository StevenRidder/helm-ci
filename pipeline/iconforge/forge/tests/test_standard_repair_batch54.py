"""Smoke Standard Repair Batch 54.

Run:  python3 -m forge.tests.test_standard_repair_batch54
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch54


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch62.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch54.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 9
    assert not result["blockers"]
    assert {row["asset"] for row in result["symbols"]} == {f"HRBFAC{index}" for index in range(10, 19)}
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}
    assert {row["source_judge"] for row in result["symbols"]} == {"catalog/standard_judge_batch_008.json"}

    for asset in (f"HRBFAC{index}" for index in range(10, 19)):
        svg = _svg(asset, result)
        assert 'data-repair-batch="standard-repair-batch54"' in svg
        assert 'fill="var(--gray)"' in svg
        assert 'stroke="var(--black)"' in svg
        assert "generated-owned-artwork" in svg

    assert 'data-shape="default_harbour_facility_vertical_mark"' in _svg("HRBFAC10", result)
    assert 'data-shape="naval_base_n_mark"' in _svg("HRBFAC11", result)
    assert 'data-shape="ship_yard_y_mark"' in _svg("HRBFAC12", result)
    assert 'data-shape="harbour_master_anchor_mark"' in _svg("HRBFAC13", result)
    assert 'data-shape="pilot_station_p_mark"' in _svg("HRBFAC14", result)
    assert ">P</text>" in _svg("HRBFAC14", result)
    assert 'data-shape="water_police_wp_mark"' in _svg("HRBFAC15", result)
    assert ">WP</text>" in _svg("HRBFAC15", result)
    assert 'data-shape="customs_horizontal_band_mark"' in _svg("HRBFAC16", result)
    assert 'data-shape="service_repair_wrench_mark"' in _svg("HRBFAC17", result)
    assert 'data-shape="quarantine_cross_mark"' in _svg("HRBFAC18", result)

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 9
    assert (ROOT / "catalog" / "owned_repair_batch62.md").exists()
    print("standard repair batch 54: OK")


if __name__ == "__main__":
    main()
