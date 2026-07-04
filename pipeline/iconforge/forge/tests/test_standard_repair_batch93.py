"""Smoke Standard Repair Batch 93.

Run:  python3 -m forge.tests.test_standard_repair_batch93
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch93


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch93.json"


def _svg(asset: str, result: dict) -> str:
    row = next(row for row in result["symbols"] if row["asset"] == asset)
    return (ROOT / row["after_svg"]).read_text()


def main():
    result = standard_repair_batch93.build(render_outputs=False)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 16
    assert {row["asset"] for row in result["symbols"]} == set(standard_repair_batch93.TARGETS)
    assert all(row["qa"]["visual_parity"] == "repaired_pending_judge_rerun" for row in result["symbols"])
    assert all(row["source_judge"] == "catalog/standard_judge_batch_092_rerun.json" for row in result["symbols"])
    assert "M16 32 L20 29" in _svg("CBLSUB06", result)
    assert _svg("CROSSX02", result).count("stroke-width=\"0.75\"") >= 16
    assert "M23 18 L41 46" in _svg("DIAMOND1", result)
    assert "M20 21 H44 L32 45 Z" in _svg("DQUALA11", result)
    assert ">U</text>" in _svg("DQUALU01", result)
    assert ">DW</text>" in _svg("DWRTCL05", result)
    assert 'stroke-dasharray="5 4"' in _svg("DWLDEF01", result)
    assert "rect" in _svg("FERYRT02", result)
    assert REPORT.exists()
    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 16
    assert (ROOT / "catalog" / "owned_repair_batch93.md").exists()
    print("standard repair batch 93: OK")


if __name__ == "__main__":
    main()
