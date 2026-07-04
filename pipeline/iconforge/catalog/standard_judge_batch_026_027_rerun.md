# Standard Judge Batch 026/027 Rerun

- Task: FORGE-18 visual/semantic rerun for repaired batches 26 and 27 only
- Source table: `pipeline/iconforge/catalog/standard_source_table.json`
- Source batches: `pipeline/iconforge/catalog/owned_repair_batch26.json`, `pipeline/iconforge/catalog/owned_repair_batch27.json`
- Candidate status: `repaired_pending_judge_rerun`
- Counts: 10 judged, 9 pass, 1 fail, 0 final-approved
- Approval note: pass means visual/semantic rerun pass only; no row is human-final-approved.

## Verdicts

| Asset | Batch | Verdict | Confidence | Required change | Safety reason codes |
| --- | --- | --- | ---: | --- | --- |
| `MORFAC03` | 26 | pass | 0.84 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `MORFAC04` | 26 | pass | 0.89 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `MSTCON04` | 26 | pass | 0.90 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `MSTCON14` | 26 | pass | 0.90 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `POSGEN04` | 26 | pass | 0.82 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `UWTROC03` | 27 | pass | 0.93 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `UWTROC04` | 27 | pass | 0.92 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `WRECKS01` | 27 | fail | 0.78 | Remove the white circular aperture and redraw closer to the S-101/OpenCPN WRECKS01 exposed-wreck silhouette: low horizontal hull plus sloped wreckage/mast, without a generic filled sail triangle. | wrong_wreck_variant_detail, invented_internal_shape, reference_mismatch |
| `WRECKS04` | 27 | pass | 0.91 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |
| `WRECKS05` | 27 | pass | 0.88 | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. | - |

## Failure Summary

- `WRECKS01`: Remove the white circular aperture and redraw closer to the S-101/OpenCPN WRECKS01 exposed-wreck silhouette: low horizontal hull plus sloped wreckage/mast, without a generic filled sail triangle. Codes: wrong_wreck_variant_detail, invented_internal_shape, reference_mismatch.

## Evidence Notes

- Actual repaired SVGs were read from `pipeline/iconforge/assets/svg/owned_repair_batch26/` and `pipeline/iconforge/assets/svg/owned_repair_batch27/`.
- Day/dusk/night renders were read from `pipeline/iconforge/out/standard_repair_batch18/renders/` and `pipeline/iconforge/out/standard_repair_batch19/renders/`.
- Provider references used include S-101 exact/reference SVGs, OpenCPN S-52 local renders, Aqua Map refs where available, Chart 1/source-variant matrix crops, and each row semantic brief.
