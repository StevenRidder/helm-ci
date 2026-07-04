# Standard Judge Batch 019 Rerun

- Task: FORGE-18 visual rerun for repaired batch19 rows
- Source batch: `pipeline/iconforge/catalog/owned_repair_batch19.json`
- Candidate status: `repaired_pending_judge_rerun`
- Counts: 26 judged, 8 pass, 18 fail, 0 final-approved
- Approval note: pass means visual-rerun pass only; no row is human-final-approved.

## Verdicts

| Asset | Verdict | Confidence | Required change | Safety reason codes |
| --- | --- | ---: | --- | --- |
| `BOYSUP01` | fail | 0.88 | Super-buoy symbol must use the low platform/trapezoid body with ring cue from the references; reduce the tall buoy body and preserve red/black load-bearing colors. | wrong_shape, unsafe_buoy_family_confusion, reference_mismatch |
| `BOYSUP02` | fail | 0.88 | Redraw BOYSUP02 as the black low platform/trapezoid super-buoy silhouette with the reference ring/body proportions, not a tall generic buoy body. | wrong_shape, unsafe_buoy_family_confusion, reference_mismatch |
| `BOYSUP03` | fail | 0.86 | Keep the LANBY star/asterisk topmark and red/black semantics, but redraw the body as the low super-buoy platform/trapezoid reference silhouette. | wrong_shape, reference_mismatch |
| `BUIREL01` | fail | 0.88 | Redraw as the compact brown Christian religious-building witness shape from S-101/OpenCPN; remove the long stem and circular base ring. | wrong_shape, invented_stem_ring, reference_mismatch |
| `BUIREL04` | pass | 0.80 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `BUIREL05` | fail | 0.88 | Redraw with the crescent over the stem and the circular base/dot cue from the S-101/OpenCPN mosque/minaret witness; do not use a side moon glyph. | wrong_crescent_orientation, missing_circular_base, reference_mismatch |
| `BUIREL13` | fail | 0.88 | Redraw as the compact black conspicuous Christian religious-building witness shape from S-101/OpenCPN; remove the long stem and circular base ring. | wrong_shape, invented_stem_ring, reference_mismatch |
| `BUIREL14` | pass | 0.80 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `BUIREL15` | fail | 0.88 | Redraw with the black crescent over the stem and the circular base/dot cue from the conspicuous mosque/minaret witness; do not use a side moon glyph. | wrong_crescent_orientation, missing_circular_base, reference_mismatch |
| `CHIMNY01` | pass | 0.82 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `CHIMNY11` | pass | 0.82 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `CURSRB01` | pass | 0.84 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `CUSTOM01` | pass | 0.78 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `DAYSQR01` | fail | 0.90 | Redraw as the provider/reference-colored square or rectangular daymark on stem, including the lower node/base cue; do not use a black/yellow generic dayboard. | wrong_colour_family, wrong_style_family, reference_mismatch |
| `DAYTRI01` | fail | 0.88 | Redraw the point-up triangular daymark in the provider/reference color family while preserving the upright triangle and stem. | wrong_colour_family, reference_mismatch |
| `DAYTRI05` | fail | 0.88 | Redraw the point-down triangular daymark in the provider/reference color family while preserving the inverted triangle and stem. | wrong_colour_family, reference_mismatch |
| `ESSARE01` | fail | 0.90 | Replace the boxed ESSA sign with the ESSA/PSSA boundary text/line marker from the references; remove the invented enclosure and baseline decoration. | wrong_symbol_class, invented_enclosure, reference_mismatch |
| `FORSTC01` | fail | 0.86 | Redraw as the brown fortified-structure square/outline witness from S-101/OpenCPN; remove invented internal bars. | invented_internal_marks, wrong_shape, reference_mismatch |
| `FORSTC11` | fail | 0.86 | Redraw as the black conspicuous fortified-structure square/outline witness from S-101/OpenCPN; remove invented internal bars. | invented_internal_marks, wrong_shape, reference_mismatch |
| `HILTOP01` | pass | 0.80 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `HILTOP11` | pass | 0.80 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `LOCMAG01` | fail | 0.92 | Redraw as the LOCMAG01 magenta wedge/line magnetic-anomaly point witness; remove the A/M sign, crossbar, and dot. | wrong_shape, invented_text, reference_mismatch |
| `LOCMAG51` | fail | 0.92 | Redraw as the LOCMAG51 magenta magnetic-anomaly line/area wedge/line witness; remove the A/M sign and invented baseline marks. | wrong_shape, invented_text, reference_mismatch |
| `LOWACC01` | fail | 0.86 | Keep the question-mark plus diagonal line/leader cue, but remove the invented dashed baseline/contour segment. | invented_baseline, reference_mismatch |
| `MAGVAR01` | fail | 0.92 | Redraw as the MAGVAR01 magenta wedge/line magnetic-variation point glyph; remove the A/V sign, crossbar, and dot. | wrong_shape, invented_text, reference_mismatch |
| `MAGVAR51` | fail | 0.92 | Redraw as the MAGVAR51 magenta magnetic-variation line/area wedge/line glyph; remove the A/V sign and invented baseline marks. | wrong_shape, invented_text, reference_mismatch |

