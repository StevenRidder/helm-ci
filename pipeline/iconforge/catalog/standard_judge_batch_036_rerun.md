# Standard Judge Batch 036 Rerun

- Task: FORGE-14 visual/semantic rerun for owned repair batch 36 only
- Source table: `pipeline/iconforge/catalog/standard_source_table.json`
- Source batch: `pipeline/iconforge/catalog/owned_repair_batch36.json`
- Candidate status: `repaired_pending_judge_rerun`
- Counts: 2 judged, 2 pass, 0 fail, 0 final-approved
- Approval note: pass means visual/semantic rerun pass only; rows may move to `judge_pass_pending_final_approval`, but no row is human-final-approved.

## Verdicts

| Asset | Batch | Verdict | Confidence | Required change | Safety reason codes |
| --- | ---: | --- | ---: | --- | --- |
| `SNDWAV02` | 36 | pass | 0.91 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `TIDCUR01` | 36 | pass | 0.92 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |

## Failure Summary

- None.

## Evidence Notes

- Actual repaired SVGs were read from `pipeline/iconforge/assets/svg/owned_repair_batch36/`.
- Day/dusk/night Helm candidate renders were read from `pipeline/iconforge/out/standard_repair_batch28/renders/`.
- Provider references used include S-101 exact/reference SVG metadata, S-101 day renders, OpenCPN S-52 local day/dusk/night renders where available, Chart No.1 parity crops where available, S-57/OpenCPN structure, each row semantic brief, and the prior failed judge reason.
- `SNDWAV02` now preserves the critical sand-wave check: short grey angular/stepped wavelets rather than smooth swell curves.
- `TIDCUR01` now preserves the critical predicted-current check: orange dashed/discrete arrow stack, visibly distinct from the solid `TIDCUR02` actual-current arrow and without the `TIDCUR02` dot.
- Aqua Map references were not listed for these rows in the source table.
