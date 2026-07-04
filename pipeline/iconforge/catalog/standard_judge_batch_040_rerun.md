# Standard Judge Batch 040 Rerun

- Task: FORGE-14 visual/semantic rerun for repaired owned batch 40 only
- Source table: `pipeline/iconforge/catalog/standard_source_table.json`
- Source batch: `pipeline/iconforge/catalog/owned_repair_batch40.json`
- Prior critique: `pipeline/iconforge/catalog/standard_judge_batch_037_rerun.json`
- Candidate status: `repaired_pending_judge_rerun`
- Counts: 5 judged, 5 pass, 0 fail, 0 final-approved
- Approval note: pass means visual/semantic rerun pass only; rows may move to `judge_pass_pending_final_approval`, but no row is human-final-approved.

## Verdicts

| Asset | Batch | Verdict | Confidence | Required change | Safety reason codes |
| --- | ---: | --- | ---: | --- | --- |
| `RCLDEF01` | 40 | pass | 0.92 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `RDOCAL02` | 40 | pass | 0.91 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `RDOCAL03` | 40 | pass | 0.92 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `RECTRC56` | 40 | pass | 0.90 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `RECTRC58` | 40 | pass | 0.90 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |

## Pass Notes

- `RCLDEF01`: central radio-call circle, left/right question marks, and separate upper/lower open V witnesses are present; the prior closed diamond side enclosure is gone.
- `RDOCAL02`: central radio-call circle plus one upper open V witness is present; there is no opposite-direction cue and no closed diamond enclosure.
- `RDOCAL03`: central radio-call circle plus separate upper/lower open V witnesses are present; there is no vertical center stroke and no closed diamond enclosure.
- `RECTRC56`: fixed-mark track row now uses a continuous vertical line with two opposed chevrons; there is no center dot/circle and no broken-line treatment.
- `RECTRC58`: fixed-mark track row now uses a continuous vertical line with one direction chevron; there is no center dot/circle and no broken-line treatment.

## Evidence Notes

- Actual repaired SVGs were read from `pipeline/iconforge/assets/svg/owned_repair_batch40/`.
- Candidate day/dusk/night renders were present under `pipeline/iconforge/out/standard_repair_batch32/renders/` and checked against the SVG geometry.
- Provider references used include the row semantic briefs, S-57/OpenCPN portrayal instructions, S-101 exact/reference metadata, OpenCPN S-52 local render paths, Aqua Map metadata where listed, and Curie's prior batch 037 failed judge reasons.
- The OpenCPN reference rasters retain small-scale raster artifacts and differ in stroke weight; minor Helm style differences were accepted only where the recognisable marine symbol semantics remained correct.
- Passes remain pass-pending-human only and do not grant final approval.
