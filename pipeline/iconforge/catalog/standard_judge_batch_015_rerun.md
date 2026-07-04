# Standard Judge Batch 015 Rerun

- Task: FORGE-18 visual rerun for repaired batch15 rows
- Source batch: `pipeline/iconforge/catalog/owned_repair_batch15.json`
- Candidate status: `repaired_pending_judge_rerun`
- Counts: 35 judged, 21 pass, 14 fail, 0 final-approved
- Approval note: pass means visual-rerun pass only; no row is human-final-approved.

## Verdicts

| Asset | Verdict | Confidence | Required change | Safety reason codes |
| --- | --- | ---: | --- | --- |
| `BOYSPR01` | pass | 0.84 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `BOYSPR70` | pass | 0.86 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `BOYSPR71` | pass | 0.86 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `BOYSPR72` | pass | 0.86 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `BRTHNO01` | pass | 0.78 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `BUAARE02` | fail | 0.88 | Redraw as a single compact brown filled built-up-area dot/area cue; remove the multi-circle cluster and baseline. | wrong_shape, invented_detail, reference_mismatch |
| `BUIREL01` | fail | 0.87 | Redraw to the brown Christian religious-building schematic silhouette from OpenCPN/S-101 rather than a plain Latin cross. | wrong_shape, reference_mismatch |
| `BUIREL04` | fail | 0.90 | Redraw to the brown non-Christian religious-building rectangular/hourglass schematic; remove the dome and cross-like top. | wrong_shape, wrong_religious_variant, reference_mismatch |
| `BUIREL05` | fail | 0.88 | Redraw to the brown mosque/minaret reference silhouette: crescent over stem with circular base/dot, without extra side minarets. | wrong_shape, invented_detail, reference_mismatch |
| `BUIREL13` | fail | 0.87 | Redraw to the conspicuous black Christian religious-building schematic silhouette from OpenCPN/S-101 rather than a plain Latin cross. | wrong_shape, reference_mismatch |
| `BUIREL14` | fail | 0.90 | Redraw to the conspicuous black non-Christian rectangular/hourglass schematic; remove the dome and cross-like top. | wrong_shape, wrong_religious_variant, reference_mismatch |
| `BUIREL15` | fail | 0.88 | Redraw to the conspicuous black mosque/minaret reference silhouette: crescent over stem with circular base/dot, without extra side minarets. | wrong_shape, invented_detail, reference_mismatch |
| `BUISGL01` | pass | 0.84 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `BUISGL11` | pass | 0.84 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `BUNSTA02` | fail | 0.86 | Redraw to the OpenCPN water bunker-station bucket/barrel silhouette with blue water band; avoid a standalone faucet/droplet pictogram. | wrong_shape, invented_generic_icon, reference_mismatch |
| `BUNSTA03` | fail | 0.85 | Redraw as a readable ballast-station cube/box service symbol with visible face/grid divisions instead of a solid filled mass. | wrong_shape, lost_internal_structure, reference_mismatch |
| `CBLARE51` | pass | 0.80 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `CHCRDEL1` | pass | 0.83 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `CHCRID01` | pass | 0.86 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `CHINFO06` | pass | 0.85 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `CHINFO07` | pass | 0.85 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `CHINFO08` | pass | 0.85 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `CHINFO09` | pass | 0.85 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `CHINFO10` | pass | 0.85 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `CHINFO11` | pass | 0.85 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `CHKSYM01` | pass | 0.82 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `CURSRA01` | pass | 0.88 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `CURSRB01` | fail | 0.90 | Remove the circular center ring and render four separated orange cursor arms with an open center gap. | wrong_shape, invented_detail, reference_mismatch |
| `CUSTOM01` | fail | 0.88 | Redraw as a single red/white customs roundel with the central white band; do not use overlapping circles. | wrong_shape, wrong_colour_pattern, reference_mismatch |
| `DANGER51` | pass | 0.79 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `DANGER52` | pass | 0.76 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved; revisit only if a stronger exact DANGER52 witness rejects the center dot. | - |
| `DAYSQR01` | fail | 0.90 | Redraw as the provider-colored square/rectangular daymark on stem and remove the invented horizontal bar. | wrong_colour_family, invented_detail, reference_mismatch |
| `DAYTRI01` | fail | 0.88 | Redraw the point-up triangular daymark with the provider color family while preserving upright orientation and stem. | wrong_colour_family, reference_mismatch |
| `DAYTRI05` | fail | 0.88 | Redraw the point-down triangular daymark with the provider color family while preserving inverted orientation and stem. | wrong_colour_family, reference_mismatch |
| `EBLVRM11` | pass | 0.80 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |

