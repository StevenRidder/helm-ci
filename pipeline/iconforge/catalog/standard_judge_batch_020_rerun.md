# Standard Judge Batch 020 Rerun

- Task: FORGE-18 visual rerun for repaired batch20 rows
- Source batch: `pipeline/iconforge/catalog/owned_repair_batch20.json`
- Candidate status: `repaired_pending_judge_rerun`
- Counts: 30 judged, 7 pass, 23 fail, 0 final-approved
- Approval note: pass means automated visual-rerun pass only; no row is human-final-approved. Chart No.1 exact-crop/manual final evidence is absent for these rows.

## Verdicts

| Asset | Verdict | Confidence | Required change | Safety reason codes |
| --- | --- | ---: | --- | --- |
| `QUAPOS01` | pass | 0.80 | No repair required for this automated visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `QUARRY01` | fail | 0.88 | Redraw QUARRY01 as the compact brown quarry crossed-tool/hash symbol inside the reference circular witness; remove the hourglass top/bottom bars. | wrong_shape, missing_reference_enclosure, reference_mismatch |
| `QUESMRK1` | pass | 0.82 | No repair required for this automated visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `RACNSP01` | pass | 0.76 | No repair required for this automated visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `RADRFL03` | fail | 0.82 | Resolve the provider conflict and redraw RADRFL03 to the S-101/OpenCPN magenta starburst/ring witness, or record an explicit manual exception choosing the AquaMap reflector motif before rerun pass. | conflicting_reference_witness, wrong_colour_family, reference_mismatch |
| `RASCAN01` | fail | 0.86 | Redraw RASCAN01 as the brown rectangular scanner-frame witness with top horizontal bar, vertical supports, and lower pivot circle; remove the broadcast-arc motif. | wrong_shape, wrong_scanner_structure, reference_mismatch |
| `RASCAN11` | fail | 0.86 | Redraw RASCAN11 as the black conspicuous radar-scanner frame with top bar, vertical supports, and lower pivot circle; remove the broadcast-arc motif. | wrong_shape, wrong_scanner_structure, reference_mismatch |
| `RCTLPT52` | pass | 0.78 | No repair required for this automated visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `RDOCAL02` | fail | 0.90 | Redraw RDOCAL02 as the one-direction radio call-in point witness: circle plus one triangular direction point; remove the R label, arrow, and outer sign circle. | wrong_shape, invented_text, missing_directional_semantics, reference_mismatch |
| `RDOCAL03` | fail | 0.90 | Redraw RDOCAL03 as the bidirectional radio call-in point witness with opposed triangular points around the circle; remove the R label, arrows, and enclosing sign circle. | wrong_shape, invented_text, missing_bidirectional_semantics, reference_mismatch |
| `RDOSTA02` | fail | 0.88 | Redraw RDOSTA02 as the simple magenta radio-station circle/point witness from S-101/OpenCPN; do not use a mast or broadcast-wave icon. | wrong_symbol_class, wrong_shape, reference_mismatch |
| `RECDEF51` | fail | 0.88 | Redraw RECDEF51 as the recommended-track line with the central unknown-direction question cue; remove the directional arrowhead and magenta dashed-arrow styling. | wrong_direction_semantics, wrong_colour_family, missing_track_line, reference_mismatch |
| `RECTRC55` | fail | 0.86 | Redraw RECTRC55 as the two-way recommended-track witness with a track line and central opposed chevrons; remove the standalone horizontal arrow treatment. | wrong_shape, missing_track_line, reference_mismatch |
| `RECTRC56` | fail | 0.86 | Redraw RECTRC56 as the fixed-mark two-way recommended-track reference: track line plus opposed chevrons/fixed-mark cue at reference proportions; remove the standalone arrow sign. | wrong_shape, missing_track_line, reference_mismatch |
| `RECTRC57` | fail | 0.86 | Redraw RECTRC57 as the one-way recommended-track line witness with arrow/chevron on the track axis; remove the standalone horizontal dashed arrow. | wrong_shape, missing_track_line, reference_mismatch |
| `RECTRC58` | fail | 0.86 | Redraw RECTRC58 as the fixed-mark one-way recommended-track line witness with one direction cue; remove the standalone arrow sign and center-circle treatment unless the fixed-mark cue matches the reference. | wrong_shape, missing_track_line, reference_mismatch |
| `REFPNT02` | pass | 0.80 | No repair required for this automated visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `RETRFL01` | fail | 0.90 | Redraw RETRFL01 as the magenta retro-reflector comb/E witness with vertical spine and three horizontal bars; remove the triangular outline. | wrong_shape, reference_mismatch |
| `RETRFL02` | fail | 0.90 | Redraw RETRFL02 as the simplified retro-reflector comb/E witness with vertical spine and horizontal bars; remove the triangular outline. | wrong_shape, wrong_colour_family, reference_mismatch |
| `RSCSTA02` | pass | 0.74 | No repair required for this automated visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `SCALEB10` | fail | 0.90 | Redraw SCALEB10 as the vertical segmented one-mile scalebar in the reference color/segment pattern; remove the large black ladder and 1M text label. | wrong_colour_family, wrong_shape, wrong_scalebar_pattern, reference_mismatch |
| `SCALEB11` | fail | 0.90 | Redraw SCALEB11 as the vertical segmented 10-mile latitude scalebar at reference proportions; remove the horizontal bar and 10M text treatment. | wrong_orientation, wrong_shape, wrong_scalebar_pattern, reference_mismatch |
| `SNDWAV02` | fail | 0.86 | Redraw SNDWAV02 as the grey repeating sand-wave reference pattern with angular/short wavelets at reference scale; remove the large two-line brown wave motif. | wrong_colour_family, wrong_wave_pattern, wrong_scale, reference_mismatch |
| `SOUNDG02` | pass | 0.76 | No repair required for this automated visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `SWPARE51` | fail | 0.90 | Redraw SWPARE51 as the simple grey swept-area U/bracket witness; remove the magenta rounded enclosure and internal dash. | wrong_colour_family, wrong_shape, invented_internal_mark, reference_mismatch |
| `TMBYRD01` | fail | 0.84 | Redraw TMBYRD01 as the open brown timber-yard hash/grid witness; remove the enclosing square frame and match the reference stroke count/proportions. | invented_enclosure, wrong_grid_structure, reference_mismatch |
| `TNKCON02` | fail | 0.88 | Redraw TNKCON02 as the simple brown circular tank ring at reference proportions; remove extra side ovals and layered outlines. | wrong_shape, invented_detail, reference_mismatch |
| `TNKCON12` | fail | 0.88 | Redraw TNKCON12 as the simple black conspicuous tank ring/donut at reference proportions; remove extra side ovals and layered outlines. | wrong_shape, invented_detail, reference_mismatch |
| `TNKFRM01` | fail | 0.90 | Redraw TNKFRM01 as the brown tank-farm circular enclosure containing the reference clustered-dot/circle pattern; do not use three unenclosed touching rings. | missing_reference_enclosure, wrong_cluster_count, reference_mismatch |
| `TNKFRM11` | fail | 0.90 | Redraw TNKFRM11 as the black tank-farm circular enclosure containing the reference clustered-dot pattern; do not use three unenclosed touching rings. | missing_reference_enclosure, wrong_cluster_count, reference_mismatch |

