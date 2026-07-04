"""Visual repair loop for exact Chart No.1 symbol crops.

FORGE-15 restores the useful part of the pilot: a vision-capable judge provides
structured repair feedback that a generator can consume. The loop starts only
with FORGE-14 rows that have true exact_symbol_crop evidence.

Run:  python -m forge.chart1_visual_repair --limit 20
Live: ANTHROPIC_API_KEY=... python -m forge.chart1_visual_repair --live --limit 20
"""
from __future__ import annotations

import argparse
import base64
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from . import chart1_parity


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "chart1_visual_repair"
REPORT = ROOT / "out" / "chart1_parity" / "report.json"


@dataclass
class RepairFeedback:
    source_crop_valid: bool
    overall_pass: bool
    observed: str
    expected: str
    repair_instruction: str
    safety_reason_codes: list[str]
    confidence: float


class LiveVisualRepairJudge:
    """Vision judge that compares candidate render to exact Chart No.1 crop."""

    def __init__(self, model: str = "claude-opus-4-8", client=None):
        if client is None:
            import anthropic

            client = anthropic.Anthropic()
        self.client = client
        self.model = model
        self.source = f"live:{model}"

    def judge(self, row: dict, candidate_png: bytes, source_png: bytes) -> RepairFeedback:
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "source_crop_valid": {"type": "boolean"},
                "overall_pass": {"type": "boolean"},
                "observed": {"type": "string"},
                "expected": {"type": "string"},
                "repair_instruction": {"type": "string"},
                "safety_reason_codes": {"type": "array", "items": {"type": "string"}},
                "confidence": {"type": "number"},
            },
            "required": [
                "source_crop_valid",
                "overall_pass",
                "observed",
                "expected",
                "repair_instruction",
                "safety_reason_codes",
                "confidence",
            ],
        }
        content = [
            _image_block(candidate_png),
            _image_block(source_png),
            {
                "type": "text",
                "text": (
                    "You are the strict visual judge in a nautical chart-symbol repair loop.\n"
                    "Image 1 is the generated candidate. Image 2 is the official NOAA U.S. Chart No.1 "
                    "source crop. Compare them as symbol geometry, not as pixel-identical artwork.\n"
                    "If the source crop is not a single symbol/glyph, set source_crop_valid=false.\n"
                    "Return repair feedback for the generator LLM. Be concrete: name the wrong body, "
                    "wrong topmark, wrong color, wrong orientation, or light-flare/generic-placeholder "
                    "failure. Do not approve unless the candidate visually matches the source crop and "
                    "the semantic expectation.\n\n"
                    f"Asset: {row['asset']}\n"
                    f"Expected class: {row['chart1_class']}\n"
                    f"Expected shape: {row['expected_shape']}\n"
                    f"Expected colors: {row['expected_colors']}\n"
                    f"Existing deterministic reasons: {row['reason_codes']}\n"
                    f"Reference crop id: {row['reference_crop_id']}\n"
                ),
            },
        ]
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1600,
            output_config={"format": {"type": "json_schema", "schema": schema}},
            messages=[{"role": "user", "content": content}],
        )
        data = json.loads(next(block.text for block in response.content if block.type == "text"))
        return RepairFeedback(**data)


def _image_block(png: bytes) -> dict:
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": "image/png",
            "data": base64.standard_b64encode(png).decode(),
        },
    }


def _ensure_parity_report() -> dict:
    if not REPORT.exists():
        rc = chart1_parity.main([])
        if rc != 0:
            raise RuntimeError("chart1 parity report generation failed")
    return json.loads(REPORT.read_text())


def _selected_rows(report: dict, limit: int | None) -> list[dict]:
    rows = [
        row for row in report["rows"]
        if row["reference_evidence_status"] == "exact_symbol_crop" and row["verdict"] != "deferred"
    ]
    rows = sorted(rows, key=lambda row: (row["asset"], row["style"], row["palette"]))
    return rows[:limit] if limit else rows


def _excluded_counts(report: dict) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in report["rows"]:
        status = row["reference_evidence_status"]
        if status == "exact_symbol_crop" or row["verdict"] == "deferred":
            continue
        counts[status] = counts.get(status, 0) + 1
    return counts


