# Standard Judge Batch 033 Rerun

- Task: FORGE-14 visual/semantic rerun for owned repair batch 33 only
- Source table: `pipeline/iconforge/catalog/standard_source_table.json`
- Source batch: `pipeline/iconforge/catalog/owned_repair_batch33.json`
- Candidate status: `repaired_pending_judge_rerun`
- Counts: 11 judged, 11 pass, 0 fail, 0 final-approved
- Approval note: pass means visual/semantic rerun pass only; rows may move to `judge_pass_pending_final_approval`, but no row is human-final-approved.

## Verdicts

| Asset | Batch | Verdict | Confidence | Required change | Safety reason codes |
| --- | ---: | --- | ---: | --- | --- |
| `DAYSQR01` | 33 | pass | 0.91 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `DAYSQR21` | 33 | pass | 0.91 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `DAYTRI01` | 33 | pass | 0.91 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `DAYTRI05` | 33 | pass | 0.91 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `LITFLT01` | 33 | pass | 0.88 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `LITFLT02` | 33 | pass | 0.88 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `LITVES01` | 33 | pass | 0.89 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `LITVES02` | 33 | pass | 0.88 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `RADRFL03` | 33 | pass | 0.90 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `RASCAN01` | 33 | pass | 0.90 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `RASCAN11` | 33 | pass | 0.90 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |

## Failure Summary

- None.

## Evidence Notes

- Actual repaired SVGs were read from `pipeline/iconforge/assets/svg/owned_repair_batch33/`.
- Day/dusk/night Helm candidate renders were read from `pipeline/iconforge/out/standard_repair_batch25/renders/`.
- Provider references used include S-101 exact/reference SVG metadata, S-101 day renders, OpenCPN S-52 local day/dusk/night renders, Chart No.1 parity crops where available, S-57/OpenCPN structure, each row semantic brief, and Aqua Map only for `RADRFL03`.
- Semantic gate notes: DAYSQR01/DAYSQR21 preserve square daymark forms; DAYTRI01/DAYTRI05 preserve point-up and point-down triangular daymark orientation; LITFLT01/LITFLT02 preserve full/simplified light-float forms; LITVES01/LITVES02 preserve full/simplified light-vessel forms; RADRFL03 follows the S-101/OpenCPN magenta starburst/ring witness; RASCAN01/RASCAN11 preserve radar-scanner frame structures with the correct brown/black class colour.
