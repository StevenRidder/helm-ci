# Standard Judge Batch 080 Rerun

- Project: `vulkan`
- Task: `FORGE-15`
- Agent: `codex/FORGE-15-judge-loop-current`
- Source batch: `owned_repair_batch80`
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
| `UNITFTH1` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: fathom-unit boundary mark preserves the orange F text cue. No final approval is granted. |
| `UNITMTR1` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: metre-unit boundary mark preserves the orange M text cue. No final approval is granted. |
| `VECGND01` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: ownship course/speed-over-ground arrowhead preserves the black double-chevron cue. No final approval is granted. |
| `VECGND21` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: ARPA/AIS course/speed-over-ground arrowhead preserves the green double-chevron cue. No final approval is granted. |
| `VTCLMK01` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: vertical clearance mark preserves the black vertical gauge/clearance witness family. No final approval is granted. |
| `VECWTR01` | Fail | 0.90 | Redraw VECWTR01 as the black single-chevron through-water vector arrowhead; do not reuse the double-chevron over-ground shape. | wrong_vector_arrow_family, ground_water_vector_confusion, reference_mismatch | FAIL. The repaired SVG renders as a black double-chevron arrowhead, but the OpenCPN witness for course/speed through the water is a single-chevron arrowhead. |
| `VECWTR21` | Fail | 0.90 | Redraw VECWTR21 as the green single-chevron through-water vector arrowhead; do not reuse the double-chevron over-ground shape. | wrong_vector_arrow_family, ground_water_vector_confusion, reference_mismatch | FAIL. The repaired SVG renders as a green double-chevron arrowhead, but the OpenCPN witness for ARPA/AIS course/speed through the water is a single-chevron arrowhead. |

## Failed Symbols

- `VECWTR01`: Redraw VECWTR01 as the black single-chevron through-water vector arrowhead; do not reuse the double-chevron over-ground shape.
- `VECWTR21`: Redraw VECWTR21 as the green single-chevron through-water vector arrowhead; do not reuse the double-chevron over-ground shape.

## Evidence Notes

- Judged current repaired rows from owned_repair_batch80.
- Pass means judge_pass_pending_final_approval only; this artifact grants zero final approvals.
- Through-water vector arrows were rejected where they reused the over-ground double-chevron shape.
