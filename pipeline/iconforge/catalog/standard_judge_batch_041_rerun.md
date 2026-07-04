# Standard Judge Batch 041 Rerun

- Task: FORGE-14 visual/semantic rerun for owned repair batch 41 only
- Source table: `pipeline/iconforge/catalog/standard_source_table.json`
- Source batch: `pipeline/iconforge/catalog/owned_repair_batch41.json`
- Candidate status: `repaired_pending_judge_rerun`
- Counts: 15 judged, 15 pass, 0 fail, 0 final-approved
- Approval note: pass means visual/semantic rerun pass only; rows may move to `judge_pass_pending_final_approval`, but no row is human-final-approved.

## Verdicts

| Asset | Batch | Verdict | Confidence | Required change | Safety reason codes |
| --- | ---: | --- | ---: | --- | --- |
| `NMKPRH02` | 41 | pass | 0.88 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `NMKPRH06` | 41 | pass | 0.93 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `NMKPRH07` | 41 | pass | 0.91 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `NMKPRH08` | 41 | pass | 0.94 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `NMKPRH10` | 41 | pass | 0.92 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `NMKPRH11` | 41 | pass | 0.92 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `NMKPRH12` | 41 | pass | 0.91 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `NMKPRH13` | 41 | pass | 0.91 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `NMKPRH14` | 41 | pass | 0.92 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `NMKRCD01` | 41 | pass | 0.90 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `NMKRCD02` | 41 | pass | 0.91 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `NMKRCD03` | 41 | pass | 0.92 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `NMKRCD04` | 41 | pass | 0.92 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `NMKRCD05` | 41 | pass | 0.94 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |
| `NMKRCD06` | 41 | pass | 0.94 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - |

## Failure Summary

- None.

## Evidence Notes

- Actual repaired SVGs were read from `pipeline/iconforge/assets/svg/owned_repair_batch41/`.
- Source metadata came from `pipeline/iconforge/catalog/standard_source_table.json`, including each row semantic brief, S-57/S-52 structure, prior failed judge text, and provider reference metadata.
- The catalog lists OpenCPN reference render paths for these rows, but `pipeline/iconforge/out/opencpn_s52_reference/` was not present in this detached worktree; the rerun therefore used the row metadata plus repaired SVG visual inspection, including local scratch thumbnails with CSS variables expanded.
- Prohibition rows now use either the red prohibition board or the side-specific split diamond as appropriate, preserve the expected glyph meaning, and include a visible prohibition slash where required.
- Recommended-passage rows now use yellow or green/white recommended diamonds, or blue direction boards for traffic-direction symbols, and preserve one-vs-both and left-vs-right direction cues.
- Minor Helm stroke/radius simplifications are treated as acceptable because the notice-symbol semantics remain recognisable and no row is final-approved by this artifact.

## Per-Symbol Notes

- `NMKPRH02`: Pass pending human: the repaired asset has the red entry-prohibited board silhouette, red/white/black load-bearing colours, and recognisable prohibition semantics. The older expected text mentions horizontal bars, but the required change and semantic brief are satisfied at notice-symbol level; final reference approval is still outside this artifact. No final approval implied.
- `NMKPRH06`: Pass pending human: correct prohibition-board family, correct passing/overtaking arrows, and visible slash are present. Minor Helm stroke simplification does not change the notice meaning. No final approval implied.
- `NMKPRH07`: Pass pending human: correct red prohibition board and berth/quay prohibition meaning are present with a visible slash. No final approval implied.
- `NMKPRH08`: Pass pending human: anchor is now inside the correct red prohibition board with visible slash; the prior standalone-anchor failure is repaired. No final approval implied.
- `NMKPRH10`: Pass pending human: turning-prohibited board, turn glyph, red/white/black colours, and visible slash are present. No final approval implied.
- `NMKPRH11`: Pass pending human: avoid-wash wave glyph is now on the red prohibition board with visible slash. No final approval implied.
- `NMKPRH12`: Pass pending human: side-specific split-diamond prohibition marker is preserved with left-side red cue and visible slash. No final approval implied.
- `NMKPRH13`: Pass pending human: side-specific split-diamond prohibition marker is mirrored from NMKPRH12 with right-side red cue and visible slash. No final approval implied.
- `NMKPRH14`: Pass pending human: engine-boat prohibition is represented by red board, motorboat glyph, and visible slash. No final approval implied.
- `NMKRCD01`: Pass pending human: yellow recommended-passage diamond has the both-directions cue and no center-ring placeholder. No final approval implied.
- `NMKRCD02`: Pass pending human: paired yellow diamonds plus one-way cue preserve the one-direction semantic distinction. No final approval implied.
- `NMKRCD03`: Pass pending human: green/white right-side recommended-passage diamond is present and distinct from the left-side sibling. No final approval implied.
- `NMKRCD04`: Pass pending human: green/white left-side recommended-passage diamond is present and distinct from the right-side sibling. No final approval implied.
- `NMKRCD05`: Pass pending human: blue recommended-traffic board with left arrow preserves the required direction cue. No final approval implied.
- `NMKRCD06`: Pass pending human: blue recommended-traffic board with right arrow preserves the required direction cue. No final approval implied.
