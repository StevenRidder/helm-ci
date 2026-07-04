# Standard Judge Batch 078 Rerun

- Project: `vulkan`
- Task: `FORGE-15`
- Agent: `codex/FORGE-15-judge-loop-current`
- Source batch: `owned_repair_batch78`
- Approval note: pass means `judge_pass_pending_final_approval` only; no row is human-final-approved.

## Summary

| Result | Count |
| --- | ---: |
| Selected | 12 |
| Pass pending human | 10 |
| Fail | 2 |
| Final approved | 0 |

## Verdicts

| Symbol | Verdict | Confidence | Required change | Safety reason codes | Notes |
| --- | --- | ---: | --- | --- | --- |
| `DISMAR03` | Pass pending human | 0.85 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: distance mark preserves the magenta distance/text cue. No final approval is granted. |
| `DISMAR04` | Pass pending human | 0.85 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: distance point with no mark preserves the magenta km text cue. No final approval is granted. |
| `LITFLT10` | Pass pending human | 0.85 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: red/white light float preserves the float body, light, and red/white colour semantics. No final approval is granted. |
| `LITFLT61` | Pass pending human | 0.85 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: green light float preserves the float body, light, and green colour semantics. No final approval is granted. |
| `LITVES60` | Pass pending human | 0.85 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: red light vessel preserves the vessel body and light cue closely enough for human review. No final approval is granted. |
| `LITVES61` | Pass pending human | 0.85 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: green light vessel preserves the vessel body and light cue closely enough for human review. No final approval is granted. |
| `OWNSHP01` | Pass pending human | 0.85 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: own-ship constant-size symbol preserves the concentric-circle cue. No final approval is granted. |
| `OWNSHP05` | Pass pending human | 0.85 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: own-ship to-scale symbol preserves the elongated vessel outline cue. No final approval is granted. |
| `RFNERY01` | Pass pending human | 0.85 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: refinery mark preserves the circular refinery/well witness family. No final approval is granted. |
| `RFNERY11` | Pass pending human | 0.85 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: conspicuous refinery mark preserves the black circular refinery/well witness family. No final approval is granted. |
| `SCALEB10` | Fail | 0.90 | Redraw SCALEB10 as the segmented one-mile vertical scale bar witness with alternating ticks/segments; do not use a solid capped I-beam. | wrong_scalebar_silhouette, missing_segment_pattern, reference_mismatch | FAIL. The repaired SVG renders as a solid orange capped I-beam, but the OpenCPN/Chart 1 witness is a segmented one-mile vertical scale bar with alternating coloured ticks. |
| `SCALEB11` | Fail | 0.90 | Redraw SCALEB11 as the segmented 10-mile vertical latitude scale witness with visible tick/dash segments; do not use a solid capped I-beam. | wrong_scalebar_silhouette, missing_segment_pattern, reference_mismatch | FAIL. The repaired SVG renders as a solid black capped I-beam, but the witness is a segmented 10-mile latitude scale bar with visible dash/tick segments. |

## Failed Symbols

- `SCALEB10`: Redraw SCALEB10 as the segmented one-mile vertical scale bar witness with alternating ticks/segments; do not use a solid capped I-beam.
- `SCALEB11`: Redraw SCALEB11 as the segmented 10-mile vertical latitude scale witness with visible tick/dash segments; do not use a solid capped I-beam.

## Evidence Notes

- Judged current repaired rows from owned_repair_batch78.
- Pass means judge_pass_pending_final_approval only; this artifact grants zero final approvals.
- Scale bars that lost segmentation were failed back to repair.
