"""Smoke the FORGE-15 visual repair feedback loop.

Run:  python -m forge.tests.test_chart1_visual_repair
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

from .. import chart1_visual_repair


ROOT = Path(__file__).resolve().parent.parent.parent


class _Block:
    def __init__(self, text):
        self.type, self.text = "text", text


class _Resp:
    def __init__(self, text):
        self.content = [_Block(text)]


class _Messages:
    def __init__(self, outer):
        self.outer = outer

    def create(self, **kw):
        self.outer.captured = kw
        return _Resp(self.outer.canned)


class StubClient:
    def __init__(self, canned):
        self.canned, self.captured = canned, None
        self.messages = _Messages(self)


def main():
    result = chart1_visual_repair.run(limit=12, live=False)

    assert result["status"] == "offline_feedback_scaffold"
    assert result["judge_backend"] == "offline:heuristic_feedback_not_visual"
    assert result["selection"]["required_reference_evidence_status"] == "exact_symbol_crop"
    assert result["selection"]["selected_rows"] == 12
    assert result["selection"]["excluded_non_exact_counts"]["class_panel_reference"] == 20
    assert result["selection"]["excluded_non_exact_counts"]["multi_symbol_reference"] == 175
    assert result["selection"]["excluded_non_exact_counts"]["manual_exception"] == 28

    for row in result["rows"]:
        assert row["reference_crop_id"].startswith("topmark_")
        assert row["reference_crop"]
        assert row["render"]
        assert row["svg"]
        feedback = row["feedback"]
        assert feedback["source_crop_valid"] is True
        assert feedback["overall_pass"] is False
        assert feedback["repair_instruction"]
        assert "visual_repair_required" in feedback["safety_reason_codes"]
        prompt = row["generator_repair_prompt"]
        assert row["reference_crop"] in prompt
        assert row["render"] in prompt
        assert "Repair instruction:" in prompt

    saved = json.loads((ROOT / "out" / "chart1_visual_repair" / "repair_feedback.json").read_text())
    assert saved["selection"] == result["selection"]
    assert len(saved["rows"]) == 12

    canned = json.dumps({
        "source_crop_valid": True,
        "overall_pass": False,
        "observed": "red light flare",
        "expected": "black slanted topmark rectangle",
        "repair_instruction": "Remove light flare rays and draw the slanted rectangle.",
        "safety_reason_codes": ["topmark_rendered_as_light"],
        "confidence": 0.91,
    })
    client = StubClient(canned)
    judge = chart1_visual_repair.LiveVisualRepairJudge(client=client)
    parity = json.loads((ROOT / "out" / "chart1_parity" / "report.json").read_text())
    parity_row = next(
        row for row in parity["rows"]
        if row["reference_evidence_status"] == "exact_symbol_crop" and row["verdict"] != "deferred"
    )
    feedback = judge.judge(parity_row, b"CANDIDATEPNG", b"SOURCEPNG")
    assert feedback.repair_instruction.startswith("Remove light flare")

    kw = client.captured
    assert kw["model"] == "claude-opus-4-8"
    assert kw["output_config"]["format"]["type"] == "json_schema"
    schema = kw["output_config"]["format"]["schema"]
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) >= {"source_crop_valid", "repair_instruction", "safety_reason_codes"}
    images = [block for block in kw["messages"][0]["content"] if block.get("type") == "image"]
    assert len(images) == 2, "candidate and source crop images are both sent"
    assert base64.b64decode(images[0]["source"]["data"]) == b"CANDIDATEPNG"
    assert base64.b64decode(images[1]["source"]["data"]) == b"SOURCEPNG"

    print("chart1 visual repair loop: OK")


if __name__ == "__main__":
    main()
