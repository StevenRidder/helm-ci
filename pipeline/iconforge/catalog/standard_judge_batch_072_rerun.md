# Standard Judge Batch 072 Rerun

- Project: `vulkan`
- Task: `FORGE-15`
- Agent: `codex/FORGE-15-judge-loop-current`
- Source batch: `owned_repair_batch72`
- Approval note: pass means `judge_pass_pending_final_approval` only; no row is human-final-approved.

## Summary

| Result | Count |
| --- | ---: |
| Selected | 7 |
| Pass pending human | 5 |
| Fail | 2 |
| Final approved | 0 |

## Verdicts

| Symbol | Verdict | Confidence | Required change | Safety reason codes | Notes |
| --- | --- | ---: | --- | --- | --- |
| `TOPMAR01` | Pass pending human | 0.84 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: red/green horizontal-banded circular topmark preserves the required colour order. No final approval is granted. |
| `TOPMAR91` | Pass pending human | 0.84 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: red compact rectangular topmark preserves the red topmark cue. No final approval is granted. |
| `TOPMAR92` | Pass pending human | 0.84 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: green compact rectangular topmark preserves the green topmark cue. No final approval is granted. |
| `TOPMAR98` | Pass pending human | 0.84 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: diamond topmark preserves the white/orange diagonal colour cue. No final approval is granted. |
| `TOPMAR99` | Pass pending human | 0.84 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: diamond topmark preserves the white/orange diagonal colour cue. No final approval is granted. |
| `TOPMAR90` | Fail | 0.88 | Redraw TOPMAR90 as the pricken point-down topmark from the witness: stem with side/barb detail and downward orientation, not a plain arrow. | wrong_topmark_silhouette, missing_pricken_barbs, reference_mismatch | FAIL. The repaired SVG renders as a generic downward arrow, but the OpenCPN witness is a pricken point-down topmark with a stem and side/barb detail. |
| `TOPMAR93` | Fail | 0.88 | Redraw TOPMAR93 as the pricken point-up topmark from the witness: stem with side/barb detail and upward orientation, not a plain arrow. | wrong_topmark_silhouette, missing_pricken_barbs, reference_mismatch | FAIL. The repaired SVG renders as a generic upward arrow, but the OpenCPN witness is a pricken point-up topmark with a stem and side/barb detail. |

## Failed Symbols

- `TOPMAR90`: Redraw TOPMAR90 as the pricken point-down topmark from the witness: stem with side/barb detail and downward orientation, not a plain arrow.
- `TOPMAR93`: Redraw TOPMAR93 as the pricken point-up topmark from the witness: stem with side/barb detail and upward orientation, not a plain arrow.

## Evidence Notes

- Judged current repaired rows from owned_repair_batch72.
- Pass means judge_pass_pending_final_approval only; this artifact grants zero final approvals.
- Generic arrows were rejected where the reference requires pricken side/barb detail.