## Failure Summary

- `BOYSUP01`: Super-buoy symbol must use the low platform/trapezoid body with ring cue from the references; reduce the tall buoy body and preserve red/black load-bearing colors. Codes: wrong_shape, unsafe_buoy_family_confusion, reference_mismatch.
- `BOYSUP02`: Redraw BOYSUP02 as the black low platform/trapezoid super-buoy silhouette with the reference ring/body proportions, not a tall generic buoy body. Codes: wrong_shape, unsafe_buoy_family_confusion, reference_mismatch.
- `BOYSUP03`: Keep the LANBY star/asterisk topmark and red/black semantics, but redraw the body as the low super-buoy platform/trapezoid reference silhouette. Codes: wrong_shape, reference_mismatch.
- `BUIREL01`: Redraw as the compact brown Christian religious-building witness shape from S-101/OpenCPN; remove the long stem and circular base ring. Codes: wrong_shape, invented_stem_ring, reference_mismatch.
- `BUIREL05`: Redraw with the crescent over the stem and the circular base/dot cue from the S-101/OpenCPN mosque/minaret witness; do not use a side moon glyph. Codes: wrong_crescent_orientation, missing_circular_base, reference_mismatch.
- `BUIREL13`: Redraw as the compact black conspicuous Christian religious-building witness shape from S-101/OpenCPN; remove the long stem and circular base ring. Codes: wrong_shape, invented_stem_ring, reference_mismatch.
- `BUIREL15`: Redraw with the black crescent over the stem and the circular base/dot cue from the conspicuous mosque/minaret witness; do not use a side moon glyph. Codes: wrong_crescent_orientation, missing_circular_base, reference_mismatch.
- `DAYSQR01`: Redraw as the provider/reference-colored square or rectangular daymark on stem, including the lower node/base cue; do not use a black/yellow generic dayboard. Codes: wrong_colour_family, wrong_style_family, reference_mismatch.
- `DAYTRI01`: Redraw the point-up triangular daymark in the provider/reference color family while preserving the upright triangle and stem. Codes: wrong_colour_family, reference_mismatch.
- `DAYTRI05`: Redraw the point-down triangular daymark in the provider/reference color family while preserving the inverted triangle and stem. Codes: wrong_colour_family, reference_mismatch.
- `ESSARE01`: Replace the boxed ESSA sign with the ESSA/PSSA boundary text/line marker from the references; remove the invented enclosure and baseline decoration. Codes: wrong_symbol_class, invented_enclosure, reference_mismatch.
- `FORSTC01`: Redraw as the brown fortified-structure square/outline witness from S-101/OpenCPN; remove invented internal bars. Codes: invented_internal_marks, wrong_shape, reference_mismatch.
- `FORSTC11`: Redraw as the black conspicuous fortified-structure square/outline witness from S-101/OpenCPN; remove invented internal bars. Codes: invented_internal_marks, wrong_shape, reference_mismatch.
- `LOCMAG01`: Redraw as the LOCMAG01 magenta wedge/line magnetic-anomaly point witness; remove the A/M sign, crossbar, and dot. Codes: wrong_shape, invented_text, reference_mismatch.
- `LOCMAG51`: Redraw as the LOCMAG51 magenta magnetic-anomaly line/area wedge/line witness; remove the A/M sign and invented baseline marks. Codes: wrong_shape, invented_text, reference_mismatch.
- `LOWACC01`: Keep the question-mark plus diagonal line/leader cue, but remove the invented dashed baseline/contour segment. Codes: invented_baseline, reference_mismatch.
- `MAGVAR01`: Redraw as the MAGVAR01 magenta wedge/line magnetic-variation point glyph; remove the A/V sign, crossbar, and dot. Codes: wrong_shape, invented_text, reference_mismatch.
- `MAGVAR51`: Redraw as the MAGVAR51 magenta magnetic-variation line/area wedge/line glyph; remove the A/V sign and invented baseline marks. Codes: wrong_shape, invented_text, reference_mismatch.

## Passed Assets

`BUIREL04`, `BUIREL14`, `CHIMNY01`, `CHIMNY11`, `CURSRB01`, `CUSTOM01`, `HILTOP01`, `HILTOP11`
