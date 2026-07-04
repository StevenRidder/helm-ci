# Standard Judge Batch 018 Rerun

- Task: FORGE-18 visual rerun for repaired batch18 rows
- Source batch: `pipeline/iconforge/catalog/owned_repair_batch18.json`
- Candidate status: `repaired_pending_judge_rerun`
- Counts: 43 judged, 5 pass, 38 fail, 0 final-approved
- Approval note: pass means visual-rerun pass only; no row is human-final-approved.

## Verdicts

| Asset | Verdict | Confidence | Required change | Safety reason codes |
| --- | --- | ---: | --- | --- |
| `BRIDGE01` | fail | 0.88 | Redraw as the BRIDGE01 opening-bridge concentric ring/double-ring witness; remove the diagonal slash and center dash details. | invented_detail, wrong_shape, reference_mismatch |
| `CGUSTA02` | pass | 0.78 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `CRANES01` | fail | 0.88 | Redraw as the brown S-101/OpenCPN crane with boom, post, hook, base, and reference colour family. | wrong_colour_family, wrong_shape, reference_mismatch |
| `CURDEF01` | fail | 0.86 | Redraw as the vertical current/stream arrow with side question marks and straight lower barb/stem structure; remove the curved lower arc. | wrong_shape, wrong_directional_structure, reference_mismatch |
| `CURENT01` | pass | 0.80 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `DAYSQR21` | fail | 0.90 | Redraw DAYSQR21 with the provider/reference daymark colour family and base/ring details; do not substitute a yellow black-outlined board. | wrong_colour_family, wrong_style_family, reference_mismatch |
| `DWRTPT51` | fail | 0.88 | Redraw as the DW deep-water-route text mark in the reference style; remove the rounded enclosing placard. | invented_enclosure, wrong_shape, reference_mismatch |
| `EBBSTR01` | pass | 0.80 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `FAIRWY51` | fail | 0.88 | Redraw as the vertical one-way fairway arrow using the reference colour/stroke treatment, not magenta precaution/route styling. | wrong_colour_family, reference_mismatch |
| `FAIRWY52` | fail | 0.88 | Redraw as the vertical two-way fairway arrow using the reference colour/stroke treatment, not magenta styling. | wrong_colour_family, reference_mismatch |
| `FLDSTR01` | fail | 0.86 | Redraw with the S-101/OpenCPN upward flood-stream arrow and side-rate barb geometry. | wrong_shape, missing_rate_barb, reference_mismatch |
| `FLGSTF01` | fail | 0.88 | Redraw the brown/gold flagstaff with the reference flag shape plus base/ring marker. | wrong_shape, missing_base_detail, reference_mismatch |
| `FLTHAZ02` | fail | 0.92 | Redraw FLTHAZ02 as the magenta circular floating-hazard witness from S-101/OpenCPN; remove the black hull/chevron substitution. | wrong_symbol_class, wrong_colour_family, wrong_shape, reference_mismatch |
| `FOGSIG01` | fail | 0.90 | Redraw as the fog-signal arc glyph in the reference purple/magenta treatment; remove the invented bell/horn body. | invented_body, wrong_colour_family, reference_mismatch |
| `FOULGND1` | fail | 0.92 | Redraw as the open foul-ground hash/slash mark; do not use an asterisk/star. | wrong_shape, unsafe_symbol_confusion, reference_mismatch |
| `FRYARE51` | fail | 0.92 | Redraw as the ferry-area route/ferry-outline witness; remove the F signboard. | invented_label, invented_enclosure, wrong_shape, reference_mismatch |
| `FRYARE52` | fail | 0.92 | Redraw as the cable-ferry area route/ferry-outline witness; remove the CF signboard. | invented_label, invented_enclosure, wrong_shape, reference_mismatch |
| `FSHFAC02` | fail | 0.90 | Redraw as the fishing-stakes frame and angled-stake geometry from the reference. | wrong_shape, wrong_colour_family, reference_mismatch |
| `FSHFAC03` | fail | 0.90 | Redraw as the fishing-stakes area pattern/comb symbol; remove the triangular stake silhouette. | wrong_shape, wrong_pattern, reference_mismatch |
| `FSHGRD01` | fail | 0.90 | Redraw as the fishing-ground fish outline from the references; remove the FG lettering and wrong colour family. | invented_text, wrong_colour_family, reference_mismatch |
| `FSHHAV01` | fail | 0.92 | Redraw as the fish-haven fish plus dotted boundary witness; remove FH text and wrong colour family. | invented_text, missing_dotted_boundary, wrong_colour_family, reference_mismatch |
| `HULKES01` | fail | 0.90 | Redraw as the HULKES01 hulk silhouette from the references; remove the A-like marker and align the hull shape/colour. | wrong_shape, invented_internal_mark, reference_mismatch |
| `INFARE51` | fail | 0.88 | Redraw as the INFARE51 information/restriction-area box glyph; remove the signpost and curved base. | invented_stand, wrong_shape, reference_mismatch |
| `INFORM01` | fail | 0.90 | Redraw as the reference information marker with leader line and origin circle; remove the signpost substitution. | missing_leader_line, missing_origin_marker, wrong_shape, reference_mismatch |
| `ITZARE51` | fail | 0.92 | Redraw as the IT inshore-traffic-area text mark in the reference style; remove the double-arrow icon. | wrong_symbol_text, wrong_shape, reference_mismatch |
| `LNDARE01` | fail | 0.92 | Redraw as the LNDARE01 land-area point/disk symbol from the references; remove the mound silhouette. | wrong_shape, substituted_landform_icon, reference_mismatch |
| `MARCUL02` | fail | 0.90 | Redraw as the MARCUL02 marine-farm fish/net line motif from S-101/OpenCPN. | wrong_shape, missing_fish_motif, reference_mismatch |
| `MONUMT02` | fail | 0.88 | Redraw as the brown MONUMT02 monument silhouette with diagonal bands and base/ring details. | missing_internal_bands, missing_base_detail, reference_mismatch |
| `MONUMT12` | fail | 0.88 | Redraw as the black conspicuous MONUMT12 monument with diagonal bands and base/ring details. | missing_internal_bands, missing_base_detail, reference_mismatch |
| `MSTCON04` | fail | 0.88 | Redraw as the MSTCON04 narrow mast/needle silhouette with base/ring marker and brown reference colour. | wrong_shape, missing_base_ring, reference_mismatch |
| `MSTCON14` | fail | 0.88 | Redraw as the MSTCON14 black narrow mast/needle silhouette with base/ring marker. | wrong_shape, missing_base_ring, reference_mismatch |
| `NORTHAR1` | fail | 0.88 | Redraw as the NORTHAR1 simple orange north-arrow/stem glyph with reference N placement. | wrong_shape, wrong_text_placement, reference_mismatch |
| `NOTBRD11` | pass | 0.82 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `OBSTRN03` | fail | 0.90 | Redraw with the reference filled/tinted obstruction circle and dotted perimeter; remove the center-dot-only treatment. | missing_fill, wrong_colour_treatment, reference_mismatch |
| `OFSPLF01` | fail | 0.92 | Redraw as the OFSPLF01 square platform glyph with central dot; remove the legged platform pictogram. | wrong_shape, invented_platform_detail, reference_mismatch |
| `PILBOP02` | fail | 0.92 | Redraw as the PILBOP02 magenta circle/diamond pilot-boarding witness; remove the P letter and stem. | invented_text, wrong_shape, reference_mismatch |
| `PILPNT02` | fail | 0.92 | Redraw as the PILPNT02 black pile/bollard point mark at reference proportions; remove the signpost. | wrong_shape, invented_stand, reference_mismatch |
| `POSGEN01` | fail | 0.86 | Keep the ring/dot geometry but change POSGEN01 to the reference brown colour family. | wrong_colour_family, reference_mismatch |
| `POSGEN03` | fail | 0.88 | Redraw as the POSGEN03 black ring/dot witness; remove crosshair spokes. | invented_crosshair, wrong_shape, reference_mismatch |
| `POSGEN04` | fail | 0.90 | Redraw as the POSGEN04 reference ring marker; remove the invented internal triangle. | invented_internal_shape, wrong_shape, reference_mismatch |
| `PRCARE12` | pass | 0.80 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `PRCARE51` | fail | 0.88 | Redraw PRCARE51 as the reference precautionary-area boundary triangle; remove the dashed outline substitution. | wrong_line_style, wrong_pattern, reference_mismatch |
| `PRDINS02` | fail | 0.92 | Redraw as the PRDINS02 brown crossed mine/quarry tools symbol; remove the crossed-circle target. | wrong_shape, substituted_target_icon, reference_mismatch |