## Failure Summary

- `QUARRY01`: Redraw QUARRY01 as the compact brown quarry crossed-tool/hash symbol inside the reference circular witness; remove the hourglass top/bottom bars. Codes: wrong_shape, missing_reference_enclosure, reference_mismatch.
- `RADRFL03`: Resolve the provider conflict and redraw RADRFL03 to the S-101/OpenCPN magenta starburst/ring witness, or record an explicit manual exception choosing the AquaMap reflector motif before rerun pass. Codes: conflicting_reference_witness, wrong_colour_family, reference_mismatch.
- `RASCAN01`: Redraw RASCAN01 as the brown rectangular scanner-frame witness with top horizontal bar, vertical supports, and lower pivot circle; remove the broadcast-arc motif. Codes: wrong_shape, wrong_scanner_structure, reference_mismatch.
- `RASCAN11`: Redraw RASCAN11 as the black conspicuous radar-scanner frame with top bar, vertical supports, and lower pivot circle; remove the broadcast-arc motif. Codes: wrong_shape, wrong_scanner_structure, reference_mismatch.
- `RDOCAL02`: Redraw RDOCAL02 as the one-direction radio call-in point witness: circle plus one triangular direction point; remove the R label, arrow, and outer sign circle. Codes: wrong_shape, invented_text, missing_directional_semantics, reference_mismatch.
- `RDOCAL03`: Redraw RDOCAL03 as the bidirectional radio call-in point witness with opposed triangular points around the circle; remove the R label, arrows, and enclosing sign circle. Codes: wrong_shape, invented_text, missing_bidirectional_semantics, reference_mismatch.
- `RDOSTA02`: Redraw RDOSTA02 as the simple magenta radio-station circle/point witness from S-101/OpenCPN; do not use a mast or broadcast-wave icon. Codes: wrong_symbol_class, wrong_shape, reference_mismatch.
- `RECDEF51`: Redraw RECDEF51 as the recommended-track line with the central unknown-direction question cue; remove the directional arrowhead and magenta dashed-arrow styling. Codes: wrong_direction_semantics, wrong_colour_family, missing_track_line, reference_mismatch.
- `RECTRC55`: Redraw RECTRC55 as the two-way recommended-track witness with a track line and central opposed chevrons; remove the standalone horizontal arrow treatment. Codes: wrong_shape, missing_track_line, reference_mismatch.
- `RECTRC56`: Redraw RECTRC56 as the fixed-mark two-way recommended-track reference: track line plus opposed chevrons/fixed-mark cue at reference proportions; remove the standalone arrow sign. Codes: wrong_shape, missing_track_line, reference_mismatch.
- `RECTRC57`: Redraw RECTRC57 as the one-way recommended-track line witness with arrow/chevron on the track axis; remove the standalone horizontal dashed arrow. Codes: wrong_shape, missing_track_line, reference_mismatch.
- `RECTRC58`: Redraw RECTRC58 as the fixed-mark one-way recommended-track line witness with one direction cue; remove the standalone arrow sign and center-circle treatment unless the fixed-mark cue matches the reference. Codes: wrong_shape, missing_track_line, reference_mismatch.
- `RETRFL01`: Redraw RETRFL01 as the magenta retro-reflector comb/E witness with vertical spine and three horizontal bars; remove the triangular outline. Codes: wrong_shape, reference_mismatch.
- `RETRFL02`: Redraw RETRFL02 as the simplified retro-reflector comb/E witness with vertical spine and horizontal bars; remove the triangular outline. Codes: wrong_shape, wrong_colour_family, reference_mismatch.
- `SCALEB10`: Redraw SCALEB10 as the vertical segmented one-mile scalebar in the reference color/segment pattern; remove the large black ladder and 1M text label. Codes: wrong_colour_family, wrong_shape, wrong_scalebar_pattern, reference_mismatch.
- `SCALEB11`: Redraw SCALEB11 as the vertical segmented 10-mile latitude scalebar at reference proportions; remove the horizontal bar and 10M text treatment. Codes: wrong_orientation, wrong_shape, wrong_scalebar_pattern, reference_mismatch.
- `SNDWAV02`: Redraw SNDWAV02 as the grey repeating sand-wave reference pattern with angular/short wavelets at reference scale; remove the large two-line brown wave motif. Codes: wrong_colour_family, wrong_wave_pattern, wrong_scale, reference_mismatch.
- `SWPARE51`: Redraw SWPARE51 as the simple grey swept-area U/bracket witness; remove the magenta rounded enclosure and internal dash. Codes: wrong_colour_family, wrong_shape, invented_internal_mark, reference_mismatch.
- `TMBYRD01`: Redraw TMBYRD01 as the open brown timber-yard hash/grid witness; remove the enclosing square frame and match the reference stroke count/proportions. Codes: invented_enclosure, wrong_grid_structure, reference_mismatch.
- `TNKCON02`: Redraw TNKCON02 as the simple brown circular tank ring at reference proportions; remove extra side ovals and layered outlines. Codes: wrong_shape, invented_detail, reference_mismatch.
- `TNKCON12`: Redraw TNKCON12 as the simple black conspicuous tank ring/donut at reference proportions; remove extra side ovals and layered outlines. Codes: wrong_shape, invented_detail, reference_mismatch.
- `TNKFRM01`: Redraw TNKFRM01 as the brown tank-farm circular enclosure containing the reference clustered-dot/circle pattern; do not use three unenclosed touching rings. Codes: missing_reference_enclosure, wrong_cluster_count, reference_mismatch.
- `TNKFRM11`: Redraw TNKFRM11 as the black tank-farm circular enclosure containing the reference clustered-dot pattern; do not use three unenclosed touching rings. Codes: missing_reference_enclosure, wrong_cluster_count, reference_mismatch.

## Passed Assets

`QUAPOS01`, `QUESMRK1`, `RACNSP01`, `RCTLPT52`, `REFPNT02`, `RSCSTA02`, `SOUNDG02`
