# Standard Judge Batch 017 Rerun

- Task: FORGE-18 visual rerun for repaired batch17 rows
- Source batch: `pipeline/iconforge/catalog/owned_repair_batch17.json`
- Candidate status: `repaired_pending_judge_rerun`
- Counts: 26 judged, 5 pass, 21 fail, 0 final-approved
- Approval note: pass means visual-rerun pass only; no row is human-final-approved.

## Verdicts

| Asset | Verdict | Confidence | Required change | Safety reason codes |
| --- | --- | ---: | --- | --- |
| `BUAARE02` | pass | 0.78 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `BUIREL01` | fail | 0.88 | Redraw as the compact brown Christian religious-building witness shape from S-101/OpenCPN; remove the church-outline body and baseline. | wrong_shape, invented_building_outline, reference_mismatch |
| `BUIREL04` | fail | 0.90 | Redraw as the brown horizontal non-Christian religious-building rectangle/hourglass witness; remove the vertical hourglass orientation and baseline. | wrong_orientation, wrong_shape, invented_baseline, reference_mismatch |
| `BUIREL05` | fail | 0.88 | Redraw with the crescent over the stem and the circular base/dot cue from the S-101/OpenCPN mosque/minaret witness; do not use a side moon glyph. | wrong_crescent_orientation, missing_circular_base, reference_mismatch |
| `BUIREL13` | fail | 0.88 | Redraw as the compact black conspicuous Christian religious-building witness shape from S-101/OpenCPN; remove the church-outline body and baseline. | wrong_shape, invented_building_outline, reference_mismatch |
| `BUIREL14` | fail | 0.90 | Redraw as the black horizontal conspicuous non-Christian religious-building rectangle/hourglass witness; remove the vertical orientation and baseline. | wrong_orientation, wrong_shape, invented_baseline, reference_mismatch |
| `BUIREL15` | fail | 0.88 | Redraw with the black crescent over the stem and the circular base/dot cue from the conspicuous mosque/minaret witness; do not use a side moon glyph. | wrong_crescent_orientation, missing_circular_base, reference_mismatch |
| `CHIMNY01` | fail | 0.86 | Redraw the brown chimney with vertical stack, top smoke form, and the base ring/dot marker; keep the chimney class instead of a generic tower. | missing_base_ring, incomplete_top_smoke, reference_mismatch |
| `CHIMNY11` | fail | 0.86 | Redraw the black conspicuous chimney with vertical stack, top smoke form, and the base ring/dot marker. | missing_base_ring, incomplete_top_smoke, reference_mismatch |
| `CURSRB01` | fail | 0.92 | Remove the center dot and leave a clean open gap between the four orange cursor arms. | missing_open_centre, invented_center_dot, reference_mismatch |
| `DAYSQR01` | fail | 0.90 | Redraw as the provider-coloured square/rectangular daymark on stem, including the lower node/base cue where present; do not use a black generic dayboard. | wrong_colour_family, missing_base_node, reference_mismatch |
| `DAYTRI01` | fail | 0.90 | Redraw the point-up triangular daymark in the provider/reference color family while preserving the upright triangle and stem. | wrong_colour_family, reference_mismatch |
| `DAYTRI05` | fail | 0.90 | Redraw the point-down triangular daymark in the provider/reference color family while preserving the inverted triangle and stem. | wrong_colour_family, reference_mismatch |
| `DSHAER01` | pass | 0.80 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `DSHAER11` | pass | 0.80 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `FLASTK01` | pass | 0.82 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `FLASTK11` | pass | 0.82 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `FORSTC01` | fail | 0.88 | Redraw as the brown fortified-structure square/outline witness from S-101/OpenCPN; remove the crenellated castle top and baseline. | wrong_shape, invented_crenellations, reference_mismatch |
| `FORSTC11` | fail | 0.88 | Redraw as the black conspicuous fortified-structure square/outline witness from S-101/OpenCPN; remove the crenellated castle top and baseline. | wrong_shape, invented_crenellations, reference_mismatch |
| `HILTOP01` | fail | 0.92 | Redraw as the brown radial hill/mountain-top starburst witness; remove the mountain-arch silhouette. | wrong_symbol_shape, substituted_landform_icon, reference_mismatch |
| `HILTOP11` | fail | 0.92 | Redraw as the black radial conspicuous hill/mountain-top starburst witness; remove the mountain-arch silhouette. | wrong_symbol_shape, substituted_landform_icon, reference_mismatch |
| `LOCMAG01` | fail | 0.92 | Redraw as the LOCMAG01 magenta wedge/line magnetic-anomaly point witness; remove the enclosing circle and internal diamond. | wrong_shape, invented_enclosure, reference_mismatch |
| `LOCMAG51` | fail | 0.90 | Redraw as the LOCMAG51 magenta magnetic-anomaly line/area wedge/line witness; remove the dashed arch and T-base substitution. | wrong_shape, invented_arch, reference_mismatch |
| `LOWACC01` | fail | 0.90 | Redraw as the low-accuracy contour question-mark with diagonal line/leader cue; remove the dashed arc. | missing_diagonal_line, invented_contour_arc, reference_mismatch |
| `MAGVAR01` | fail | 0.92 | Redraw as the MAGVAR01 magenta wedge/line magnetic-variation point glyph; remove the arrow and crossbar. | wrong_shape, wrong_directional_structure, reference_mismatch |
| `MAGVAR51` | fail | 0.92 | Redraw as the MAGVAR51 magenta magnetic-variation line/area wedge/line glyph; remove the arrow and dashed arc. | wrong_shape, wrong_directional_structure, reference_mismatch |

