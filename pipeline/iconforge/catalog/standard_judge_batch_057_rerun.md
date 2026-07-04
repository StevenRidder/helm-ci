# Standard Judge Batch 057 Rerun

- Project: `vulkan`
- Task: `FORGE-14`
- Agent: `codex/FORGE-14-judge-b57`
- Source batch: `pipeline/iconforge/catalog/owned_repair_batch57.json`
- Source table: `pipeline/iconforge/catalog/standard_source_table.json`
- Scope: `owned_repair_batch57` 20 TOPSHP compact square-board repairs
- Approval note: pass means `judge_pass_pending_final_approval` only; no row is human-final-approved.

## Summary

| Result | Count |
| --- | ---: |
| Selected | 20 |
| Pass pending human | 9 |
| Fail | 11 |
| Final approved | 0 |

## Verdicts

| Symbol | Verdict | Confidence | Required change | Safety reason codes | Notes |
| --- | --- | ---: | --- | --- | --- |
| `TOPSHP22` | Pass pending human | 0.88 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: compact square-board silhouette, load-bearing colours, and row/reference pattern semantics match closely enough for judge_pass_pending_final_approval. No final approval is granted. |
| `TOPSHP23` | Pass pending human | 0.88 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: compact square-board silhouette, load-bearing colours, and row/reference pattern semantics match closely enough for judge_pass_pending_final_approval. No final approval is granted. |
| `TOPSHP24` | Pass pending human | 0.88 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: compact square-board silhouette, load-bearing colours, and row/reference pattern semantics match closely enough for judge_pass_pending_final_approval. No final approval is granted. |
| `TOPSHP25` | Fail | 0.90 | Redraw COLPAT6 as the compact square-board reference pattern: white field with orange nested/center block, not a 4x4 checkerboard. | `wrong_colour_pattern`, `reference_mismatch` | Fail: compact square-board silhouette is repaired, but the colour/pattern does not satisfy the source-table references closely enough for judge_pass_pending_final_approval. |
| `TOPSHP28` | Pass pending human | 0.88 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: compact square-board silhouette, load-bearing colours, and row/reference pattern semantics match closely enough for judge_pass_pending_final_approval. No final approval is granted. |
| `TOPSHP29` | Fail | 0.90 | Redraw COLPAT6 as the compact square-board reference pattern: red field with nested green/red center geometry, not a 4x4 checkerboard. | `wrong_colour_pattern`, `reference_mismatch` | Fail: compact square-board silhouette is repaired, but the colour/pattern does not satisfy the source-table references closely enough for judge_pass_pending_final_approval. |
| `TOPSHP30` | Fail | 0.90 | Redraw COLPAT6 as the compact square-board reference pattern: green field with nested white/yellow center geometry, not a 4x4 checkerboard. | `wrong_colour_pattern`, `missing_reference_cue`, `reference_mismatch` | Fail: compact square-board silhouette is repaired, but the colour/pattern does not satisfy the source-table references closely enough for judge_pass_pending_final_approval. |
| `TOPSHP31` | Fail | 0.90 | Redraw COLPAT6 as the compact square-board reference pattern: orange field with nested white center geometry, not a 4x4 checkerboard. | `wrong_colour_pattern`, `reference_mismatch` | Fail: compact square-board silhouette is repaired, but the colour/pattern does not satisfy the source-table references closely enough for judge_pass_pending_final_approval. |
| `TOPSHP32` | Pass pending human | 0.88 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: compact square-board silhouette, load-bearing colours, and row/reference pattern semantics match closely enough for judge_pass_pending_final_approval. No final approval is granted. |
| `TOPSHP33` | Fail | 0.82 | Do not promote without an exact OpenCPN/source render for this TOPSHP33 COLPAT6 row; the current 4x4 checkerboard is inconsistent with the neighboring COLPAT6 reference family. | `missing_exact_reference`, `wrong_colour_pattern`, `reference_mismatch` | Fail: compact square-board silhouette is repaired, but the colour/pattern does not satisfy the source-table references closely enough for judge_pass_pending_final_approval. |
| `TOPSHP34` | Pass pending human | 0.88 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: compact square-board silhouette, load-bearing colours, and row/reference pattern semantics match closely enough for judge_pass_pending_final_approval. No final approval is granted. |
| `TOPSHP35` | Pass pending human | 0.88 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: compact square-board silhouette, load-bearing colours, and row/reference pattern semantics match closely enough for judge_pass_pending_final_approval. No final approval is granted. |
| `TOPSHP36` | Pass pending human | 0.88 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: compact square-board silhouette, load-bearing colours, and row/reference pattern semantics match closely enough for judge_pass_pending_final_approval. No final approval is granted. |
| `TOPSHP37` | Fail | 0.90 | Restore the COLPAT6 black/white nested-square reference cue; the current all-black checker cells collapse to a solid black board and lose the inner white pattern. | `missing_required_pattern`, `missing_required_colour`, `reference_mismatch` | Fail: compact square-board silhouette is repaired, but the colour/pattern does not satisfy the source-table references closely enough for judge_pass_pending_final_approval. |
| `TOPSHP38` | Fail | 0.90 | Redraw the squared/checkered reference as the compact 2x2 orange/white quadrant layout; the current 4x4 checkerboard overstates the pattern and does not match the reference crop. | `wrong_colour_pattern`, `reference_mismatch` | Fail: compact square-board silhouette is repaired, but the colour/pattern does not satisfy the source-table references closely enough for judge_pass_pending_final_approval. |
| `TOPSHP40` | Fail | 0.90 | Restore the COLPAT6 white/black nested-square reference cue; the current 4x4 checkerboard does not match the OpenCPN reference pattern. | `wrong_colour_pattern`, `reference_mismatch` | Fail: compact square-board silhouette is repaired, but the colour/pattern does not satisfy the source-table references closely enough for judge_pass_pending_final_approval. |
| `TOPSHP41` | Fail | 0.90 | Restore the horizontal orange/white band cue shown by the reference render; the current candidate is effectively solid orange and drops the white bands. | `missing_required_colour`, `wrong_colour_pattern`, `reference_mismatch` | Fail: compact square-board silhouette is repaired, but the colour/pattern does not satisfy the source-table references closely enough for judge_pass_pending_final_approval. |
| `TOPSHP42` | Pass pending human | 0.88 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: compact square-board silhouette, load-bearing colours, and row/reference pattern semantics match closely enough for judge_pass_pending_final_approval. No final approval is granted. |
| `TOPSHP43` | Fail | 0.90 | Restore the compound COLPAT6+horizontal reference cue with green/red plus nested white/green structure; the current simple green/red/green bands are too shallow. | `missing_required_pattern`, `missing_required_colour`, `reference_mismatch` | Fail: compact square-board silhouette is repaired, but the colour/pattern does not satisfy the source-table references closely enough for judge_pass_pending_final_approval. |
| `TOPSHP44` | Fail | 0.90 | Restore the COLPAT6 yellow/white nested-square reference cue; the current yellow-only board loses the reference pattern. | `missing_required_colour`, `missing_required_pattern`, `reference_mismatch` | Fail: compact square-board silhouette is repaired, but the colour/pattern does not satisfy the source-table references closely enough for judge_pass_pending_final_approval. |