## Failure Summary

- `BRIDGE01`: Redraw as the BRIDGE01 opening-bridge concentric ring/double-ring witness; remove the diagonal slash and center dash details. Codes: invented_detail, wrong_shape, reference_mismatch.
- `CRANES01`: Redraw as the brown S-101/OpenCPN crane with boom, post, hook, base, and reference colour family. Codes: wrong_colour_family, wrong_shape, reference_mismatch.
- `CURDEF01`: Redraw as the vertical current/stream arrow with side question marks and straight lower barb/stem structure; remove the curved lower arc. Codes: wrong_shape, wrong_directional_structure, reference_mismatch.
- `DAYSQR21`: Redraw DAYSQR21 with the provider/reference daymark colour family and base/ring details; do not substitute a yellow black-outlined board. Codes: wrong_colour_family, wrong_style_family, reference_mismatch.
- `DWRTPT51`: Redraw as the DW deep-water-route text mark in the reference style; remove the rounded enclosing placard. Codes: invented_enclosure, wrong_shape, reference_mismatch.
- `FAIRWY51`: Redraw as the vertical one-way fairway arrow using the reference colour/stroke treatment, not magenta precaution/route styling. Codes: wrong_colour_family, reference_mismatch.
- `FAIRWY52`: Redraw as the vertical two-way fairway arrow using the reference colour/stroke treatment, not magenta styling. Codes: wrong_colour_family, reference_mismatch.
- `FLDSTR01`: Redraw with the S-101/OpenCPN upward flood-stream arrow and side-rate barb geometry. Codes: wrong_shape, missing_rate_barb, reference_mismatch.
- `FLGSTF01`: Redraw the brown/gold flagstaff with the reference flag shape plus base/ring marker. Codes: wrong_shape, missing_base_detail, reference_mismatch.
- `FLTHAZ02`: Redraw FLTHAZ02 as the magenta circular floating-hazard witness from S-101/OpenCPN; remove the black hull/chevron substitution. Codes: wrong_symbol_class, wrong_colour_family, wrong_shape, reference_mismatch.
- `FOGSIG01`: Redraw as the fog-signal arc glyph in the reference purple/magenta treatment; remove the invented bell/horn body. Codes: invented_body, wrong_colour_family, reference_mismatch.
- `FOULGND1`: Redraw as the open foul-ground hash/slash mark; do not use an asterisk/star. Codes: wrong_shape, unsafe_symbol_confusion, reference_mismatch.
- `FRYARE51`: Redraw as the ferry-area route/ferry-outline witness; remove the F signboard. Codes: invented_label, invented_enclosure, wrong_shape, reference_mismatch.
- `FRYARE52`: Redraw as the cable-ferry area route/ferry-outline witness; remove the CF signboard. Codes: invented_label, invented_enclosure, wrong_shape, reference_mismatch.
- `FSHFAC02`: Redraw as the fishing-stakes frame and angled-stake geometry from the reference. Codes: wrong_shape, wrong_colour_family, reference_mismatch.
- `FSHFAC03`: Redraw as the fishing-stakes area pattern/comb symbol; remove the triangular stake silhouette. Codes: wrong_shape, wrong_pattern, reference_mismatch.
- `FSHGRD01`: Redraw as the fishing-ground fish outline from the references; remove the FG lettering and wrong colour family. Codes: invented_text, wrong_colour_family, reference_mismatch.
- `FSHHAV01`: Redraw as the fish-haven fish plus dotted boundary witness; remove FH text and wrong colour family. Codes: invented_text, missing_dotted_boundary, wrong_colour_family, reference_mismatch.
- `HULKES01`: Redraw as the HULKES01 hulk silhouette from the references; remove the A-like marker and align the hull shape/colour. Codes: wrong_shape, invented_internal_mark, reference_mismatch.
- `INFARE51`: Redraw as the INFARE51 information/restriction-area box glyph; remove the signpost and curved base. Codes: invented_stand, wrong_shape, reference_mismatch.
- `INFORM01`: Redraw as the reference information marker with leader line and origin circle; remove the signpost substitution. Codes: missing_leader_line, missing_origin_marker, wrong_shape, reference_mismatch.
- `ITZARE51`: Redraw as the IT inshore-traffic-area text mark in the reference style; remove the double-arrow icon. Codes: wrong_symbol_text, wrong_shape, reference_mismatch.
- `LNDARE01`: Redraw as the LNDARE01 land-area point/disk symbol from the references; remove the mound silhouette. Codes: wrong_shape, substituted_landform_icon, reference_mismatch.
- `MARCUL02`: Redraw as the MARCUL02 marine-farm fish/net line motif from S-101/OpenCPN. Codes: wrong_shape, missing_fish_motif, reference_mismatch.
- `MONUMT02`: Redraw as the brown MONUMT02 monument silhouette with diagonal bands and base/ring details. Codes: missing_internal_bands, missing_base_detail, reference_mismatch.
- `MONUMT12`: Redraw as the black conspicuous MONUMT12 monument with diagonal bands and base/ring details. Codes: missing_internal_bands, missing_base_detail, reference_mismatch.
- `MSTCON04`: Redraw as the MSTCON04 narrow mast/needle silhouette with base/ring marker and brown reference colour. Codes: wrong_shape, missing_base_ring, reference_mismatch.
- `MSTCON14`: Redraw as the MSTCON14 black narrow mast/needle silhouette with base/ring marker. Codes: wrong_shape, missing_base_ring, reference_mismatch.
- `NORTHAR1`: Redraw as the NORTHAR1 simple orange north-arrow/stem glyph with reference N placement. Codes: wrong_shape, wrong_text_placement, reference_mismatch.
- `OBSTRN03`: Redraw with the reference filled/tinted obstruction circle and dotted perimeter; remove the center-dot-only treatment. Codes: missing_fill, wrong_colour_treatment, reference_mismatch.
- `OFSPLF01`: Redraw as the OFSPLF01 square platform glyph with central dot; remove the legged platform pictogram. Codes: wrong_shape, invented_platform_detail, reference_mismatch.
- `PILBOP02`: Redraw as the PILBOP02 magenta circle/diamond pilot-boarding witness; remove the P letter and stem. Codes: invented_text, wrong_shape, reference_mismatch.
- `PILPNT02`: Redraw as the PILPNT02 black pile/bollard point mark at reference proportions; remove the signpost. Codes: wrong_shape, invented_stand, reference_mismatch.
- `POSGEN01`: Keep the ring/dot geometry but change POSGEN01 to the reference brown colour family. Codes: wrong_colour_family, reference_mismatch.
- `POSGEN03`: Redraw as the POSGEN03 black ring/dot witness; remove crosshair spokes. Codes: invented_crosshair, wrong_shape, reference_mismatch.
- `POSGEN04`: Redraw as the POSGEN04 reference ring marker; remove the invented internal triangle. Codes: invented_internal_shape, wrong_shape, reference_mismatch.
- `PRCARE51`: Redraw PRCARE51 as the reference precautionary-area boundary triangle; remove the dashed outline substitution. Codes: wrong_line_style, wrong_pattern, reference_mismatch.
- `PRDINS02`: Redraw as the PRDINS02 brown crossed mine/quarry tools symbol; remove the crossed-circle target. Codes: wrong_shape, substituted_target_icon, reference_mismatch.

## Passed Assets

`CGUSTA02`, `CURENT01`, `EBBSTR01`, `NOTBRD11`, `PRCARE12`
