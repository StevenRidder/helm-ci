# Standard Judge Batch 092 Rerun

- Project: `vulkan`
- Task: `FORGE-15`
- Agent: `codex/FORGE-15-judge-loop-current`
- Source batch: `owned_repair_batch92`
- Approval note: pass means `judge_pass_pending_final_approval` only; no row is human-final-approved.

## Summary

| Result | Count |
| --- | ---: |
| Selected | 20 |
| Pass pending human | 4 |
| Fail to repair queue | 16 |
| Final approved | 0 |

## Verdicts

| Symbol | Verdict | Confidence | Required change | Safety reason codes |
| --- | --- | ---: | --- | --- |
| `CBLSUB06` | Fail to repair | 0.84 | Add the small terminal slash/kink seen in the OpenCPN cable witness and tighten the wave cadence; current candidate is close but too generic. | visual_parity_mismatch, reference_witness_not_followed, repairable_batch92_candidate |
| `CLRLIN01` | Pass pending human | 0.88 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `CROSSX02` | Fail to repair | 0.84 | Replace the large grid with a tight small-dot/cross fill matching the dense OpenCPN witness; keep the marks tiny at chart scale. | visual_parity_mismatch, reference_witness_not_followed, repairable_batch92_candidate |
| `DIAMOND1` | Fail to repair | 0.84 | Use the OpenCPN crossed-line witness for depth-less-than-safety-contour, not a four-diamond cluster. | visual_parity_mismatch, reference_witness_not_followed, repairable_batch92_candidate |
| `DQUALA11` | Fail to repair | 0.84 | Recreate the triangular outlined survey-quality stamp with internal star/cross marks; do not use two free triangles plus a plus sign. | visual_parity_mismatch, reference_witness_not_followed, repairable_batch92_candidate |
| `DQUALA21` | Fail to repair | 0.84 | Recreate the triangular outlined survey-quality stamp with internal star/cross marks and the lower bar cue from the witness. | visual_parity_mismatch, reference_witness_not_followed, repairable_batch92_candidate |
| `DQUALB01` | Fail to repair | 0.84 | Use the triangular outlined survey-quality witness, not three horizontal bars. | visual_parity_mismatch, reference_witness_not_followed, repairable_batch92_candidate |
| `DQUALC01` | Fail to repair | 0.84 | Use the rounded capsule witness with three internal star/cross marks; current free plus marks miss the enclosure. | visual_parity_mismatch, reference_witness_not_followed, repairable_batch92_candidate |
| `DQUALD01` | Fail to repair | 0.84 | Use the rounded capsule witness with internal star/cross marks; current dashed triangle is the wrong family. | visual_parity_mismatch, reference_witness_not_followed, repairable_batch92_candidate |
| `DQUALU01` | Fail to repair | 0.84 | Keep the rounded capsule and add the centered U glyph seen in the OpenCPN witness. | visual_parity_mismatch, reference_witness_not_followed, repairable_batch92_candidate |
| `DWLDEF01` | Fail to repair | 0.84 | Align the magenta route line, angle-bracket cue, question mark, and DW label to match the OpenCPN witness; current line/label placement is too simplified. | visual_parity_mismatch, reference_witness_not_followed, repairable_batch92_candidate |
| `DWRTCL05` | Fail to repair | 0.84 | Match the two-way deep-water route witness: thin magenta line, bracket/arrow cues, and DW label placement; current arrows are too large. | visual_parity_mismatch, reference_witness_not_followed, repairable_batch92_candidate |
| `DWRTCL06` | Fail to repair | 0.84 | Match the fixed-mark two-way deep-water route witness with the correct line/arrow cadence and DW placement; current arrows are too large. | visual_parity_mismatch, reference_witness_not_followed, repairable_batch92_candidate |
| `DWRTCL07` | Fail to repair | 0.84 | Match the one-way deep-water route witness with small right-arrow cue and DW label; current arrow/label scale is too large. | visual_parity_mismatch, reference_witness_not_followed, repairable_batch92_candidate |
| `DWRTCL08` | Fail to repair | 0.84 | Match the fixed-mark one-way deep-water route witness with small right-arrow cue and DW label; current arrow/label scale is too large. | visual_parity_mismatch, reference_witness_not_followed, repairable_batch92_candidate |
| `ERBLNA01` | Pass pending human | 0.88 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `ERBLNB01` | Pass pending human | 0.88 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `FERYRT01` | Fail to repair | 0.84 | Use the ferry-route witness: magenta dashed line with the small vessel/route cue, not an F text label. | visual_parity_mismatch, reference_witness_not_followed, repairable_batch92_candidate |
| `FERYRT02` | Fail to repair | 0.84 | Use the cable-ferry witness: grey dashed line with compact boat/box cue centered on the line; current rectangle is close but too large and not integrated. | visual_parity_mismatch, reference_witness_not_followed, repairable_batch92_candidate |
| `FOULAR01` | Pass pending human | 0.88 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |

## Evidence Notes

- Judged current repaired rows from owned_repair_batch92 against provider witnesses and semantic metadata.
- Pass means judge_pass_pending_final_approval only; this artifact grants zero final approvals.
- Failures are strict visual-parity failures, not final row rejections.
