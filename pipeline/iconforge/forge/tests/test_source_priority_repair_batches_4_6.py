"""Smoke the final source-priority repair batches.

Run:  python -m forge.tests.test_source_priority_repair_batches_4_6
"""
from __future__ import annotations

from pathlib import Path

from .. import source_priority_repair_batch4
from .. import source_priority_repair_batch5
from .. import source_priority_repair_batch6


ROOT = Path(__file__).resolve().parent.parent.parent


def _check(report: dict, *, batch_offset: int, batch_size: int, first: str, last: str) -> None:
    assert report["status"] == "candidate_batch_pending_visual_review"
    assert report["batch_offset"] == batch_offset
    assert report["batch_size"] == batch_size
    assert report["symbols"][0]["asset"] == first
    assert report["symbols"][-1]["asset"] == last
    assert all(row["qa"]["final_approved"] is False for row in report["symbols"])
    assert all(row["provenance"]["origin"] == "generated-owned-artwork" for row in report["symbols"])
    assert all(row["provenance"]["style_contract_id"] == "helm-openbridge-navigation-v1" for row in report["symbols"])
    for row in report["symbols"]:
        assert (ROOT / row["after_svg"]).exists()


def main():
    batch4 = source_priority_repair_batch4.build(render_outputs=False)
    batch5 = source_priority_repair_batch5.build(render_outputs=False)
    batch6 = source_priority_repair_batch6.build(render_outputs=False)

    _check(batch4, batch_offset=420, batch_size=150, first="RECTRC56", last="TOWERS73")
    _check(batch5, batch_offset=570, batch_size=150, first="TOWERS74|;TX(OBJNAM", last="TIDCUR02")
    _check(batch6, batch_offset=720, batch_size=27, first="TIDCUR03", last="WNDMIL12")

    assert batch4["summary"]["repair_existing_helm_style_svg"] == 144
    assert batch4["summary"]["redraw_s101_reference_into_helm_style"] == 6
    assert batch4["summary"]["generated_placeholder_no_fallback"] == 0

    assert batch5["summary"]["repair_existing_helm_style_svg"] == 41
    assert batch5["summary"]["redraw_s101_reference_into_helm_style"] == 109
    assert batch5["summary"]["generated_placeholder_no_fallback"] == 6

    assert batch6["summary"]["repair_existing_helm_style_svg"] == 0
    assert batch6["summary"]["redraw_s101_reference_into_helm_style"] == 27
    assert batch6["summary"]["generated_placeholder_no_fallback"] == 0

    total = sum(report["batch_size"] for report in [batch4, batch5, batch6])
    assert total == 327
    print("source-priority repair batches 4-6: OK")


if __name__ == "__main__":
    main()
