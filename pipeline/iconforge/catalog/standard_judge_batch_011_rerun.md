# standard_judge_batch_011_rerun

Visual rerun after batch11 repairs. No SVGs edited. No rows final-approved.

- Selected rows: 50
- Pass: 39
- Fail/blocker: 11
- Status inputs: repaired_pending_judge_rerun=30, shape_pass_pending_visual_rerun=20

| Symbol | Input status | Pass | Confidence | Observed | Required change | Safety codes |
|---|---:|---:|---:|---|---|---|
| BCNTOW90 | shape_pass_pending_visual_rerun | yes | 0.78 | Simplified brown/yellow-brown tower beacon on a post. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| BLKADJ01 | shape_pass_pending_visual_rerun | yes | 0.90 | Black square adjustment symbol with centered grey square. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| BORDER01 | shape_pass_pending_visual_rerun | yes | 0.76 | Thin red diagonal slash/border mark. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| BOYBAR01 | shape_pass_pending_visual_rerun | yes | 0.74 | Barrel buoy with red-over-black body and black stem. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| BOYCAN01 | shape_pass_pending_visual_rerun | yes | 0.82 | Can/cylindrical buoy outline with black stroke and white interior. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| BOYCAN62 | shape_pass_pending_visual_rerun | yes | 0.77 | Can buoy split green over black. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| BOYCAN72 | shape_pass_pending_visual_rerun | yes | 0.88 | Can buoy with red-green-red horizontal bands. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| BOYCAN73 | shape_pass_pending_visual_rerun | yes | 0.88 | Can buoy with green-red-green horizontal bands. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| BOYCAN74 | shape_pass_pending_visual_rerun | yes | 0.80 | Can buoy with red-white-red repeated horizontal cue. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| BOYCAN76 | shape_pass_pending_visual_rerun | yes | 0.86 | Can buoy with black-red-black body. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| BOYCAN77 | shape_pass_pending_visual_rerun | yes | 0.84 | Can buoy with white-orange horizontal cue. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| BOYCAN78 | shape_pass_pending_visual_rerun | yes | 0.84 | Can buoy with white-orange-white horizontal cue. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| BOYCAN79 | shape_pass_pending_visual_rerun | yes | 0.90 | Can buoy filled orange. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| BOYCAN81 | shape_pass_pending_visual_rerun | no | 0.70 | Can body is still rendered white-orange-white. | Resolve the orange/white source-order ambiguity, then redraw so the visible bands follow the authoritative order. | wrong_colour_order, brief_reference_conflict, unsafe_special_purpose_confusion |
| BOYCAN82 | shape_pass_pending_visual_rerun | yes | 0.80 | Can buoy with red-white-red repeated horizontal cue. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| BOYCAN83 | shape_pass_pending_visual_rerun | yes | 0.80 | Can buoy with red-white-red horizontal cue. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| BOYCON01 | shape_pass_pending_visual_rerun | yes | 0.74 | Conical/nun buoy split red over black. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| BOYCON63 | shape_pass_pending_visual_rerun | yes | 0.88 | Conical/nun buoy with black-red-black bands. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| BOYCON66 | shape_pass_pending_visual_rerun | yes | 0.88 | Conical/nun buoy with red-green-red bands. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| BOYCON67 | shape_pass_pending_visual_rerun | yes | 0.88 | Conical/nun buoy with green-red-green bands. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| BOYCON71 | repaired_pending_judge_rerun | yes | 0.90 | Conical/nun buoy with black-yellow-black order. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| BOYCON72 | repaired_pending_judge_rerun | yes | 0.90 | Conical/nun buoy with yellow-black-yellow order. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| BOYCON74 | repaired_pending_judge_rerun | no | 0.86 | Conical body shows only a single green middle band on a white body. | Redraw BOYCON74 with five ordered green-white-green-white-green bands on the conical body. | missing_colour_bands, wrong_colour_order, reference_mismatch |
| BOYCON78 | repaired_pending_judge_rerun | yes | 0.88 | Conical/nun buoy split red/white vertically. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| BOYCON79 | repaired_pending_judge_rerun | yes | 0.72 | Stake/perch beacon with red over green body. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| BOYCON80 | repaired_pending_judge_rerun | yes | 0.86 | Conical/nun buoy with white-orange-white bands. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| BOYCON81 | repaired_pending_judge_rerun | no | 0.84 | Conical body shows a blue/red/white split cue, but not the full blue-red-white-blue plus mixed stripe requirement. | Add the missing final blue segment and resolve the mixed horizontal/vertical striping pattern against exact references. | missing_colour_band, wrong_pattern, unsafe_special_purpose_confusion |
| BOYDEF03 | repaired_pending_judge_rerun | yes | 0.78 | Default buoy body with prominent question-mark cue. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| BOYGEN03 | repaired_pending_judge_rerun | yes | 0.76 | Black generic/default buoy body. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| BOYINB01 | repaired_pending_judge_rerun | no | 0.82 | Candidate remains a generic black buoy body with a white center inset. | Redraw the black installation-buoy silhouette from S-101/OpenCPN instead of using a generic buoy body. | wrong_shape, reference_mismatch, unsafe_symbol_confusion |
| BOYISD12 | repaired_pending_judge_rerun | no | 0.88 | Candidate uses a red buoy body with a single black ball/topmark. | Redraw BOYISD12 with the isolated-danger cue from S-101/Aqua Map/OpenCPN, including the correct paired/topmark treatment. | missing_topmark, wrong_topmark_count, unsafe_isolated_danger_confusion |
| BOYLAT13 | repaired_pending_judge_rerun | yes | 0.86 | Conical lateral buoy with green-red-green order. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| BOYLAT14 | repaired_pending_judge_rerun | yes | 0.86 | Conical lateral buoy with red-green-red order. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| BOYLAT23 | repaired_pending_judge_rerun | yes | 0.86 | Can lateral buoy with green-red-green order. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| BOYLAT24 | repaired_pending_judge_rerun | yes | 0.86 | Can lateral buoy with red-green-red order. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| BOYLAT26 | repaired_pending_judge_rerun | yes | 0.78 | Narrow white-over-red lateral mark. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| BOYLAT27 | repaired_pending_judge_rerun | yes | 0.78 | Narrow white-over-green lateral mark. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| BOYLAT52 | repaired_pending_judge_rerun | no | 0.80 | Candidate now shows red-green-red, but the local OpenCPN witness render is absent. | Regenerate/verify out/opencpn_s52_reference/BOYLAT52__day.png before promoting this row. | missing_reference_render, insufficient_visual_evidence |
| BOYLAT53 | repaired_pending_judge_rerun | no | 0.80 | Candidate now shows green-red-green, but the local OpenCPN witness render is absent. | Regenerate/verify out/opencpn_s52_reference/BOYLAT53__day.png before promoting this row. | missing_reference_render, insufficient_visual_evidence |
| BOYMOR01 | repaired_pending_judge_rerun | no | 0.87 | Candidate is a plain black spherical buoy. | Redraw BOYMOR01 as the black mooring buoy/facility cue shown by S-101/Aqua Map/OpenCPN. | wrong_shape, reference_mismatch, unsafe_mooring_confusion |
| BOYMOR11 | repaired_pending_judge_rerun | no | 0.90 | Candidate is a target/ring marker on a stem. | Redraw the simplified mooring facility/buoy symbol instead of the target-ring substitute. | wrong_symbol_family, wrong_shape, reference_mismatch |
| BOYPIL01 | repaired_pending_judge_rerun | yes | 0.82 | Black pillar buoy body. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| BOYPIL66 | repaired_pending_judge_rerun | yes | 0.90 | Pillar buoy with red-green-red bands. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| BOYPIL67 | repaired_pending_judge_rerun | yes | 0.90 | Pillar buoy with green-red-green bands. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| BOYPIL70 | repaired_pending_judge_rerun | yes | 0.90 | Pillar buoy with black-yellow-black bands. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| BOYPIL71 | repaired_pending_judge_rerun | yes | 0.90 | Pillar buoy with yellow-black-yellow bands. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| BOYPIL72 | repaired_pending_judge_rerun | yes | 0.90 | Pillar buoy with black-red-black bands. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| BOYPIL73 | repaired_pending_judge_rerun | yes | 0.88 | Pillar buoy with vertical red/white split. | No repair required for visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| BOYPIL78 | repaired_pending_judge_rerun | no | 0.86 | Candidate still uses horizontal red-white bands on the pillar. | Replace horizontal bands with the red/white squared/checkered pattern on the pillar body. | wrong_pattern, reference_mismatch |
| BOYSAW12 | repaired_pending_judge_rerun | no | 0.86 | Candidate uses a red/white buoy body with a single red ball top cue. | Redraw BOYSAW12 to match the compact red safe-water simplified reference cue without the extra white split/topmark substitute. | wrong_shape, wrong_colour_family, unsafe_safe_water_confusion |

## Blockers

- OpenCPN day renders are missing for BOYLAT52 and BOYLAT53, so those rows remain failed despite matching S-101/semantic colour order.
