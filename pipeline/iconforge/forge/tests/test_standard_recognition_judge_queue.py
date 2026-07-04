"""Smoke the visual recognition judge queue.

Run:  python3 -m forge.tests.test_standard_recognition_judge_queue
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_craft_audit, standard_recognition_judge_queue, standard_style_audit


ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    standard_style_audit.build()
    standard_craft_audit.build()
    result = standard_recognition_judge_queue.build()
    summary = result["summary"]

    assert result["status"] == "recognition_judge_queue_built"
    assert summary["packets"] == 824
    assert summary["recognition_ready"] > 0
    assert summary["recognition_ready_with_style_notes"] > 0
    assert summary["recognition_blocked"] == 41
    assert summary["blocker_counts"]["no_reference_images"] == 41
    assert summary["provider_image_counts"]["opencpn_render"] >= 700

    by_asset = {packet["asset"]: packet for packet in result["packets"]}
    boybar = by_asset["BOYBAR01"]
    assert boybar["status"] in {"recognition_ready", "recognition_ready_with_style_notes"}
    assert boybar["semantic_brief"]["required_shape"] == "barrel buoy body"
    assert any(image["provider"] == "opencpn_render" for image in boybar["reference_images"])
    assert any(image["provider"] == "s101" for image in boybar["reference_images"])
    assert boybar["judge_contract"]["question"].startswith("Does the Helm candidate")
    assert "thin-stroke clean geometric style" in " ".join(boybar["judge_contract"]["must_check"])

    danger = by_asset["DANGER53"]
    assert danger["status"] == "recognition_blocked"
    assert "style_blocked" in danger["blockers"]
    assert "craft_blocked" in danger["blockers"]

    arcsln01 = by_asset["ARCSLN01"]
    assert arcsln01["status"] == "recognition_blocked"
    assert arcsln01["helm_candidate"]["source_batch"] == "catalog/owned_repair_batch91.json"
    assert "no_reference_images" in arcsln01["blockers"]

    saved = json.loads((ROOT / "catalog" / "standard_recognition_judge_queue.json").read_text())
    assert saved["summary"]["packets"] == summary["packets"]
    assert (ROOT / "catalog" / "standard_recognition_judge_queue.csv").exists()
    assert (ROOT / "catalog" / "standard_recognition_judge_queue.md").exists()
    print("standard recognition judge queue: OK")


if __name__ == "__main__":
    main()
