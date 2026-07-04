# Standard Judge Batch 007/009 Beacon Rerun

- Task: FORGE-14 visual/semantic rerun for owned repair batches 7 and 9 beacon/stake/tower repairs only
- Source table: `pipeline/iconforge/catalog/standard_source_table.json`
- Source batches: `pipeline/iconforge/catalog/owned_repair_batch7.json`, `pipeline/iconforge/catalog/owned_repair_batch9.json`
- Candidate status: `repaired_pending_judge_rerun`
- Counts: 20 judged, 19 pass, 1 fail, 0 final-approved
- Approval note: pass means visual/semantic rerun pass only; rows may move to `judge_pass_pending_final_approval`, but no row is human-final-approved.

## Verdicts

| Asset | Batch | Verdict | Confidence | Required change | Safety reason codes |
| --- | ---: | --- | ---: | --- | --- |
| `BCNGEN05` | 7 | pass | 0.88 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `BCNGEN60` | 7 | pass | 0.89 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `BCNGEN61` | 7 | pass | 0.89 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `BCNGEN64` | 7 | fail | 0.94 | Redraw BCNGEN64 with four ordered horizontal bands red/white/red/white (COLOUR3,1,3,1) inside the BCNGEN beacon/spar body; keep the black outline and stem, then rerender day/dusk/night for judge rerun. | wrong_colour_order, missing_colour_bands, reference_mismatch |
| `BCNGEN65` | 9 | pass | 0.92 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `BCNGEN70` | 9 | pass | 0.93 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `BCNGEN71` | 9 | pass | 0.93 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `BCNGEN76` | 9 | pass | 0.93 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `BCNLAT23` | 9 | pass | 0.90 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `BCNLAT50` | 9 | pass | 0.84 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `BCNSTK03` | 9 | pass | 0.84 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `BCNSTK77` | 9 | pass | 0.88 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `BCNSTK79` | 9 | pass | 0.91 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `BCNSTK80` | 9 | pass | 0.91 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `BCNTOW63` | 9 | pass | 0.90 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `BCNTOW66` | 9 | pass | 0.90 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `BCNTOW70` | 9 | pass | 0.92 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `BCNTOW71` | 9 | pass | 0.92 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `BCNTOW74` | 9 | pass | 0.91 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `BCNTOW76` | 9 | pass | 0.92 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |

## Failure Summary

- `BCNGEN64`: Redraw BCNGEN64 with four ordered horizontal bands red/white/red/white (COLOUR3,1,3,1) inside the BCNGEN beacon/spar body; keep the black outline and stem, then rerender day/dusk/night for judge rerun.

## Evidence Notes

- Actual repaired SVGs were read from `pipeline/iconforge/assets/svg/owned_repair_batch7/` and `pipeline/iconforge/assets/svg/owned_repair_batch9/`.
- Batch 7 day/dusk/night Helm renders were read from `pipeline/iconforge/out/triad_judge_repair_batch1/renders/`; batch 9 renders were read from `pipeline/iconforge/out/standard_repair_batch1/renders/`.
- Provider references used include OpenCPN S-52 local day/dusk/night renders, Chart No.1 parity crops where present, S-57/OpenCPN structure, and each row semantic brief. S-101 and AquaMap references were not listed for these rows in the source table.
- Semantic gate notes: all pass rows preserve beacon/stake/tower class and load-bearing colour order; `BCNSTK77` retains a metadata conflict for final approval review, but its OpenCPN/render evidence supports the green-leading repaired cue.
- `BCNGEN64` fails because the repaired SVG has only two red/white bands while the OpenCPN/S-57 row requires the full red/white/red/white sequence.
