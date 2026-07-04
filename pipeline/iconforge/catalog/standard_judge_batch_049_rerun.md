# Standard Judge Batch 049 Rerun

- Project: `vulkan`
- Task: `FORGE-15`
- Agent: `codex/FORGE-15-judge-loop-current`
- Source batch: `owned_repair_batch49`
- Approval note: pass means `judge_pass_pending_final_approval` only; no row is human-final-approved.

## Summary

| Result | Count |
| --- | ---: |
| Selected | 20 |
| Pass pending human | 18 |
| Fail | 2 |
| Final approved | 0 |

## Verdicts

| Symbol | Verdict | Confidence | Required change | Safety reason codes | Notes |
| --- | --- | ---: | --- | --- | --- |
| `TOPSHP47` | Fail | 0.93 | Redraw TOPSHP47 as a compact square/slanted-board topmark, preserving the red/red colour semantics; do not use a tall rectangle body. | wrong_topmark_silhouette, wrong_aspect_ratio, reference_mismatch | FAIL. The repaired SVG renders as a tall upright rectangle, while the OpenCPN/Chart 1 witnesses show a compact square/slanted-board topmark. |
| `TOPSHP48` | Fail | 0.93 | Redraw TOPSHP48 as a compact square/slanted-board topmark, preserving the green/green colour semantics; do not use a tall rectangle body. | wrong_topmark_silhouette, wrong_aspect_ratio, reference_mismatch | FAIL. The repaired SVG renders as a tall upright rectangle, while the OpenCPN/Chart 1 witnesses show a compact square/slanted-board topmark. |
| `TOPSHP51` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: diamond/topmark silhouette and white-black-white partition match the witness family. No final approval is granted. |
| `TOPSHP52` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: solid black diamond/topmark silhouette matches the witness family. No final approval is granted. |
| `TOPSHP53` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: solid yellow diamond/topmark silhouette matches the witness family. No final approval is granted. |
| `TOPSHP54` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: solid red diamond/topmark silhouette matches the witness family. No final approval is granted. |
| `TOPSHP55` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: solid orange diamond/topmark silhouette matches the witness family. No final approval is granted. |
| `TOPSHP58` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: red/white diamond partition matches the witness family. No final approval is granted. |
| `TOPSHP61` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: orange/white diamond partition matches the witness family. No final approval is granted. |
| `TOPSHP62` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: white/orange diamond partition matches the witness family. No final approval is granted. |
| `TOPSHP63` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: white/red/white diamond partition matches the witness family. No final approval is granted. |
| `TOPSHP64` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: white/green/white diamond partition matches the witness family. No final approval is granted. |
| `TOPSHP65` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: white/red diamond partition matches the witness family. No final approval is granted. |
| `TOPSHP67` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: orange/white diamond partition matches the witness family. No final approval is granted. |
| `TOPSHP69` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: white/red diamond partition matches the witness family. No final approval is granted. |
| `TOPSHP70` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: yellow diamond/topmark silhouette matches the witness family. No final approval is granted. |
| `TOPSHP71` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: white/orange diamond partition matches the witness family. No final approval is granted. |
| `TOPSHP72` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: white/red/white diamond partition matches the witness family. No final approval is granted. |
| `TOPSHP73;TE('%s'` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: white/black/white diamond partition and text-bearing cue match the S-52 row well enough for human review. No final approval is granted. |
| `TOPSHP74` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: red/white/white/red diamond partition matches the witness family. No final approval is granted. |

## Failed Symbols

- `TOPSHP47`: Redraw TOPSHP47 as a compact square/slanted-board topmark, preserving the red/red colour semantics; do not use a tall rectangle body.
- `TOPSHP48`: Redraw TOPSHP48 as a compact square/slanted-board topmark, preserving the green/green colour semantics; do not use a tall rectangle body.

## Evidence Notes

- Judged current repaired rows from owned_repair_batch49.
- Pass means judge_pass_pending_final_approval only; this artifact grants zero final approvals.
- TOPSHP47 and TOPSHP48 fail because the generated candidate is a tall rectangle instead of the compact square/slanted-board witness shape.
