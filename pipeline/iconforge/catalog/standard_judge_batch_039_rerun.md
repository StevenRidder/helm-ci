# Standard Judge Batch 039 Rerun

- Project: `vulkan`
- Task: `FORGE-15`
- Agent: `codex/FORGE-15-judge-loop-current`
- Source batch: `owned_repair_batch39`
- Approval note: pass means `judge_pass_pending_final_approval` only; no row is human-final-approved.

## Summary

| Result | Count |
| --- | ---: |
| Selected | 16 |
| Pass pending human | 14 |
| Fail | 2 |
| Final approved | 0 |

## Verdicts

| Symbol | Verdict | Confidence | Required change | Safety reason codes | Notes |
| --- | --- | ---: | --- | --- | --- |
| `NMKINF25` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: secondary-waterway-left notice panel preserves the OpenCPN sign family and branch cue. No final approval is granted. |
| `NMKINF26` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: secondary-waterway/main-fairway-right notice panel preserves the OpenCPN sign family and branch cue. No final approval is granted. |
| `NMKINF27` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: secondary-waterway/main-fairway-left notice panel preserves the OpenCPN sign family and branch cue. No final approval is granted. |
| `NMKINF28` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: secondary-waterway-left/main-fairway-right notice panel preserves the OpenCPN sign family and branch cue. No final approval is granted. |
| `NMKINF29` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: secondary-waterway-right/main-fairway-left notice panel preserves the OpenCPN sign family and branch cue. No final approval is granted. |
| `NMKINF40` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: telephone notice panel is a recognizable handset-style information mark. No final approval is granted. |
| `NMKINF43` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: waterski notice panel is a recognizable skier-on-water silhouette. No final approval is granted. |
| `NMKINF44` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: sailing-boats notice panel is a recognizable sailboat silhouette. No final approval is granted. |
| `NMKINF45` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: non-powered boat notice panel is a recognizable small-boat silhouette. No final approval is granted. |
| `NMKINF46` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: windsurfing notice panel is a recognizable board-and-sail silhouette. No final approval is granted. |
| `NMKINF47` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: nautical radio notice panel preserves the VHF text cue. No final approval is granted. |
| `NMKINF48` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: waterscooter/jetski notice panel is a recognizable rider-and-watercraft silhouette. No final approval is granted. |
| `NMKINF49` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: high-speed motorboat notice panel is a recognizable fast-boat silhouette. No final approval is granted. |
| `NMKINF50` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: slipping-of-boats notice panel is a recognizable slipway/ramp-and-boat silhouette. No final approval is granted. |
| `NMKINF38` | Fail | 0.91 | Redraw NMKINF38 as the end-of-prohibition/regulation notice mark: blue square panel with one single diagonal white slash only, not an X. | wrong_notice_mark_silhouette, extra_stroke_changes_meaning, reference_mismatch | FAIL. The repaired SVG renders as a white X in a blue notice panel, but the OpenCPN/Chart 1 witness for end of prohibition or regulation is a single diagonal white slash. |
| `NMKINF53` | Fail | 0.89 | Redraw NMKINF53 as the maximum number of vessels side-by-side marker with three vertical white bars in the notice panel; do not use stacked hull shapes. | wrong_notice_mark_silhouette, wrong_symbol_family, reference_mismatch | FAIL. The repaired SVG renders as three stacked boat/hull shapes, but the witness is the maximum-number-of-vessels sign with three simple side-by-side vertical white bars. |

## Failed Symbols

- `NMKINF38`: Redraw NMKINF38 as the end-of-prohibition/regulation notice mark: blue square panel with one single diagonal white slash only, not an X.
- `NMKINF53`: Redraw NMKINF53 as the maximum number of vessels side-by-side marker with three vertical white bars in the notice panel; do not use stacked hull shapes.

## Evidence Notes

- Judged current repaired rows from owned_repair_batch39.
- Pass means judge_pass_pending_final_approval only; this artifact grants zero final approvals.
- Rows that changed the notice-mark sign meaning were failed back to repair.
