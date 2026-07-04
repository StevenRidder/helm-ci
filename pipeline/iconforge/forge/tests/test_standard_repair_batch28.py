"""Smoke Standard Repair Batch 28.

Run:  python3 -m forge.tests.test_standard_repair_batch28
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch28


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch36.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch28.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 2
    assert not result["blockers"]

    assert {row["asset"] for row in result["symbols"]} == {"SNDWAV02", "TIDCUR01"}
    assert {row["source_judge"] for row in result["symbols"]} == {"catalog/standard_judge_batch_035_rerun.json"}
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}

    sand = _svg("SNDWAV02", result)
    assert "var(--gray)" in sand
    assert "M9 36 H17 L21 25 L25 36" in sand
    assert " C" not in sand

    current = _svg("TIDCUR01", result)
    assert "var(--orange)" in current
    assert "M32 55 V48 M32 41 V34 M32 27 V20" in current
    assert "M21 23 L32 11 L43 23" in current
    assert '<circle cx="43" cy="13"' not in current

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 2
    assert (ROOT / "catalog" / "owned_repair_batch36.md").exists()
    print("standard repair batch 28: OK")


if __name__ == "__main__":
    main()
