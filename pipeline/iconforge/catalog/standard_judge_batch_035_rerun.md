# Standard Judge Batch 035 Rerun

- Task: FORGE-14 visual/semantic rerun for owned repair batch 35 only
- Source table: `pipeline/iconforge/catalog/standard_source_table.json`
- Source batch: `pipeline/iconforge/catalog/owned_repair_batch35.json`
- Candidate status: `repaired_pending_judge_rerun`
- Counts: 11 judged, 9 pass, 2 fail, 0 final-approved
- Approval note: pass means visual/semantic rerun pass only; rows may move to `judge_pass_pending_final_approval`, but no row is human-final-approved.

## Verdicts

| Asset | Batch | Verdict | Confidence | Required change | Safety reason codes |
| --- | ---: | --- | ---: | --- | --- |
| `PRDINS02` | 35 | pass | 0.91 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `PSSARE01` | 35 | pass | 0.88 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `QUARRY01` | 35 | pass | 0.92 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `SNDWAV02` | 35 | fail | 0.89 | Redraw SNDWAV02 as short grey angular/stepped sand-wave wavelets at the S-101/OpenCPN reference scale; remove the large smooth swell-like wave curve. | `wrong_wave_pattern`, `wrong_scale`, `reference_mismatch` |
| `SPRING02` | 35 | pass | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `SWPARE51` | 35 | pass | 0.93 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `TIDCUR01` | 35 | fail | 0.93 | Redraw TIDCUR01 as the predicted-current orange dashed arrow stack: keep separate chevrons, break the shaft into dashed/discrete segments including the lower tail, and keep it visually distinct from solid TIDCUR02 actual-current arrow. | `wrong_line_pattern`, `missing_predicted_current_dash_pattern`, `dangerous_actual_current_confusion`, `reference_mismatch` |
| `TIDCUR02` | 35 | pass | 0.92 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `TIDCUR03` | 35 | pass | 0.94 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `TIDEHT01` | 35 | pass | 0.92 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `TIDSTR01` | 35 | pass | 0.92 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |

## Failure Summary

- `SNDWAV02`: Redraw SNDWAV02 as short grey angular/stepped sand-wave wavelets at the S-101/OpenCPN reference scale; remove the large smooth swell-like wave curve.
- `TIDCUR01`: Redraw TIDCUR01 as the predicted-current orange dashed arrow stack: keep separate chevrons, break the shaft into dashed/discrete segments including the lower tail, and keep it visually distinct from solid TIDCUR02 actual-current arrow.

## Evidence Notes

- Actual repaired SVGs were read from `pipeline/iconforge/assets/svg/owned_repair_batch35/`.
- Day/dusk/night Helm candidate renders were read from `pipeline/iconforge/out/standard_repair_batch27/renders/`.
- Provider references used include S-101 exact/reference SVG metadata, S-101 day renders, OpenCPN S-52 local day/dusk/night renders where available, Chart No.1 parity crops where available, S-57/OpenCPN structure, each row semantic brief, and the prior failed judge reason.
- Aqua Map references were not listed for these rows in the source table; `PSSARE01` had no OpenCPN day/dusk/night render file available in the local reference directory, so its S-101 text witness carried the label check.
- Semantic gate notes: `PRDINS02`, `PSSARE01`, `QUARRY01`, `SPRING02`, `SWPARE51`, `TIDCUR02`, `TIDCUR03`, `TIDEHT01`, and `TIDSTR01` preserve the required symbol class and load-bearing shape/colour/text. `SNDWAV02` fails because the candidate remains a smooth swell-like wave instead of short angular sand-wave wavelets. `TIDCUR01` fails because the predicted-current dashed/discrete arrow distinction is not preserved and the glyph is too close to solid `TIDCUR02`.
