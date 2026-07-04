"""Smoke Standard Repair Batch 37.

Run:  python3 -m forge.tests.test_standard_repair_batch37
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch37


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch45.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch37.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 18
    assert not result["blockers"]
    assert {row["asset"] for row in result["symbols"]} == set(standard_repair_batch37.REPAIRS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}

    assert '<rect x="22" y="24" width="20" height="24"' in _svg("REFDMP01", result)
    assert "M20 51 V25" in _svg("RFNERY01", result)
    assert "var(--black)" in _svg("RFNERY11", result)
    assert "stroke-dasharray" in _svg("RTLDEF51", result)
    assert ">1</text>" in _svg("SCALEB10", result)
    assert ">10</text>" in _svg("SCALEB11", result)
    assert '<ellipse cx="32" cy="21"' in _svg("SILBUI01", result)
    assert "var(--black)" in _svg("SILBUI11", result)
    assert ">SS</text>" in _svg("SISTAT02", result)
    assert ">PE</text>" in _svg("SSENTR01", result)
    assert ">LK</text>" in _svg("SSLOCK01", result)
    assert ">WS</text>" in _svg("SSWARS01", result)
    assert "M32 9 L37 25" in _svg("STARPT01", result)
    assert "M15 20 H49" in _svg("TMBYRD01", result)
    assert '<circle cx="32" cy="32" r="17"' in _svg("TNKCON02", result)
    assert "var(--black)" in _svg("TNKCON12", result)
    assert '<circle cx="32" cy="33" r="19"' in _svg("TNKFRM01", result)
    assert "var(--black)" in _svg("TNKFRM11", result)

    for asset in standard_repair_batch37.REPAIRS:
        svg = _svg(asset, result)
        assert "data-repair-batch=\"standard-repair-batch37\"" in svg
        assert "generated-owned-artwork" in svg

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 18
    assert (ROOT / "catalog" / "owned_repair_batch45.md").exists()
    print("standard repair batch 37: OK")


if __name__ == "__main__":
    main()
