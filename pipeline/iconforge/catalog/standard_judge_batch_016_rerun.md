# Standard Judge Batch 016 Rerun

- Task: FORGE-18 visual rerun for repaired batch16 rows
- Source batch: `pipeline/iconforge/catalog/owned_repair_batch16.json`
- Candidate status: `repaired_pending_judge_rerun`
- Counts: 24 judged, 15 pass, 9 fail, 0 final-approved
- Approval note: pass means visual-rerun pass only; no row is human-final-approved.

## Verdicts

| Asset | Verdict | Confidence | Required change | Safety reason codes |
| --- | --- | ---: | --- | --- |
| `BOYCON74` | pass | 0.86 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `CAIRNS01` | pass | 0.84 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `CAIRNS11` | pass | 0.84 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `CTNARE51` | pass | 0.86 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `CTYARE51` | pass | 0.86 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `CURENT01` | fail | 0.88 | Redraw as the straight vertical current arrow with lower branching barbs; remove the curved secondary stroke. | wrong_shape, wrong_directional_structure, reference_mismatch |
| `DAYSQR21` | fail | 0.90 | Redraw to the provider-coloured square/rectangular daymark on stem with the reference base/ring detail; remove the black cross and white-panel substitution. | wrong_colour_family, invented_detail, reference_mismatch |
| `DIRBOY01` | pass | 0.80 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `DIRBOYA1` | pass | 0.82 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `DIRBOYB1` | pass | 0.82 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `DISMAR05` | pass | 0.78 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `DISMAR06` | pass | 0.76 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `DNGHILIT` | pass | 0.83 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `DOMES001` | pass | 0.84 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `DOMES011` | pass | 0.84 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `DWRUTE51` | pass | 0.86 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `EBBSTR01` | fail | 0.90 | Redraw as the upward stream-rate arrow/barb silhouette from S-101/OpenCPN; do not invert the arrow. | wrong_orientation, wrong_shape, reference_mismatch |
| `ERBLTIK1` | pass | 0.84 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `FAIRWY51` | fail | 0.90 | Redraw as the vertical outlined one-way fairway arrow from S-101/OpenCPN; remove the horizontal magenta arrow/tick substitution. | wrong_orientation, wrong_colour_family, wrong_shape, reference_mismatch |
| `FAIRWY52` | fail | 0.90 | Redraw as the vertical outlined two-way fairway arrow from S-101/OpenCPN; remove the horizontal magenta double-arrow substitution. | wrong_orientation, wrong_colour_family, wrong_shape, reference_mismatch |
| `FLDSTR01` | fail | 0.88 | Redraw with the S-101/OpenCPN upward flood-stream arrow and side-barb/rate cue; remove the double horizontal crossbars. | wrong_shape, missing_rate_barb, reference_mismatch |
| `FLGSTF01` | fail | 0.86 | Redraw as the brown/gold flagstaff/flagpole witness with the reference flag shape and base/ring detail; remove the black/white generic flag substitution. | wrong_colour_family, missing_base_detail, reference_mismatch |
| `FOULGND1` | fail | 0.87 | Redraw as the open foul-ground hash/slash reference mark; remove the enclosing square and radial star-like structure. | wrong_shape, invented_enclosure, unsafe_symbol_confusion, reference_mismatch |
| `INFORM01` | fail | 0.89 | Redraw as the reference information marker with boxed i/glyph plus leader line and origin circle; do not use a standalone circled i. | wrong_shape, missing_leader_line, missing_origin_marker, reference_mismatch |

## Failure Summary

- `CURENT01`: Redraw as the straight vertical current arrow with lower branching barbs; remove the curved secondary stroke. Codes: wrong_shape, wrong_directional_structure, reference_mismatch.
- `DAYSQR21`: Redraw to the provider-coloured square/rectangular daymark on stem with the reference base/ring detail; remove the black cross and white-panel substitution. Codes: wrong_colour_family, invented_detail, reference_mismatch.
- `EBBSTR01`: Redraw as the upward stream-rate arrow/barb silhouette from S-101/OpenCPN; do not invert the arrow. Codes: wrong_orientation, wrong_shape, reference_mismatch.
- `FAIRWY51`: Redraw as the vertical outlined one-way fairway arrow from S-101/OpenCPN; remove the horizontal magenta arrow/tick substitution. Codes: wrong_orientation, wrong_colour_family, wrong_shape, reference_mismatch.
- `FAIRWY52`: Redraw as the vertical outlined two-way fairway arrow from S-101/OpenCPN; remove the horizontal magenta double-arrow substitution. Codes: wrong_orientation, wrong_colour_family, wrong_shape, reference_mismatch.
- `FLDSTR01`: Redraw with the S-101/OpenCPN upward flood-stream arrow and side-barb/rate cue; remove the double horizontal crossbars. Codes: wrong_shape, missing_rate_barb, reference_mismatch.
- `FLGSTF01`: Redraw as the brown/gold flagstaff/flagpole witness with the reference flag shape and base/ring detail; remove the black/white generic flag substitution. Codes: wrong_colour_family, missing_base_detail, reference_mismatch.
- `FOULGND1`: Redraw as the open foul-ground hash/slash reference mark; remove the enclosing square and radial star-like structure. Codes: wrong_shape, invented_enclosure, unsafe_symbol_confusion, reference_mismatch.
- `INFORM01`: Redraw as the reference information marker with boxed i/glyph plus leader line and origin circle; do not use a standalone circled i. Codes: wrong_shape, missing_leader_line, missing_origin_marker, reference_mismatch.

## Passed Assets

`BOYCON74`, `CAIRNS01`, `CAIRNS11`, `CTNARE51`, `CTYARE51`, `DIRBOY01`, `DIRBOYA1`, `DIRBOYB1`, `DISMAR05`, `DISMAR06`, `DNGHILIT`, `DOMES001`, `DOMES011`, `DWRUTE51`, `ERBLTIK1`
