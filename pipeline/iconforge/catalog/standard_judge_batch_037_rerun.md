# Standard Judge Batch 037 Rerun

- Task: FORGE-14 visual/semantic rerun for owned repair batch 37 only
- Source table: `pipeline/iconforge/catalog/standard_source_table.json`
- Source batch: `pipeline/iconforge/catalog/owned_repair_batch37.json`
- Candidate status: `repaired_pending_judge_rerun`
- Counts: 12 judged, 7 pass, 5 fail, 0 final-approved
- Approval note: pass means visual/semantic rerun pass only; rows may move to `judge_pass_pending_final_approval`, but no row is human-final-approved.

## Verdicts

| Asset | Batch | Verdict | Confidence | Required change | Safety reason codes |
| --- | ---: | --- | ---: | --- | --- |
| `RCLDEF01` | 37 | fail | 0.86 | Redraw RCLDEF01 with the central circle, two question marks, and separate upper/lower V direction witnesses; remove the continuous diamond side enclosure. | wrong_silhouette, radio_call_direction_cue_mismatch, reference_mismatch |
| `RDOCAL02` | 37 | fail | 0.93 | Redraw RDOCAL02 as a central radio-call circle with one upper triangular/V direction point; remove the closed diamond and any opposite-direction cue. | wrong_direction_semantics, wrong_silhouette, reference_mismatch |
| `RDOCAL03` | 37 | fail | 0.91 | Redraw RDOCAL03 as the central circle with separate upper and lower triangular/V direction witnesses; remove the closed diamond and vertical center stroke. | wrong_direction_semantics, wrong_silhouette, reference_mismatch |
| `RDOSTA02` | 37 | pass | 0.94 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `RECDEF51` | 37 | pass | 0.89 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `RECTRC55` | 37 | pass | 0.90 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `RECTRC56` | 37 | fail | 0.82 | Redraw RECTRC56 with a continuous vertical fixed-mark track line and opposed chevrons; remove the added center circle and broken-line treatment. | fixed_mark_semantics_mismatch, wrong_silhouette, reference_mismatch |
| `RECTRC57` | 37 | pass | 0.88 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `RECTRC58` | 37 | fail | 0.83 | Redraw RECTRC58 with a continuous vertical fixed-mark track line and one direction chevron; remove the added center circle and broken-line treatment. | fixed_mark_semantics_mismatch, wrong_silhouette, reference_mismatch |
| `RETRFL01` | 37 | pass | 0.91 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `RETRFL02` | 37 | pass | 0.90 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `RTPBCN02` | 37 | pass | 0.87 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |

## Failure Summary

- `RCLDEF01`: still carries a continuous diamond enclosure; must use separate upper/lower V witnesses with the central circle and left/right question marks.
- `RDOCAL02`: lacks the one-direction-only radio call-in silhouette; the closed diamond implies the wrong directional structure.
- `RDOCAL03`: uses a vertical center stroke instead of opposed upper/lower direction witnesses for bidirectional traffic.
- `RECTRC56`: fixed-mark two-way track distinction is not preserved; remove the center circle and use the continuous fixed-mark line.
- `RECTRC58`: fixed-mark one-way track distinction is not preserved; remove the center circle and use the continuous fixed-mark line.

## Evidence Notes

- Actual repaired SVGs were read from `pipeline/iconforge/assets/svg/owned_repair_batch37/`.
- The manifest references day/dusk/night Helm candidate renders under `pipeline/iconforge/out/standard_repair_batch29/renders/`, but those PNG render files were not present in this worktree; judgments used the actual repaired SVG geometry plus available source/reference metadata.
- Provider references used include S-101 exact/reference SVG metadata, listed OpenCPN S-52 local render paths, S-57/OpenCPN portrayal instructions, each row semantic brief, Aqua Map metadata where listed, and the prior failed judge reason in the batch catalog.
- `pipeline/iconforge/reference_providers` was not present in this branch; no extra provider files from that path were used.
- Passes remain pass-pending-human only and do not grant final approval.
