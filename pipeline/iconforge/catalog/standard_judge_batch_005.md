# Standard Judge Batch 005

First 50 `pending_judge` rows from `standard_source_table.json`; no final approvals.

- Total: 50
- Pass: 20
- Fail: 30
- Final approved: 0

| # | Symbol | Verdict | Confidence | Required change | Safety codes |
|---:|---|---|---:|---|---|
| 1 | `BOYCON69` | PASS | 0.86 | No semantic repair required before final approval QA; keep pending final approval. | - |
| 2 | `BOYCON70` | PASS | 0.86 | No semantic repair required before final approval QA; keep pending final approval. | - |
| 3 | `BOYCON71` | FAIL | 0.91 | Add the missing lower black band so the conical body reads black-yellow-black, not two-band black-yellow. | missing_colour_band, wrong_colour_order, unsafe_cardinal_confusion |
| 4 | `BOYCON72` | FAIL | 0.91 | Add the missing lower yellow band so the conical body reads yellow-black-yellow, not two-band yellow-black. | missing_colour_band, wrong_colour_order, unsafe_cardinal_confusion |
| 5 | `BOYCON73` | PASS | 0.84 | No semantic repair required before final approval QA; keep pending final approval. | - |
| 6 | `BOYCON74` | FAIL | 0.93 | Redraw with five ordered green/white/green/white/green bands on the conical body. | missing_colour_bands, wrong_colour_order, reference_mismatch |
| 7 | `BOYCON77` | PASS | 0.84 | No semantic repair required before final approval QA; keep pending final approval. | - |
| 8 | `BOYCON78` | FAIL | 0.89 | Change BOYCON78 to vertical red/white striping on the conical buoy, not horizontal bands. | wrong_pattern_orientation, reference_mismatch, unsafe_lateral_confusion |
| 9 | `BOYCON79` | FAIL | 0.88 | Replace the conical buoy silhouette with the required stake/perch beacon geometry while preserving red-over-green order. | wrong_symbol_family, wrong_shape, unsafe_buoy_beacon_confusion |
| 10 | `BOYCON80` | FAIL | 0.91 | Add the missing lower white band so the conical body reads white-orange-white. | missing_colour_band, wrong_colour_order, reference_mismatch |
| 11 | `BOYCON81` | FAIL | 0.94 | Add the missing final blue segment and resolve the required horizontal/vertical striping pattern against the exact reference before approval. | missing_colour_band, wrong_pattern, unsafe_special_purpose_confusion |
| 12 | `BOYDEF03` | FAIL | 0.94 | Redraw as the default buoy symbol family from S-101/OpenCPN, including the default/unknown cue; do not substitute a magenta generic buoy. | wrong_symbol_family, wrong_colour_family, reference_mismatch |
| 13 | `BOYGEN03` | FAIL | 0.93 | Remove invented magenta/blue fills and redraw as the black default buoy family shown by the references. | wrong_colour_family, invented_colour, reference_mismatch |
| 14 | `BOYINB01` | FAIL | 0.92 | Redraw the installation buoy silhouette from the provider references while keeping black as the load-bearing colour. | wrong_shape, reference_mismatch, unsafe_symbol_confusion |
| 15 | `BOYISD12` | FAIL | 0.95 | Redraw BOYISD12 with the isolated-danger visual cue from S-101/Aqua Map/OpenCPN, including the paired red danger marks/topmark treatment as applicable. | missing_topmark, wrong_shape, unsafe_isolated_danger_confusion |
| 16 | `BOYLAT13` | FAIL | 0.91 | Add the missing lower green band to the conical buoy. | missing_colour_band, wrong_colour_order, unsafe_lateral_confusion |
| 17 | `BOYLAT14` | FAIL | 0.91 | Add the missing lower red band to the conical buoy. | missing_colour_band, wrong_colour_order, unsafe_lateral_confusion |
| 18 | `BOYLAT23` | FAIL | 0.93 | Use a can/cylindrical buoy body and add the missing lower green band. | wrong_shape, missing_colour_band, wrong_colour_order |
| 19 | `BOYLAT24` | FAIL | 0.93 | Use a can/cylindrical buoy body and add the missing lower red band. | wrong_shape, missing_colour_band, wrong_colour_order |
| 20 | `BOYLAT25` | PASS | 0.78 | No semantic repair required before final approval QA; keep pending final approval. | - |
| 21 | `BOYLAT26` | FAIL | 0.87 | Match the narrow segmented BOYLAT26 reference silhouette while preserving white-over-red order. | wrong_shape, reference_mismatch |
| 22 | `BOYLAT27` | FAIL | 0.87 | Match the narrow segmented BOYLAT27 reference silhouette while preserving white-over-green order. | wrong_shape, reference_mismatch |
| 23 | `BOYLAT50` | PASS | 0.76 | No semantic repair required before final approval QA; keep pending final approval. | - |
| 24 | `BOYLAT51` | PASS | 0.84 | No semantic repair required before final approval QA; keep pending final approval. | - |
| 25 | `BOYLAT52` | FAIL | 0.79 | Add the missing lower red band and obtain/verify the exact local OpenCPN render before promoting. | missing_colour_band, missing_reference_render, wrong_colour_order |
| 26 | `BOYLAT53` | FAIL | 0.79 | Add the missing lower green band and obtain/verify the exact local OpenCPN render before promoting. | missing_colour_band, missing_reference_render, wrong_colour_order |
| 27 | `BOYLAT54` | PASS | 0.68 | No semantic repair required before final approval QA; keep pending final approval. | - |
| 28 | `BOYLAT55` | PASS | 0.68 | No semantic repair required before final approval QA; keep pending final approval. | - |
| 29 | `BOYLAT56` | PASS | 0.68 | No semantic repair required before final approval QA; keep pending final approval. | - |
| 30 | `BOYMOR01` | FAIL | 0.91 | Remove the invented blue fill and redraw as the black spherical/barrel mooring buoy from the reference. | wrong_colour_family, wrong_shape, reference_mismatch |
| 31 | `BOYMOR03` | PASS | 0.74 | No semantic repair required before final approval QA; keep pending final approval. | - |
| 32 | `BOYMOR11` | FAIL | 0.91 | Redraw the simplified mooring facility/buoy symbol, not a generic can buoy. | wrong_symbol_family, wrong_shape, reference_mismatch |
| 33 | `BOYMOR31` | PASS | 0.78 | No semantic repair required before final approval QA; keep pending final approval. | - |
| 34 | `BOYPIL01` | FAIL | 0.92 | Remove the invented blue lower fill and make the full pillar body black. | wrong_colour_family, invented_colour, reference_mismatch |
| 35 | `BOYPIL59` | PASS | 0.86 | No semantic repair required before final approval QA; keep pending final approval. | - |
| 36 | `BOYPIL60` | PASS | 0.86 | No semantic repair required before final approval QA; keep pending final approval. | - |
| 37 | `BOYPIL61` | PASS | 0.86 | No semantic repair required before final approval QA; keep pending final approval. | - |
| 38 | `BOYPIL62` | PASS | 0.86 | No semantic repair required before final approval QA; keep pending final approval. | - |
| 39 | `BOYPIL66` | FAIL | 0.91 | Add the missing lower red band to the pillar body. | missing_colour_band, wrong_colour_order, unsafe_lateral_confusion |
| 40 | `BOYPIL67` | FAIL | 0.91 | Add the missing lower green band to the pillar body. | missing_colour_band, wrong_colour_order, unsafe_lateral_confusion |
| 41 | `BOYPIL68` | PASS | 0.86 | No semantic repair required before final approval QA; keep pending final approval. | - |
| 42 | `BOYPIL69` | PASS | 0.86 | No semantic repair required before final approval QA; keep pending final approval. | - |
| 43 | `BOYPIL70` | FAIL | 0.91 | Add the missing lower black band to the pillar body. | missing_colour_band, wrong_colour_order, unsafe_cardinal_confusion |
| 44 | `BOYPIL71` | FAIL | 0.91 | Add the missing lower yellow band to the pillar body. | missing_colour_band, wrong_colour_order, unsafe_cardinal_confusion |
| 45 | `BOYPIL72` | FAIL | 0.91 | Add the missing lower black band to the pillar body. | missing_colour_band, wrong_colour_order, unsafe_isolated_danger_confusion |
| 46 | `BOYPIL73` | FAIL | 0.89 | Change BOYPIL73 to vertical red/white striping on the pillar body. | wrong_pattern_orientation, reference_mismatch, unsafe_safe_water_confusion |
| 47 | `BOYPIL74` | PASS | 0.82 | No semantic repair required before final approval QA; keep pending final approval. | - |
| 48 | `BOYPIL78` | FAIL | 0.90 | Replace horizontal bands with the red/white squared/checkered pattern on the pillar body. | wrong_pattern, reference_mismatch |
| 49 | `BOYPIL81` | PASS | 0.84 | No semantic repair required before final approval QA; keep pending final approval. | - |
| 50 | `BOYSAW12` | FAIL | 0.94 | Redraw BOYSAW12 to match the safe-water simplified reference cue and remove the misleading black lower body. | wrong_shape, wrong_colour_family, unsafe_safe_water_confusion |
