"""Smoke the one-symbol-at-a-time LLM judge packet builder.

Run:  python -m forge.tests.test_source_priority_llm_judge_loop
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import source_priority_llm_judge_loop


ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    result = source_priority_llm_judge_loop.build(asset="WRECKS01", render_candidate=False)

    assert result["status"] == "ready_for_one_symbol_at_a_time_judging"
    assert result["selection"]["selected_packets"] == 1
    assert result["loop_contract"][0] == "Judge one symbol at a time."

    packet = result["packets"][0]
    assert packet["asset"] == "WRECKS01"
    assert packet["status"] == "ready_for_one_symbol_llm_judge"
    assert packet["candidate"]["candidate_role"] == "latest_generated_owned_repair_candidate"
    assert packet["candidate"]["svg"] == "assets/svg/owned_repair_batch1/WRECKS01.svg"
    assert packet["official_context"]["s57"]["object_class"] == "$CSYMB"
    assert packet["official_context"]["s101"]["symbol_id"] == "WRECKS01"
    assert "level of chart datum" in packet["official_context"]["usage_description"]
    assert "Judge exactly one symbol" in packet["judge_prompt"]
    assert "one-to-one" in packet["judge_prompt"]
    assert "judge_comments" in packet["judge_prompt"]
    assert "Repair WRECKS01 only if" in packet["repair_agent_instruction"]
    assert packet["repair_queue_item"]["status"] == "queued_if_judge_fails"
    assert packet["judge_schema"]["properties"]["recognized_as"]["type"] == "string"
    assert packet["judge_schema"]["properties"]["judge_comments"]["type"] == "array"

    sources = {ref["source"] for ref in packet["reference_candidates"]}
    assert "helm_current_owned_candidate_svg" in sources
    assert "opencpn_s52_reference_render" in sources
    assert "s101_portrayal_catalogue_svg" in sources

    saved = json.loads((ROOT / "out" / "source_priority_llm_judge_loop" / "judge_packets.json").read_text())
    assert saved["packets"][0]["asset"] == "WRECKS01"
    print("source-priority LLM judge loop: OK")


if __name__ == "__main__":
    main()
