# Standard Judge Batch 058 Rerun

- Project: `vulkan`
- Task: `FORGE-14`
- Agent: `codex/FORGE-14-judge-batch58`
- Source batch: `pipeline/iconforge/catalog/owned_repair_batch58.json`
- Source table: `pipeline/iconforge/catalog/standard_source_table.json`
- Scope: `owned_repair_batch58` 11 repaired TOPSHP nested/quadrant/compound square-board pattern rows
- Approval note: pass means `judge_pass_pending_final_approval` only; no row is human-final-approved.

## Summary

| Result | Count |
| --- | ---: |
| Selected | 11 |
| Pass pending human | 10 |
| Fail | 1 |
| Final approved | 0 |

## Verdicts

| Symbol | Verdict | Confidence | Required change | Safety reason codes | Notes |
| --- | --- | ---: | --- | --- | --- |
| `TOPSHP25` | Pass pending human | 0.90 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: compact square-board silhouette, nested white/orange COLPAT6 cue, and row/reference pattern semantics match closely enough for judge_pass_pending_final_approval. No final approval is granted. |
| `TOPSHP29` | Pass pending human | 0.90 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: compact square-board silhouette, nested red/green/red COLPAT6 cue, and row/reference pattern semantics match closely enough for judge_pass_pending_final_approval. No final approval is granted. |
| `TOPSHP30` | Pass pending human | 0.90 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: compact square-board silhouette, nested green/white/yellow COLPAT6 cue, and row/reference pattern semantics match closely enough for judge_pass_pending_final_approval. No final approval is granted. |
| `TOPSHP31` | Pass pending human | 0.90 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: compact square-board silhouette, nested orange/white COLPAT6 cue, and row/reference pattern semantics match closely enough for judge_pass_pending_final_approval. No final approval is granted. |
| `TOPSHP33` | Fail | 0.78 | Attach or regenerate the exact TOPSHP33 OpenCPN/source render witness, then rerun the judge against that exact reference before promotion; do not final-approve or pass-pending from neighboring-family inference alone. | `missing_exact_reference`, `insufficient_reference_evidence` | Fail: the batch58 SVG fixes the former checkerboard into a plausible nested green/red/green square board, but the exact OpenCPN/source render referenced by the row is absent in this detached copy, so this row cannot be promoted to judge_pass_pending_final_approval. |
| `TOPSHP37` | Pass pending human | 0.90 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: compact square-board silhouette, black/white/black nested COLPAT6 cue, and row/reference pattern semantics match closely enough for judge_pass_pending_final_approval. No final approval is granted. |
| `TOPSHP38` | Pass pending human | 0.90 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: compact square-board silhouette, orange/white quadrant cue, and row/reference pattern semantics match closely enough for judge_pass_pending_final_approval. No final approval is granted. |
| `TOPSHP40` | Pass pending human | 0.90 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: compact square-board silhouette, white/black/white nested COLPAT6 cue, and row/reference pattern semantics match closely enough for judge_pass_pending_final_approval. No final approval is granted. |
| `TOPSHP41` | Pass pending human | 0.90 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: compact square-board silhouette, restored horizontal band cue, and row/reference pattern semantics match closely enough for judge_pass_pending_final_approval. No final approval is granted. |
| `TOPSHP43` | Pass pending human | 0.90 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: compact square-board silhouette, compound horizontal plus nested cue, and row/reference pattern semantics match closely enough for judge_pass_pending_final_approval. No final approval is granted. |
| `TOPSHP44` | Pass pending human | 0.90 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: compact square-board silhouette, yellow/white/yellow nested COLPAT6 cue, and row/reference pattern semantics match closely enough for judge_pass_pending_final_approval. No final approval is granted. |

## Failed Symbols

- `TOPSHP33`: Attach or regenerate the exact TOPSHP33 OpenCPN/source render witness, then rerun the judge against that exact reference before promotion; do not final-approve or pass-pending from neighboring-family inference alone.

## Evidence Notes

- Actual repaired SVGs were read from pipeline/iconforge/assets/svg/owned_repair_batch58/ in the detached copy.
- Candidate day/dusk/night renders were read from pipeline/iconforge/out/standard_repair_batch50/renders and OpenCPN/source-variant references from pipeline/iconforge/out.
- Each verdict was checked against pipeline/iconforge/catalog/standard_source_table.json row metadata plus the standard_judge_batch_057_rerun required_change that selected this repair family.
- The batch58 repair replaces the prior 4x4 checker or collapsed solid fills with compact nested, quadrant, horizontal, or compound square-board patterns.
- TOPSHP33 was not promoted because the exact OpenCPN/source render referenced by the standard table is still absent in this detached copy.
- Passes are judge_pass_pending_final_approval only and grant zero final approvals.
