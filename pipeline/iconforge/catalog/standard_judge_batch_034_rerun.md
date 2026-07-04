# Standard Judge Batch 034 Rerun

- Task: FORGE-14 visual/semantic rerun for owned repair batch 34 only
- Source table: `pipeline/iconforge/catalog/standard_source_table.json`
- Source batch: `pipeline/iconforge/catalog/owned_repair_batch34.json`
- Candidate status: `repaired_pending_judge_rerun`
- Counts: 1 judged, 1 pass, 0 fail, 0 final-approved
- Approval note: pass means visual/semantic rerun pass only; rows may move to `judge_pass_pending_final_approval`, but no row is human-final-approved.

## Verdicts

| Asset | Batch | Verdict | Confidence | Required change | Safety reason codes |
| --- | ---: | --- | ---: | --- | --- |
| `BCNGEN64` | 34 | pass | 0.94 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |

## Failure Summary

- None.

## Evidence Notes

- Actual repaired SVG was read from `pipeline/iconforge/assets/svg/owned_repair_batch34/BCNGEN64.svg`.
- Day/dusk/night Helm candidate renders were read from `pipeline/iconforge/out/standard_repair_batch26/renders/`.
- Provider references used include OpenCPN S-52 local day/dusk/night renders, the Chart No.1 parity crop where available, S-57/OpenCPN structure, the prior failed judge verdict, and the row semantic brief.
- S-101 and Aqua Map references were not listed for this row in the source table.
- Semantic gate note: `BCNGEN64` now preserves the compact BCNGEN beacon/spar body with black outline and stem, and the body has four ordered horizontal bands red/white/red/white for `COLOUR3,1,3,1`. Visual parity is acceptable in Helm style; no final approval is implied.
