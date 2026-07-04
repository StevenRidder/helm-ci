# Standard Judge Batch 079 Rerun

- Project: `vulkan`
- Task: `FORGE-15`
- Agent: `codex/FORGE-15-judge-loop-current`
- Source batch: `owned_repair_batch79`
- Approval note: pass means `judge_pass_pending_final_approval` only; no row is human-final-approved.

## Summary

| Result | Count |
| --- | ---: |
| Selected | 15 |
| Pass pending human | 14 |
| Fail | 1 |
| Final approved | 0 |

## Verdicts

| Symbol | Verdict | Confidence | Required change | Safety reason codes | Notes |
| --- | --- | ---: | --- | --- | --- |
| `SILBUI01` | Pass pending human | 0.85 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: brown silo point mark preserves the circular silo witness. No final approval is granted. |
| `SILBUI11` | Pass pending human | 0.85 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: black conspicuous silo point mark preserves the circular witness. No final approval is granted. |
| `TMBYRD01` | Pass pending human | 0.85 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: timber-yard mark preserves the crossed-stack/hash witness. No final approval is granted. |
| `TNKFRM01` | Pass pending human | 0.85 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: tank-farm mark preserves the circle-with-four-tanks witness. No final approval is granted. |
| `TNKFRM11` | Pass pending human | 0.85 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: conspicuous tank-farm mark preserves the black circle-with-four-tanks witness. No final approval is granted. |
| `TREPNT04` | Pass pending human | 0.85 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: tree mark is a recognizable Helm-style tree matching the symbol family. No final approval is granted. |
| `TREPNT05` | Pass pending human | 0.85 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: mangrove mark preserves the low arch/root witness family. No final approval is granted. |
| `TRNBSN01` | Pass pending human | 0.85 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: turning-basin mark preserves the magenta circular-turn cue. No final approval is granted. |
| `WAYPNT01` | Pass pending human | 0.85 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: planned-route waypoint preserves the red open-circle cue. No final approval is granted. |
| `WAYPNT03` | Pass pending human | 0.85 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: alternate planned-route waypoint preserves the orange open-circle cue. No final approval is granted. |
| `WAYPNT11` | Pass pending human | 0.85 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: next planned-route waypoint preserves the concentric red target cue. No final approval is granted. |
| `WEDKLP03` | Pass pending human | 0.85 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: weed/kelp mark is a recognizable branch/kelp silhouette matching the witness family. No final approval is granted. |
| `WTLVGG01` | Pass pending human | 0.85 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: water-level gauge sign preserves the WL board-on-post cue. No final approval is granted. |
| `WTLVGG02` | Pass pending human | 0.85 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: recording water-level gauge preserves the vertical gauge/tick cue. No final approval is granted. |
| `WATTUR02` | Fail | 0.87 | Redraw WATTUR02 as the three-wave overfalls/eddies/breakers mark from the witness; keep the compact grey water-turbulence silhouette and do not collapse it to two generic waves. | wrong_wave_count, oversimplified_symbol, reference_mismatch | FAIL. The repaired SVG renders as two large grey waves, but the OpenCPN/Chart 1 witness for overfalls, eddies and breakers is a compact three-wave turbulence mark. |

## Failed Symbols

- `WATTUR02`: Redraw WATTUR02 as the three-wave overfalls/eddies/breakers mark from the witness; keep the compact grey water-turbulence silhouette and do not collapse it to two generic waves.

## Evidence Notes

- Judged current repaired rows from owned_repair_batch79.
- Pass means judge_pass_pending_final_approval only; this artifact grants zero final approvals.
- Rows that lost a witness-level symbol detail were failed back to repair.
