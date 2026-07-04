# Standard Judge Batch 030 Rerun

- Task: FORGE-14 visual/semantic rerun for owned repair batch 30 only
- Source table: `pipeline/iconforge/catalog/standard_source_table.json`
- Source batch: `pipeline/iconforge/catalog/owned_repair_batch30.json`
- Candidate status: `repaired_pending_judge_rerun`
- Counts: 8 judged, 8 pass, 0 fail, 0 final-approved
- Approval note: pass means visual/semantic rerun pass only; rows may move to `judge_pass_pending_final_approval`, but no row is human-final-approved.

## Verdicts

| Asset | Batch | Verdict | Confidence | Required change | Safety reason codes |
| --- | ---: | --- | ---: | --- | --- |
| `FAIRWY51` | 30 | pass | 0.91 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `FAIRWY52` | 30 | pass | 0.91 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `FLDSTR01` | 30 | pass | 0.88 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `FRYARE51` | 30 | pass | 0.90 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `FSHFAC02` | 30 | pass | 0.88 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `FSHFAC03` | 30 | pass | 0.88 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `HRBFAC09` | 30 | pass | 0.91 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `PILPNT02` | 30 | pass | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |

## Failure Summary

- None.

## Evidence Notes

- Actual repaired SVGs were read from `pipeline/iconforge/assets/svg/owned_repair_batch30/`.
- Day/dusk/night Helm candidate renders were read from `pipeline/iconforge/out/standard_repair_batch22/renders/`.
- Provider references used include S-101 exact/reference SVGs, S-101 day renders, OpenCPN S-52 local day/dusk/night renders, S-57/OpenCPN structure, and each row semantic brief.
- Aqua Map references were not listed for these rows in the source table.
- Semantic gate notes: FAIRWY51/52 preserve gray hollow fairway arrows; FLDSTR01 preserves gray flood-stream arrow with slanted spring-rate ticks; FRYARE51 preserves magenta ferry-route styling; FSHFAC02/03 preserve gray fishing-stake conventions; HRBFAC09 preserves magenta fish/arc harbour symbol without text/enclosure; PILPNT02 preserves a filled black pile/bollard point.
