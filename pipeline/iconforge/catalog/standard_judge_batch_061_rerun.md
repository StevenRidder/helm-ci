# Standard Judge Batch 061 Rerun

- Project: `vulkan`
- Task: `FORGE-14`
- Agent: `codex/FORGE-14-judge-batch61`
- Source batch: `pipeline/iconforge/catalog/owned_repair_batch61.json`
- Source table: `pipeline/iconforge/catalog/standard_source_table.json`
- Scope: `owned_repair_batch61` 3 bounded diagonal TOWERS repairs
- Approval note: pass means `judge_pass_pending_final_approval` only; no row is human-final-approved.

## Summary

| Result | Count |
| --- | ---: |
| Selected | 3 |
| Pass pending human | 3 |
| Fail | 0 |
| Final approved | 0 |

## Verdicts

| Symbol | Verdict | Confidence | Required change | Safety reason codes | Notes |
| --- | --- | ---: | --- | --- | --- |
| `TOWERS55` | Pass pending human | 0.90 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: tapered tower silhouette is preserved, yellow/black diagonal stripe semantics are carried inside the tower body, and the rendered alpha no longer escapes to the canvas edge. Available OpenCPN/source references match closely enough for judge_pass_pending_final_approval. No final approval is granted. |
| `TOWERS94` | Pass pending human | 0.90 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: tapered tower silhouette is preserved, black/white diagonal stripe semantics are carried inside the tower body, and the visible off-body wedge from the prior rerun is gone. Available OpenCPN/source references match closely enough for judge_pass_pending_final_approval. No final approval is granted. |
| `TOWERS97` | Pass pending human | 0.90 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: tapered tower silhouette is preserved, white/black diagonal stripe semantics are carried inside the tower body, and the visible off-body wedges from the prior rerun are gone. Available OpenCPN/source references match closely enough for judge_pass_pending_final_approval. No final approval is granted. |

## Failed Symbols

- None

## Evidence Notes

- Actual repaired SVGs were read from pipeline/iconforge/assets/svg/owned_repair_batch61/ in the detached copy.
- Candidate day/dusk/night renders were read from pipeline/iconforge/out/standard_repair_batch53/renders and OpenCPN/source-variant references from pipeline/iconforge/out.
- Each verdict was checked against pipeline/iconforge/catalog/standard_source_table.json row metadata, semantic_brief, S-57 shape/color/pattern conditions, repaired SVGs, prior latest judge history, and available candidate/reference renders.
- The batch61 repair constrains the prior failing diagonal stripe geometry inside the tapered tower body for TOWERS55, TOWERS94, and TOWERS97.
- Rendered alpha bounds for all three day renders are away from the canvas edges at x=29..130, y=26..149, addressing the prior x=0 pattern-escape failure.
- Passes are judge_pass_pending_final_approval only and grant zero final approvals.
