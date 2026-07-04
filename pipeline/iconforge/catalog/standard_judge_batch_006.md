# Standard Judge Batch 006

Next 50 never-judged `pending_judge` rows from `standard_source_table.json`; no final approvals.

- Total: 50
- Pass: 18
- Fail: 32
- Final approved: 0

| # | Symbol | Verdict | Confidence | Required change | Safety codes |
|---:|---|---|---:|---|---|
| 1 | `BOYSPH01` | FAIL | 0.90 | Remove the invented blue/grey fill and redraw as a spherical buoy carrying only the required red/black load-bearing colours. | wrong_colour_family, invented_colour, reference_mismatch |
| 2 | `BOYSPH05` | PASS | 0.82 | No semantic repair required before final approval QA; keep pending final approval. | - |
| 3 | `BOYSPH60` | PASS | 0.84 | No semantic repair required before final approval QA; keep pending final approval. | - |
| 4 | `BOYSPH62` | PASS | 0.82 | No semantic repair required before final approval QA; keep pending final approval. | - |
| 5 | `BOYSPH65` | FAIL | 0.92 | Change the spherical body to vertical red/white bands/stripes in the listed colour order. | wrong_pattern_orientation, reference_mismatch, unsafe_safe_water_confusion |
| 6 | `BOYSPH66` | FAIL | 0.91 | Add the missing lower red band so the spherical buoy reads red-green-red. | missing_colour_band, wrong_colour_order, unsafe_lateral_confusion |
| 7 | `BOYSPH68` | PASS | 0.85 | No semantic repair required before final approval QA; keep pending final approval. | - |
| 8 | `BOYSPH69` | PASS | 0.85 | No semantic repair required before final approval QA; keep pending final approval. | - |
| 9 | `BOYSPH70` | FAIL | 0.91 | Add the missing lower black band so the spherical buoy reads black-yellow-black. | missing_colour_band, wrong_colour_order, unsafe_cardinal_confusion |
| 10 | `BOYSPH71` | FAIL | 0.91 | Add the missing lower yellow band so the spherical buoy reads yellow-black-yellow. | missing_colour_band, wrong_colour_order, unsafe_cardinal_confusion |
| 11 | `BOYSPH74` | PASS | 0.85 | No semantic repair required before final approval QA; keep pending final approval. | - |
| 12 | `BOYSPH75` | PASS | 0.85 | No semantic repair required before final approval QA; keep pending final approval. | - |
| 13 | `BOYSPH77` | PASS | 0.82 | No semantic repair required before final approval QA; keep pending final approval. | - |
| 14 | `BOYSPH79` | FAIL | 0.88 | Replace the spherical body with the required conical/nun red/green buoy and regenerate/verify the OpenCPN reference render before promotion. | wrong_symbol_family, wrong_shape, missing_reference_render |
| 15 | `BOYSPP11` | FAIL | 0.93 | Redraw as the simplified special-purpose buoy reference cue; remove the generic black lower body. | wrong_shape, wrong_colour_family, reference_mismatch |
| 16 | `BOYSPP15` | FAIL | 0.92 | Redraw with the simplified TSS starboard conical/triangular reference shape and remove the misleading black generic body. | wrong_shape, wrong_symbol_family, reference_mismatch |
| 17 | `BOYSPP25` | FAIL | 0.92 | Redraw with the simplified TSS port can/cylindrical reference shape and remove the misleading black generic body. | wrong_shape, wrong_symbol_family, reference_mismatch |
| 18 | `BOYSPR01` | FAIL | 0.89 | Remove the blue fill and redraw the spar using only the required white/black semantic colours. | wrong_colour_family, invented_colour, reference_mismatch |
| 19 | `BOYSPR02` | FAIL | 0.64 | Regenerate or attach the exact OpenCPN/S-101 reference for BOYSPR02 before passing visual parity. | missing_reference_render, insufficient_source_refs |
| 20 | `BOYSPR03` | FAIL | 0.64 | Regenerate or attach the exact OpenCPN/S-101 reference for BOYSPR03 before passing visual parity. | missing_reference_render, insufficient_source_refs |
| 21 | `BOYSPR04` | PASS | 0.84 | No semantic repair required before final approval QA; keep pending final approval. | - |
| 22 | `BOYSPR05` | PASS | 0.80 | No semantic repair required before final approval QA; keep pending final approval. | - |
| 23 | `BOYSPR60` | PASS | 0.84 | No semantic repair required before final approval QA; keep pending final approval. | - |
| 24 | `BOYSPR61` | PASS | 0.84 | No semantic repair required before final approval QA; keep pending final approval. | - |
| 25 | `BOYSPR62` | PASS | 0.84 | No semantic repair required before final approval QA; keep pending final approval. | - |
| 26 | `BOYSPR65` | PASS | 0.80 | No semantic repair required before final approval QA; keep pending final approval. | - |
| 27 | `BOYSPR68` | PASS | 0.85 | No semantic repair required before final approval QA; keep pending final approval. | - |
| 28 | `BOYSPR69` | PASS | 0.85 | No semantic repair required before final approval QA; keep pending final approval. | - |
| 29 | `BOYSPR70` | FAIL | 0.91 | Add the missing lower black band so the spar reads black-yellow-black. | missing_colour_band, wrong_colour_order, unsafe_cardinal_confusion |
| 30 | `BOYSPR71` | FAIL | 0.91 | Add the missing lower yellow band so the spar reads yellow-black-yellow. | missing_colour_band, wrong_colour_order, unsafe_cardinal_confusion |
| 31 | `BOYSPR72` | FAIL | 0.92 | Add the missing lower black band so the spar reads black-red-black. | missing_colour_band, wrong_colour_order, unsafe_isolated_danger_confusion |
| 32 | `BOYSUP01` | FAIL | 0.90 | Remove the invented blue/grey fill and redraw the super-buoy using only the required red/black load-bearing colours. | wrong_colour_family, invented_colour, reference_mismatch |
| 33 | `BOYSUP02` | FAIL | 0.91 | Remove the blue/grey lower fill so BOYSUP02 is a black super-buoy. | wrong_colour_family, invented_colour, reference_mismatch |
| 34 | `BOYSUP03` | FAIL | 0.94 | Redraw the LANBY paper-chart super-buoy with the required reference cue/topmark and remove the invented blue field. | missing_topmark, wrong_colour_family, reference_mismatch |
| 35 | `BOYSUP62` | PASS | 0.82 | No semantic repair required before final approval QA; keep pending final approval. | - |
| 36 | `BOYSUP65` | FAIL | 0.92 | Change the super-buoy body to vertical red/white bands/stripes in the listed colour order. | wrong_pattern_orientation, reference_mismatch |
| 37 | `BOYSUP66` | PASS | 0.82 | No semantic repair required before final approval QA; keep pending final approval. | - |
| 38 | `BRIDGE01` | FAIL | 0.95 | Replace the diamond placeholder with the opening-bridge circular/ring symbol silhouette. | wrong_symbol_family, wrong_shape, reference_mismatch |
| 39 | `BRTHNO01` | FAIL | 0.94 | Replace the diamond placeholder with the berth-number circular reference silhouette. | wrong_symbol_family, wrong_shape, reference_mismatch |
| 40 | `BUAARE02` | FAIL | 0.94 | Redraw as the built-up-area reference cue rather than the grey dashed-square placeholder. | wrong_symbol_family, wrong_shape, wrong_colour_family, reference_mismatch |
| 41 | `BUIREL01` | FAIL | 0.95 | Replace the diamond placeholder with the non-conspicuous Christian religious-building cross/church silhouette and colour. | wrong_symbol_family, wrong_shape, reference_mismatch |
| 42 | `BUIREL04` | FAIL | 0.95 | Replace the diamond placeholder with the non-Christian religious-building reference silhouette and colour. | wrong_symbol_family, wrong_shape, reference_mismatch |
| 43 | `BUIREL05` | FAIL | 0.95 | Replace the diamond placeholder with the mosque/minaret reference silhouette. | wrong_symbol_family, wrong_shape, reference_mismatch |
| 44 | `BUIREL13` | FAIL | 0.95 | Replace the diamond placeholder with the conspicuous Christian religious-building reference silhouette. | wrong_symbol_family, wrong_shape, reference_mismatch |
| 45 | `BUIREL14` | FAIL | 0.95 | Replace the diamond placeholder with the conspicuous non-Christian religious-building reference silhouette. | wrong_symbol_family, wrong_shape, reference_mismatch |
| 46 | `BUIREL15` | FAIL | 0.95 | Replace the diamond placeholder with the conspicuous mosque/minaret reference silhouette. | wrong_symbol_family, wrong_shape, reference_mismatch |
| 47 | `BUISGL01` | FAIL | 0.93 | Replace the diamond placeholder with the single-building square/reference silhouette. | wrong_symbol_family, wrong_shape, reference_mismatch |
| 48 | `BUISGL11` | FAIL | 0.93 | Replace the diamond placeholder with the conspicuous single-building square/reference silhouette. | wrong_symbol_family, wrong_shape, reference_mismatch |
| 49 | `BUNSTA01` | FAIL | 0.95 | Replace the diamond placeholder with the diesel bunker-station/fuel reference silhouette. | wrong_symbol_family, wrong_shape, reference_mismatch |
| 50 | `BUNSTA02` | FAIL | 0.95 | Replace the diamond placeholder with the water bunker-station reference silhouette. | wrong_symbol_family, wrong_shape, reference_mismatch |

## Notes
- missing third bands in cardinal/isolated-danger multi-band buoy rows
- wrong vertical-vs-horizontal stripe orientation for red/white safe-water/special rows
- invented blue/grey fills in red/black or black-only buoy rows
- generic diamond placeholders used for landmark/building/service symbols
- missing local reference renders for a few otherwise plausible spar rows
