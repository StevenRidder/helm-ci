# Standard Judge Batch 032 Rerun

- Task: FORGE-14 visual/semantic rerun for owned repair batch 32 only
- Source table: `pipeline/iconforge/catalog/standard_source_table.json`
- Source batch: `pipeline/iconforge/catalog/owned_repair_batch32.json`
- Candidate status: `repaired_pending_judge_rerun`
- Counts: 11 judged, 11 pass, 0 fail, 0 final-approved
- Approval note: pass means visual/semantic rerun pass only; rows may move to `judge_pass_pending_final_approval`, but no row is human-final-approved.

## Verdicts

| Asset | Batch | Verdict | Confidence | Required change | Safety reason codes |
| --- | ---: | --- | ---: | --- | --- |
| `BCNDEF13` | 32 | pass | 0.91 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `BCNGEN01` | 32 | pass | 0.91 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `BCNGEN03` | 32 | pass | 0.91 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `BCNISD21` | 32 | pass | 0.92 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `BCNLTC01` | 32 | pass | 0.91 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `BCNSAW13` | 32 | pass | 0.90 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `BCNSAW21` | 32 | pass | 0.90 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `BCNSPP13` | 32 | pass | 0.91 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `BCNSPP21` | 32 | pass | 0.91 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `BCNSTK02` | 32 | pass | 0.90 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `BCNTOW01` | 32 | pass | 0.91 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |

## Failure Summary

- None.

## Evidence Notes

- Actual repaired SVGs were read from `pipeline/iconforge/assets/svg/owned_repair_batch32/`.
- Day/dusk/night Helm candidate renders were read from `pipeline/iconforge/out/standard_repair_batch24/renders/`.
- Provider references used include S-101 exact/reference SVG metadata, S-101 day renders, OpenCPN S-52 local day/dusk/night renders, Chart No.1 parity crops where available, S-57/OpenCPN structure, and each row semantic brief.
- Aqua Map references were used for `BCNISD21`, `BCNSAW13`, `BCNSAW21`, `BCNSPP13`, and `BCNSPP21`; no Aqua Map row reference was listed for `BCNDEF13`, `BCNGEN01`, `BCNGEN03`, `BCNLTC01`, `BCNSTK02`, or `BCNTOW01`.
- Semantic gate notes: BCNDEF13 preserves the default beacon question-mark panel; BCNGEN01/03 preserve general/default beacon pole conventions; BCNISD21 preserves the isolated-danger two-ball convention; BCNLTC01 preserves lattice tower bracing; BCNSAW13/21 preserve safe-water major/minor forms; BCNSPP13/21 preserve yellow special-purpose major/minor forms; BCNSTK02 preserves a plain stake beacon; BCNTOW01 preserves a plain tower distinct from lattice.
