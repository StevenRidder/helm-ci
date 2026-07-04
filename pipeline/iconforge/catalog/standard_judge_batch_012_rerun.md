# standard_judge_batch_012_rerun

Visual rerun after owned batch12 repairs. No SVGs edited. No rows final-approved.

- Selected rows: 9
- Pass: 6
- Fail/blocker: 3
- Status inputs: repaired_pending_judge_rerun=9 from catalog/owned_repair_batch12.json

| Symbol | Input status | Pass | Confidence | Observed | Required change | Safety codes |
|---|---:|---:|---:|---|---|---|
| BOYCAN81 | repaired_pending_judge_rerun | yes | 0.91 | Can/cylindrical buoy with orange upper band, white lower band, black outline, and black stem. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| BOYCON74 | repaired_pending_judge_rerun | no | 0.84 | Conical/nun buoy body now has green-white-green-white-green fills, but grey horizontal separator strokes protrude well outside both sides of the cone. | Clip or remove the separator strokes so no grey horizontal bars protrude outside the conical silhouette; preserve the ordered green-white-green-white-green body. | visual_artifact, unclipped_separator_strokes, reference_mismatch |
| BOYCON81 | repaired_pending_judge_rerun | no | 0.78 | Conical/nun buoy with blue-red-white-blue horizontal colour order and translucent vertical overlays, plus grey grid/separator strokes protruding outside the body. | Resolve BOYCON81's exact special-purpose stripe pattern against the reference render, then clip or remove all grid/separator strokes outside the conical silhouette. | wrong_pattern, visual_artifact, unclipped_separator_strokes, unsafe_special_purpose_confusion |
| BOYINB01 | repaired_pending_judge_rerun | yes | 0.88 | Black installation-buoy line symbol with top ring, lower ring, baseline arms, and trapezoid frame. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| BOYISD12 | repaired_pending_judge_rerun | yes | 0.90 | Two red circular isolated-danger disks with black outlines, arranged diagonally. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| BOYMOR01 | repaired_pending_judge_rerun | yes | 0.86 | Black mooring facility line cue with upper ring, lower ring, arched body stroke, and baseline arms. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| BOYMOR11 | repaired_pending_judge_rerun | yes | 0.88 | Compact black simplified mooring symbol: filled trapezoid body with a black top disk. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| BOYPIL78 | repaired_pending_judge_rerun | no | 0.82 | Pillar buoy body now uses a red/white squared pattern, but grey vertical and horizontal grid strokes protrude outside the body like scaffolding. | Clip or remove the checker/grid separator strokes so they stay inside the pillar body; preserve the red-white squared/checkered pattern. | visual_artifact, unclipped_grid_strokes, reference_mismatch |
| BOYSAW12 | repaired_pending_judge_rerun | yes | 0.90 | Compact red disk with black outline and small black center point. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |

## Blockers

- None. The three failures are concrete visual-parity repair items, not missing-reference blockers.
