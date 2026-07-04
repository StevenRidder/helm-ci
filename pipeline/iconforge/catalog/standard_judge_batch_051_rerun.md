# Standard Judge Batch 051 Rerun

- Project: `vulkan`
- Task: `FORGE-15`
- Agent: `codex/FORGE-15-judge-loop-current`
- Source batch: `owned_repair_batch51`
- Approval note: pass means `judge_pass_pending_final_approval` only; no row is human-final-approved.

## Summary

| Result | Count |
| --- | ---: |
| Selected | 20 |
| Pass pending human | 14 |
| Fail | 6 |
| Final approved | 0 |

## Verdicts

| Symbol | Verdict | Confidence | Required change | Safety reason codes | Notes |
| --- | --- | ---: | --- | --- | --- |
| `TOPSHPA4` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: red/white compact slanted-board topmark matches the witness family. No final approval is granted. |
| `TOPSHPA5` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: white/black/white compact slanted-board topmark matches the witness family. No final approval is granted. |
| `TOPSHPA6` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: solid red compact slanted-board topmark matches the witness family. No final approval is granted. |
| `TOPSHPA7` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: green/red/green compact slanted-board topmark matches the witness family. No final approval is granted. |
| `TOPSHPA8` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: green/black compact slanted-board topmark matches the witness family. No final approval is granted. |
| `TOPSHPA9` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: white/red compact board topmark matches the row colour semantics. No final approval is granted. |
| `TOPSHPB0` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: red/white compact board topmark matches the row colour semantics. No final approval is granted. |
| `TOPSHPD1` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: orange circular topmark matches the OpenCPN/Chart 1 witness family. No final approval is granted. |
| `TOPSHPD2` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: green circular topmark matches the OpenCPN witness and row colour semantics. No final approval is granted. |
| `TOPSHPD3` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: red circular topmark matches the OpenCPN witness and row colour semantics. No final approval is granted. |
| `TOPSHPD5` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: red/white/black circular partition preserves the row colour semantics closely enough for human review. No final approval is granted. |
| `TOPSHPI1` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: yellow cross topmark matches the OpenCPN/Chart 1 cross witness family. No final approval is granted. |
| `TOPSHPI2` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: black cross topmark matches the OpenCPN/Chart 1 cross witness family. No final approval is granted. |
| `TOPSHPT1` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: red compact slanted-board topmark preserves the red row semantics and is close enough for human review. No final approval is granted. |
| `TOPSHPI3` | Fail | 0.90 | Redraw TOPSHPI3 as a cross/X topmark that preserves the white/red colour cue; do not collapse it to a plain black X. | missing_colour_pattern, colour_semantics_lost, reference_mismatch | FAIL. The repaired SVG renders as a plain black X and loses the white/red semantics visible in the OpenCPN witness and S-57 colour metadata. |
| `TOPSHPJ1` | Fail | 0.92 | Redraw TOPSHPJ1 as the yellow TOPSHP17 cup/bucket-like topmark from the OpenCPN witness, not a diagonal slash. | wrong_topmark_silhouette, wrong_symbol_family, reference_mismatch | FAIL. The repaired SVG renders as a simple yellow slash, but the OpenCPN witness is a yellow cup/bucket-like TOPSHP17 topmark. |
| `TOPSHPJ3` | Fail | 0.92 | Redraw TOPSHPJ3 as the white TOPSHP17 cup/bucket-like topmark with visible black outline; do not emit a missing or slash-only candidate. | no_visible_art, wrong_topmark_silhouette, reference_mismatch | FAIL. The repaired SVG is effectively blank/too faint in the current render while the OpenCPN witness is a white cup/bucket-like TOPSHP17 topmark. |
| `TOPSHPP2` | Fail | 0.90 | Redraw TOPSHPP2 as a yellow plus/cross topmark, not a diagonal slash. | wrong_topmark_silhouette, wrong_symbol_family, reference_mismatch | FAIL. The repaired SVG renders as a yellow diagonal slash, but the OpenCPN witness is a yellow plus/cross topmark. |
| `TOPSHPR1` | Fail | 0.90 | Redraw TOPSHPR1 as the black trapezoid/conical topmark from the OpenCPN witness, not a diagonal slash. | wrong_topmark_silhouette, wrong_symbol_family, reference_mismatch | FAIL. The repaired SVG renders as a black diagonal slash, but the OpenCPN witness is a black trapezoid/conical topmark. |
| `TOPSHPS1` | Fail | 0.91 | Redraw TOPSHPS1 as the red/white/red target/ring topmark; do not collapse it to a black slash. | wrong_topmark_silhouette, missing_colour_pattern, reference_mismatch | FAIL. The repaired SVG renders as a black diagonal slash, but the OpenCPN witness is a target/ring topmark with red-white-red semantics. |

## Failed Symbols

- `TOPSHPI3`: Redraw TOPSHPI3 as a cross/X topmark that preserves the white/red colour cue; do not collapse it to a plain black X.
- `TOPSHPJ1`: Redraw TOPSHPJ1 as the yellow TOPSHP17 cup/bucket-like topmark from the OpenCPN witness, not a diagonal slash.
- `TOPSHPJ3`: Redraw TOPSHPJ3 as the white TOPSHP17 cup/bucket-like topmark with visible black outline; do not emit a missing or slash-only candidate.
- `TOPSHPP2`: Redraw TOPSHPP2 as a yellow plus/cross topmark, not a diagonal slash.
- `TOPSHPR1`: Redraw TOPSHPR1 as the black trapezoid/conical topmark from the OpenCPN witness, not a diagonal slash.
- `TOPSHPS1`: Redraw TOPSHPS1 as the red/white/red target/ring topmark; do not collapse it to a black slash.

## Evidence Notes

- Judged current repaired rows from owned_repair_batch51.
- Pass means judge_pass_pending_final_approval only; this artifact grants zero final approvals.
- Rows that collapsed to slash-only or lost load-bearing colour cues were failed back to repair.