## Failure Summary

- `BUAARE02`: Redraw as a single compact brown filled built-up-area dot/area cue; remove the multi-circle cluster and baseline. Codes: wrong_shape, invented_detail, reference_mismatch.
- `BUIREL01`: Redraw to the brown Christian religious-building schematic silhouette from OpenCPN/S-101 rather than a plain Latin cross. Codes: wrong_shape, reference_mismatch.
- `BUIREL04`: Redraw to the brown non-Christian religious-building rectangular/hourglass schematic; remove the dome and cross-like top. Codes: wrong_shape, wrong_religious_variant, reference_mismatch.
- `BUIREL05`: Redraw to the brown mosque/minaret reference silhouette: crescent over stem with circular base/dot, without extra side minarets. Codes: wrong_shape, invented_detail, reference_mismatch.
- `BUIREL13`: Redraw to the conspicuous black Christian religious-building schematic silhouette from OpenCPN/S-101 rather than a plain Latin cross. Codes: wrong_shape, reference_mismatch.
- `BUIREL14`: Redraw to the conspicuous black non-Christian rectangular/hourglass schematic; remove the dome and cross-like top. Codes: wrong_shape, wrong_religious_variant, reference_mismatch.
- `BUIREL15`: Redraw to the conspicuous black mosque/minaret reference silhouette: crescent over stem with circular base/dot, without extra side minarets. Codes: wrong_shape, invented_detail, reference_mismatch.
- `BUNSTA02`: Redraw to the OpenCPN water bunker-station bucket/barrel silhouette with blue water band; avoid a standalone faucet/droplet pictogram. Codes: wrong_shape, invented_generic_icon, reference_mismatch.
- `BUNSTA03`: Redraw as a readable ballast-station cube/box service symbol with visible face/grid divisions instead of a solid filled mass. Codes: wrong_shape, lost_internal_structure, reference_mismatch.
- `CURSRB01`: Remove the circular center ring and render four separated orange cursor arms with an open center gap. Codes: wrong_shape, invented_detail, reference_mismatch.
- `CUSTOM01`: Redraw as a single red/white customs roundel with the central white band; do not use overlapping circles. Codes: wrong_shape, wrong_colour_pattern, reference_mismatch.
- `DAYSQR01`: Redraw as the provider-colored square/rectangular daymark on stem and remove the invented horizontal bar. Codes: wrong_colour_family, invented_detail, reference_mismatch.
- `DAYTRI01`: Redraw the point-up triangular daymark with the provider color family while preserving upright orientation and stem. Codes: wrong_colour_family, reference_mismatch.
- `DAYTRI05`: Redraw the point-down triangular daymark with the provider color family while preserving inverted orientation and stem. Codes: wrong_colour_family, reference_mismatch.

## Passed Assets

`BOYSPR01`, `BOYSPR70`, `BOYSPR71`, `BOYSPR72`, `BRTHNO01`, `BUISGL01`, `BUISGL11`, `CBLARE51`, `CHCRDEL1`, `CHCRID01`, `CHINFO06`, `CHINFO07`, `CHINFO08`, `CHINFO09`, `CHINFO10`, `CHINFO11`, `CHKSYM01`, `CURSRA01`, `DANGER51`, `DANGER52`, `EBLVRM11`