## Failed Symbols

- `TOPSHP25`: Redraw COLPAT6 as the compact square-board reference pattern: white field with orange nested/center block, not a 4x4 checkerboard.
- `TOPSHP29`: Redraw COLPAT6 as the compact square-board reference pattern: red field with nested green/red center geometry, not a 4x4 checkerboard.
- `TOPSHP30`: Redraw COLPAT6 as the compact square-board reference pattern: green field with nested white/yellow center geometry, not a 4x4 checkerboard.
- `TOPSHP31`: Redraw COLPAT6 as the compact square-board reference pattern: orange field with nested white center geometry, not a 4x4 checkerboard.
- `TOPSHP33`: Do not promote without an exact OpenCPN/source render for this TOPSHP33 COLPAT6 row; the current 4x4 checkerboard is inconsistent with the neighboring COLPAT6 reference family.
- `TOPSHP37`: Restore the COLPAT6 black/white nested-square reference cue; the current all-black checker cells collapse to a solid black board and lose the inner white pattern.
- `TOPSHP38`: Redraw the squared/checkered reference as the compact 2x2 orange/white quadrant layout; the current 4x4 checkerboard overstates the pattern and does not match the reference crop.
- `TOPSHP40`: Restore the COLPAT6 white/black nested-square reference cue; the current 4x4 checkerboard does not match the OpenCPN reference pattern.
- `TOPSHP41`: Restore the horizontal orange/white band cue shown by the reference render; the current candidate is effectively solid orange and drops the white bands.
- `TOPSHP43`: Restore the compound COLPAT6+horizontal reference cue with green/red plus nested white/green structure; the current simple green/red/green bands are too shallow.
- `TOPSHP44`: Restore the COLPAT6 yellow/white nested-square reference cue; the current yellow-only board loses the reference pattern.

## Evidence Notes

- Actual repaired SVGs were read from pipeline/iconforge/assets/svg/owned_repair_batch57/ in the detached copy.
- Candidate day/dusk/night renders were read from pipeline/iconforge/out/standard_repair_batch49/renders and OpenCPN/source-variant references from pipeline/iconforge/out.
- Each verdict was checked against pipeline/iconforge/catalog/standard_source_table.json row metadata plus the standard_judge_batch_048_rerun required_change that selected this repair family.
- The batch57 repair fixes the prior tall-rectangle silhouette by using a compact 26x26 square board with stem.
- COLPAT6 rows were accepted only where the repaired SVG matches the available nested/bordered or squared reference cue; generic 4x4 checkerboards were not accepted for non-squared rows.
- Passes are judge_pass_pending_final_approval only and grant zero final approvals.