## Failure Summary

- `BUIREL01`: Redraw as the compact brown Christian religious-building witness shape from S-101/OpenCPN; remove the church-outline body and baseline. Codes: wrong_shape, invented_building_outline, reference_mismatch.
- `BUIREL04`: Redraw as the brown horizontal non-Christian religious-building rectangle/hourglass witness; remove the vertical hourglass orientation and baseline. Codes: wrong_orientation, wrong_shape, invented_baseline, reference_mismatch.
- `BUIREL05`: Redraw with the crescent over the stem and the circular base/dot cue from the S-101/OpenCPN mosque/minaret witness; do not use a side moon glyph. Codes: wrong_crescent_orientation, missing_circular_base, reference_mismatch.
- `BUIREL13`: Redraw as the compact black conspicuous Christian religious-building witness shape from S-101/OpenCPN; remove the church-outline body and baseline. Codes: wrong_shape, invented_building_outline, reference_mismatch.
- `BUIREL14`: Redraw as the black horizontal conspicuous non-Christian religious-building rectangle/hourglass witness; remove the vertical orientation and baseline. Codes: wrong_orientation, wrong_shape, invented_baseline, reference_mismatch.
- `BUIREL15`: Redraw with the black crescent over the stem and the circular base/dot cue from the conspicuous mosque/minaret witness; do not use a side moon glyph. Codes: wrong_crescent_orientation, missing_circular_base, reference_mismatch.
- `CHIMNY01`: Redraw the brown chimney with vertical stack, top smoke form, and the base ring/dot marker; keep the chimney class instead of a generic tower. Codes: missing_base_ring, incomplete_top_smoke, reference_mismatch.
- `CHIMNY11`: Redraw the black conspicuous chimney with vertical stack, top smoke form, and the base ring/dot marker. Codes: missing_base_ring, incomplete_top_smoke, reference_mismatch.
- `CURSRB01`: Remove the center dot and leave a clean open gap between the four orange cursor arms. Codes: missing_open_centre, invented_center_dot, reference_mismatch.
- `DAYSQR01`: Redraw as the provider-coloured square/rectangular daymark on stem, including the lower node/base cue where present; do not use a black generic dayboard. Codes: wrong_colour_family, missing_base_node, reference_mismatch.
- `DAYTRI01`: Redraw the point-up triangular daymark in the provider/reference color family while preserving the upright triangle and stem. Codes: wrong_colour_family, reference_mismatch.
- `DAYTRI05`: Redraw the point-down triangular daymark in the provider/reference color family while preserving the inverted triangle and stem. Codes: wrong_colour_family, reference_mismatch.
- `FORSTC01`: Redraw as the brown fortified-structure square/outline witness from S-101/OpenCPN; remove the crenellated castle top and baseline. Codes: wrong_shape, invented_crenellations, reference_mismatch.
- `FORSTC11`: Redraw as the black conspicuous fortified-structure square/outline witness from S-101/OpenCPN; remove the crenellated castle top and baseline. Codes: wrong_shape, invented_crenellations, reference_mismatch.
- `HILTOP01`: Redraw as the brown radial hill/mountain-top starburst witness; remove the mountain-arch silhouette. Codes: wrong_symbol_shape, substituted_landform_icon, reference_mismatch.
- `HILTOP11`: Redraw as the black radial conspicuous hill/mountain-top starburst witness; remove the mountain-arch silhouette. Codes: wrong_symbol_shape, substituted_landform_icon, reference_mismatch.
- `LOCMAG01`: Redraw as the LOCMAG01 magenta wedge/line magnetic-anomaly point witness; remove the enclosing circle and internal diamond. Codes: wrong_shape, invented_enclosure, reference_mismatch.
- `LOCMAG51`: Redraw as the LOCMAG51 magenta magnetic-anomaly line/area wedge/line witness; remove the dashed arch and T-base substitution. Codes: wrong_shape, invented_arch, reference_mismatch.
- `LOWACC01`: Redraw as the low-accuracy contour question-mark with diagonal line/leader cue; remove the dashed arc. Codes: missing_diagonal_line, invented_contour_arc, reference_mismatch.
- `MAGVAR01`: Redraw as the MAGVAR01 magenta wedge/line magnetic-variation point glyph; remove the arrow and crossbar. Codes: wrong_shape, wrong_directional_structure, reference_mismatch.
- `MAGVAR51`: Redraw as the MAGVAR51 magenta magnetic-variation line/area wedge/line glyph; remove the arrow and dashed arc. Codes: wrong_shape, wrong_directional_structure, reference_mismatch.

## Passed Assets

`BUAARE02`, `DSHAER01`, `DSHAER11`, `FLASTK01`, `FLASTK11`
