# Standard Judge Batch 028/029 Rerun

- Task: FORGE-18 visual/semantic rerun for repaired batches 28 and 29 only
- Source table: `pipeline/iconforge/catalog/standard_source_table.json`
- Source batches: `pipeline/iconforge/catalog/owned_repair_batch28.json`, `pipeline/iconforge/catalog/owned_repair_batch29.json`
- Candidate status: `repaired_pending_judge_rerun`
- Counts: 7 judged, 7 pass, 0 fail, 0 final-approved
- Approval note: pass means visual/semantic rerun pass only; no row is human-final-approved.

## Verdicts

| Asset | Batch | Verdict | Confidence | Required change | Safety reason codes |
| --- | ---: | --- | ---: | --- | --- |
| `TSSCRS51` | 28 | pass | 0.90 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `TSSLPT51` | 28 | pass | 0.93 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `TSSRON51` | 28 | pass | 0.92 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `TWRDEF51` | 28 | pass | 0.88 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `TWRTPT52` | 28 | pass | 0.90 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `TWRTPT53` | 28 | pass | 0.88 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `WRECKS01` | 29 | pass | 0.90 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |

## Failure Summary

- None.

## Evidence Notes

- Actual repaired SVGs were read from `pipeline/iconforge/assets/svg/owned_repair_batch28/` and `pipeline/iconforge/assets/svg/owned_repair_batch29/`.
- Day/dusk/night renders were read from `pipeline/iconforge/out/standard_repair_batch20/renders/` and `pipeline/iconforge/out/standard_repair_batch21/renders/`.
- Provider references used include S-101 exact/reference SVGs, OpenCPN S-52 local renders, and each row semantic brief.
- `WRECKS01` specifically confirms the prior failed white-aperture issue is gone; the candidate is now a low hull plus sloped wreckage/mast exposed-wreck silhouette.
