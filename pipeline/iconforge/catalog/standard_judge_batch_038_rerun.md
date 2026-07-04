# Standard Judge Batch 038 Rerun

- Task: FORGE-14 visual/semantic rerun for owned repair batch 38 only
- Source table: `pipeline/iconforge/catalog/standard_source_table.json`
- Source batch: `pipeline/iconforge/catalog/owned_repair_batch38.json`
- Candidate status: `repaired_pending_judge_rerun`
- Counts: 12 judged, 12 pass, 0 fail, 0 final-approved
- Approval note: pass means visual/semantic rerun pass only; rows may move to `judge_pass_pending_final_approval`, but no row is human-final-approved.

## Verdicts

| Asset | Batch | Verdict | Confidence | Required change | Safety reason codes |
| --- | ---: | --- | ---: | --- | --- |
| `NMKINF01` | 38 | pass | 0.90 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `NMKINF02` | 38 | pass | 0.92 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `NMKINF03` | 38 | pass | 0.88 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `NMKINF04` | 38 | pass | 0.91 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `NMKINF05` | 38 | pass | 0.92 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `NMKINF06` | 38 | pass | 0.89 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `NMKINF19` | 38 | pass | 0.93 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `NMKINF20` | 38 | pass | 0.89 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `NMKINF21` | 38 | pass | 0.87 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `NMKINF22` | 38 | pass | 0.92 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `NMKINF23` | 38 | pass | 0.91 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `NMKINF24` | 38 | pass | 0.91 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |

## Failure Summary

- None.

## Evidence Notes

- Actual repaired SVGs were read from `pipeline/iconforge/assets/svg/owned_repair_batch38/`.
- Source metadata was read from `pipeline/iconforge/catalog/standard_source_table.json` and `pipeline/iconforge/catalog/owned_repair_batch38.json`.
- Provider reference directory `pipeline/iconforge/reference_providers` was absent in this checkout; Aqua Map references were not listed for these rows.
- Listed OpenCPN S-52 reference render paths were catalog witnesses only; the PNG files were not present under `pipeline/iconforge/out` on this branch tip.
- A color-correct temporary contact sheet was rendered outside the repo by substituting Helm palette tokens into the owned SVGs and rendering with system Chrome.
- All 12 candidates preserve the NMKINF notice-board family, required board color convention, and load-bearing glyph semantics: entry permitted, overhead power line, weir, cable ferry, ferry, berthing, anchoring, making fast, vehicle loading/unloading, turning, centered crossing, and right-side secondary waterway.
