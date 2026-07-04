# Standard Judge Batch 047 Rerun

- Task: FORGE-14 visual/semantic rerun for owned repair batch 47 only
- Source table: `pipeline/iconforge/catalog/standard_source_table.json`
- Source batch: `pipeline/iconforge/catalog/owned_repair_batch47.json`
- Candidate status: `repaired_pending_judge_rerun`
- Counts: 20 judged, 6 pass, 14 fail, 0 final-approved
- Approval note: pass means visual/semantic rerun pass only; rows may move to `judge_pass_pending_final_approval`, but no row is human-final-approved.

## Verdicts

| Asset | Batch | Verdict | Confidence | Required change | Safety reason codes |
| --- | ---: | --- | ---: | --- | --- |
| `TOPSHP00` | 47 | fail | 0.88 | Redraw as the TOPSHP00 square/target-like board reference rather than a tall rectangular panel; preserve red board with the required white-white-red/border pattern. | `wrong_topmark_silhouette`, `wrong_aspect_ratio`, `reference_mismatch` |
| `TOPSHP01` | 47 | fail | 0.90 | Redraw TOPSHP01 with the tapered board/trapezoid topmark silhouette from the OpenCPN/Chart No.1 witness while preserving orange/white detail. | `wrong_topmark_silhouette`, `missing_trapezoid_board_shape`, `reference_mismatch` |
| `TOPSHP02` | 47 | fail | 0.90 | Redraw TOPSHP02 with the tapered board/trapezoid topmark silhouette from the provider witness while preserving red/black vertical order. | `wrong_topmark_silhouette`, `missing_trapezoid_board_shape`, `reference_mismatch` |
| `TOPSHP03` | 47 | fail | 0.90 | Redraw TOPSHP03 with the tapered board/trapezoid topmark silhouette from the provider witness while preserving orange/white detail. | `wrong_topmark_silhouette`, `missing_trapezoid_board_shape`, `reference_mismatch` |
| `TOPSHP04` | 47 | fail | 0.90 | Redraw TOPSHP04 with the tapered board/trapezoid topmark silhouette from the provider witness while preserving red/black vertical order. | `wrong_topmark_silhouette`, `missing_trapezoid_board_shape`, `reference_mismatch` |
| `TOPSHP05` | 47 | pass | 0.91 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `TOPSHP07` | 47 | pass | 0.92 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `TOPSHP08` | 47 | fail | 0.94 | Redraw TOPSHP08 with the required red/red/yellow S-57 horizontal/banded pattern; the current vertical red/yellow split drops one red band and uses the wrong stripe orientation. | `wrong_colour_order`, `wrong_colour_pattern`, `missing_required_colour`, `reference_mismatch` |
| `TOPSHP09;TE('%s'` | 47 | fail | 0.94 | Redraw TOPSHP09 with the required red/red/green horizontal/S-57 band pattern while keeping the text-bearing cue; the current vertical stripes do not match the required colour pattern. | `wrong_colour_pattern`, `wrong_stripe_orientation`, `reference_mismatch` |
| `TOPSHP10` | 47 | pass | 0.90 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `TOPSHP11` | 47 | pass | 0.90 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `TOPSHP12` | 47 | pass | 0.90 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `TOPSHP13` | 47 | pass | 0.88 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `TOPSHP15;TE('%s'` | 47 | fail | 0.94 | Redraw TOPSHP15 with the required red/red/yellow S-57 band pattern while keeping the text-bearing cue; the current vertical stripes do not match the required colour pattern. | `wrong_colour_pattern`, `wrong_stripe_orientation`, `reference_mismatch` |
| `TOPSHP16` | 47 | fail | 0.93 | Redraw TOPSHP16 with the provider red/white S-57 topmark pattern; the current vertical split does not match the reference colour layout. | `wrong_colour_pattern`, `wrong_stripe_orientation`, `reference_mismatch` |
| `TOPSHP17` | 47 | fail | 0.93 | Redraw TOPSHP17 to the provider topmark silhouette instead of a rectangular board; preserve orange/black/orange order once the shape is corrected. | `wrong_topmark_silhouette`, `reference_mismatch` |
| `TOPSHP18` | 47 | fail | 0.92 | Redraw TOPSHP18 to the provider topmark silhouette; a solid rectangular panel does not match the referenced topmark shape. | `wrong_topmark_silhouette`, `missing_colour_pattern`, `reference_mismatch` |
| `TOPSHP19` | 47 | fail | 0.93 | Redraw TOPSHP19 to the provider topmark silhouette; the current rectangular red/yellow panel has the wrong shape for the reference family. | `wrong_topmark_silhouette`, `reference_mismatch` |
| `TOPSHP20` | 47 | fail | 0.92 | Redraw TOPSHP20 to the provider topmark silhouette; a solid rectangular panel does not match the referenced topmark shape. | `wrong_topmark_silhouette`, `missing_colour_pattern`, `reference_mismatch` |
| `TOPSHP21` | 47 | fail | 0.91 | Redraw TOPSHP21 with the provider square/board silhouette and aspect; the current tall rectangle does not match the reference shape. | `wrong_topmark_silhouette`, `wrong_aspect_ratio`, `reference_mismatch` |

