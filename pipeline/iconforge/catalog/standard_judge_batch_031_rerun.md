# Standard Judge Batch 031 Rerun

- Task: FORGE-14 visual/semantic rerun for owned repair batch 31 only
- Source table: `pipeline/iconforge/catalog/standard_source_table.json`
- Source batch: `pipeline/iconforge/catalog/owned_repair_batch31.json`
- Candidate status: `repaired_pending_judge_rerun`
- Counts: 6 judged, 6 pass, 0 fail, 0 final-approved
- Approval note: pass means visual/semantic rerun pass only; rows may move to `judge_pass_pending_final_approval`, but no row is human-final-approved.

## Verdicts

| Asset | Batch | Verdict | Confidence | Required change | Safety reason codes |
| --- | ---: | --- | ---: | --- | --- |
| `HULKES01` | 31 | pass | 0.90 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `LNDARE01` | 31 | pass | 0.90 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `LOCMAG01` | 31 | pass | 0.91 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `LOCMAG51` | 31 | pass | 0.91 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `MAGVAR01` | 31 | pass | 0.90 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `MAGVAR51` | 31 | pass | 0.90 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |

## Failure Summary

- None.

## Evidence Notes

- Actual repaired SVGs were read from `pipeline/iconforge/assets/svg/owned_repair_batch31/`.
- Day/dusk/night Helm candidate renders were read from `pipeline/iconforge/out/standard_repair_batch23/renders/`.
- Provider references used include S-101 exact/reference SVG metadata, S-101 day renders, OpenCPN S-52 local day/dusk/night renders, Chart No.1 parity crops where available, S-57/OpenCPN structure, and each row semantic brief.
- Aqua Map references were not listed for these rows in the source table.
- Semantic gate notes: HULKES01 preserves the low brown hulk silhouette; LNDARE01 preserves a plain land point marker; LOCMAG01/51 preserve open magenta magnetic-anomaly wedge/vertical-line variants; MAGVAR01/51 preserve filled magenta magnetic-variation wedge/vertical-line variants.