def _heuristic_feedback(row: dict) -> RepairFeedback:
    expected = f"{row['chart1_class']} from {row['reference_crop_id']}"
    observed = row["observed_shape"]
    reasons = list(row["reason_codes"])
    if observed == "light_flare":
        instruction = (
            "Remove all radial light rays and circular flare geometry. Draw only the topmark glyph "
            f"shown in the Chart No.1 source crop ({row['chart1_class']}) using CSS color variables, "
            "with a compact 64x64 viewBox and the existing anchor preserved."
        )
    elif observed == "generic_body":
        instruction = (
            "Replace the generic body placeholder with the exact standalone topmark silhouette shown "
            f"in the Chart No.1 source crop ({row['chart1_class']})."
        )
    else:
        instruction = (
            "Redraw the candidate so its silhouette, orientation, and color tokens match the exact "
            f"Chart No.1 source crop ({row['chart1_class']})."
        )
    return RepairFeedback(
        source_crop_valid=True,
        overall_pass=False,
        observed=observed,
        expected=expected,
        repair_instruction=instruction,
        safety_reason_codes=sorted(set(reasons + ["visual_repair_required"])),
        confidence=0.0,
    )


def _repair_prompt(row: dict, feedback: RepairFeedback) -> str:
    return (
        "Repair this Icon Forge SVG candidate using the visual judge feedback.\n"
        "Do not trace OpenCPN raster artwork. Use the NOAA Chart No.1 source crop as reference.\n"
        "Preserve CSS variable colors, 64x64 viewBox, no text, and anchor semantics.\n\n"
        f"Asset: {row['asset']}\n"
        f"Candidate SVG: {row['svg']}\n"
        f"Candidate render: {row['render']}\n"
        f"Chart No.1 source crop: {row['reference_crop']}\n"
        f"Expected: {feedback.expected}\n"
        f"Observed: {feedback.observed}\n"
        f"Repair instruction: {feedback.repair_instruction}\n"
        f"Safety reasons: {', '.join(feedback.safety_reason_codes)}\n"
    )


def _row_record(row: dict, feedback: RepairFeedback, backend: str) -> dict:
    return {
        "asset": row["asset"],
        "style": row["style"],
        "palette": row["palette"],
        "reference_crop_id": row["reference_crop_id"],
        "reference_crop": row["reference_crop"],
        "render": row["render"],
        "svg": row["svg"],
        "chart1_class": row["chart1_class"],
        "expected_shape": row["expected_shape"],
        "observed_shape": row["observed_shape"],
        "deterministic_reasons": row["reason_codes"],
        "judge_backend": backend,
        "feedback": asdict(feedback),
        "generator_repair_prompt": _repair_prompt(row, feedback),
    }


def run(limit: int | None, live: bool) -> dict:
    report = _ensure_parity_report()
    selected = _selected_rows(report, limit)
    use_live = live and bool(os.environ.get("ANTHROPIC_API_KEY"))
    judge = LiveVisualRepairJudge() if use_live else None
    backend = judge.source if judge else "offline:heuristic_feedback_not_visual"
    rows = []
    for row in selected:
        candidate_png = (ROOT / row["render"]).read_bytes()
        source_png = (ROOT / row["reference_crop"]).read_bytes()
        feedback = judge.judge(row, candidate_png, source_png) if judge else _heuristic_feedback(row)
        rows.append(_row_record(row, feedback, backend))

    status = "live_judged" if judge else "offline_feedback_scaffold"
    if live and not os.environ.get("ANTHROPIC_API_KEY"):
        status = "blocked_missing_anthropic_key"
    result = {
        "schema_version": 1,
        "generator": "iconforge-chart1-visual-repair",
        "status": status,
        "judge_backend": backend,
        "source_report": "out/chart1_parity/report.json",
        "selection": {
            "required_reference_evidence_status": "exact_symbol_crop",
            "selected_rows": len(selected),
            "excluded_non_exact_counts": _excluded_counts(report),
        },
        "non_go_conditions": [
            "Do not feed class_panel_reference or multi_symbol_reference rows into the repair loop.",
            "Do not treat offline heuristic feedback as a visual-model verdict.",
            "Do not final-approve a repaired SVG until deterministic checks and live visual judge pass.",
        ],
        "rows": rows,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "repair_feedback.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--live", action="store_true", help="use the live vision judge; requires ANTHROPIC_API_KEY")
    args = parser.parse_args(argv)
    result = run(args.limit, args.live)
    print(f"visual repair: {result['status']}")
    print(f"judge backend: {result['judge_backend']}")
    print(f"selected rows: {result['selection']['selected_rows']}")
    print(f"excluded: {result['selection']['excluded_non_exact_counts']}")
    print(f"report: {OUT / 'repair_feedback.json'}")
    return 2 if result["status"] == "blocked_missing_anthropic_key" else 0


if __name__ == "__main__":
    raise SystemExit(main())