## Failure Summary

- `TOPSHP00`: Redraw as the TOPSHP00 square/target-like board reference rather than a tall rectangular panel; preserve red board with the required white-white-red/border pattern.
- `TOPSHP01`: Redraw TOPSHP01 with the tapered board/trapezoid topmark silhouette from the OpenCPN/Chart No.1 witness while preserving orange/white detail.
- `TOPSHP02`: Redraw TOPSHP02 with the tapered board/trapezoid topmark silhouette from the provider witness while preserving red/black vertical order.
- `TOPSHP03`: Redraw TOPSHP03 with the tapered board/trapezoid topmark silhouette from the provider witness while preserving orange/white detail.
- `TOPSHP04`: Redraw TOPSHP04 with the tapered board/trapezoid topmark silhouette from the provider witness while preserving red/black vertical order.
- `TOPSHP08`: Redraw TOPSHP08 with the required red/red/yellow S-57 horizontal/banded pattern; the current vertical red/yellow split drops one red band and uses the wrong stripe orientation.
- `TOPSHP09;TE('%s'`: Redraw TOPSHP09 with the required red/red/green horizontal/S-57 band pattern while keeping the text-bearing cue; the current vertical stripes do not match the required colour pattern.
- `TOPSHP15;TE('%s'`: Redraw TOPSHP15 with the required red/red/yellow S-57 band pattern while keeping the text-bearing cue; the current vertical stripes do not match the required colour pattern.
- `TOPSHP16`: Redraw TOPSHP16 with the provider red/white S-57 topmark pattern; the current vertical split does not match the reference colour layout.
- `TOPSHP17`: Redraw TOPSHP17 to the provider topmark silhouette instead of a rectangular board; preserve orange/black/orange order once the shape is corrected.
- `TOPSHP18`: Redraw TOPSHP18 to the provider topmark silhouette; a solid rectangular panel does not match the referenced topmark shape.
- `TOPSHP19`: Redraw TOPSHP19 to the provider topmark silhouette; the current rectangular red/yellow panel has the wrong shape for the reference family.
- `TOPSHP20`: Redraw TOPSHP20 to the provider topmark silhouette; a solid rectangular panel does not match the referenced topmark shape.
- `TOPSHP21`: Redraw TOPSHP21 with the provider square/board silhouette and aspect; the current tall rectangle does not match the reference shape.

## Evidence Notes

- Actual repaired SVGs were read from `pipeline/iconforge/assets/svg/owned_repair_batch47/` in the detached copy.
- Prior failures came from `catalog/standard_judge_batch_012.json` and `catalog/standard_judge_batch_013.json`; their required changes were checked against the new SVGs.
- Day candidate renders and provider witnesses were read from the source worktree `/private/tmp/helm-forge14/pipeline/iconforge/out/` because those ignored render artifacts are not present in the clean detached clone.
- `TOPSHP09;TE('%s'` and `TOPSHP15;TE('%s'` preserve a visible text cue, but fail because their required red/red/green and red/red/yellow S-57 band patterns are rendered as vertical stripes.
- Passes are limited to the simple triangle repairs where silhouette, orientation, and load-bearing colour matched the semantic/provider references: `TOPSHP05`, `TOPSHP07`, `TOPSHP10`, `TOPSHP11`, `TOPSHP12`, and `TOPSHP13`.
