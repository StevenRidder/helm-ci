# Standard Judge Batch 085 Rerun

- Project: `vulkan`
- Task: `FORGE-15`
- Agent: `codex/FORGE-15-judge-loop-current`
- Source batch: `owned_repair_batch85`
- Approval note: pass means `judge_pass_pending_final_approval` only; no row is human-final-approved.

## Summary

| Result | Count |
| --- | ---: |
| Selected | 2 |
| Pass pending human | 2 |
| Fail | 0 |
| Final approved | 0 |

## Verdicts

| Symbol | Verdict | Confidence | Required change | Safety reason codes | Notes |
| --- | --- | ---: | --- | --- | --- |
| `VECWTR01` | Pass pending human | 0.92 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: black through-water vector now preserves the single-chevron witness shape. No final approval is granted. |
| `VECWTR21` | Pass pending human | 0.92 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: green through-water vector now preserves the single-chevron witness shape. No final approval is granted. |

## Failed Symbols

- None.

## Evidence Notes

- Judged current repaired rows from owned_repair_batch85.
- Pass means judge_pass_pending_final_approval only; this artifact grants zero final approvals.
- The repair specifically resolves the double-chevron versus single-chevron through-water vector confusion.
