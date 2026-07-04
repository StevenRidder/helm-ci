# Standard Judge Batch 043 Rerun

- Project: `vulkan`
- Task: `FORGE-14`
- Agent: `codex/FORGE-14-judge-batch43`
- Source batch: `pipeline/iconforge/catalog/owned_repair_batch43.json`
- Source table: `pipeline/iconforge/catalog/standard_source_table.json`
- Scope: `NOTBRD12, NOTMRK01, NOTMRK02, NOTMRK03, OSPONE02, OSPSIX02, OWNSHP01, OWNSHP05, PIER0001, PLNPOS01, PLNPOS02, PLNSPD03, PLNSPD04, POSITN02`

Pass means `judge_pass_pending_final_approval` only. This rerun grants zero final approvals.

## Summary

| Result | Count |
| --- | ---: |
| Selected | 14 |
| Pass pending human | 7 |
| Fail | 7 |
| Final approved | 0 |

## Verdicts

| Symbol | Verdict | Confidence | Required change | Safety reason codes | Notes |
| --- | --- | ---: | --- | --- | --- |
| `NOTBRD12` | Pass pending human | 0.91 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: required yellow board/post silhouette is present and the old diamond/ring placeholder is gone. Scale and stroke weight are Helm styling differences only; no final approval implied. |
| `NOTMRK01` | Pass pending human | 0.92 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: prohibition board shape, red/white/black colour family, and slash semantics are restored. No final approval implied. |
| `NOTMRK02` | Pass pending human | 0.90 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: the diamond placeholder is gone and the red regulation board with white field preserves the requested restriction-board semantics. No final approval implied. |
| `NOTMRK03` | Fail | 0.88 | Replace with the NOTMRK03 reference information/recommendation notice-board shape and preserve the blue/black reference colour family or provide explicit metadata justifying the alternate white-board convention. | wrong_shape, wrong_colour_family, invented_detail, reference_mismatch | Fail: the repair removes the diamond but changes the reference color family and silhouette by introducing a white posted board and text glyph. Human review may later accept a different convention, but this standard rerun cannot. |
| `OSPONE02` | Fail | 0.90 | Use the OSPONE02 one-minute vector tick as a short reference-aligned black tick/line, or record explicit orientation/colour metadata before rerun approval. | wrong_line_orientation, wrong_colour_family, reference_mismatch, unsafe_ownship_confusion | Fail: the repair restores a tick-like line but changes both orientation and colour family relative to the available reference, which is load-bearing for this line/tick symbol. |
| `OSPSIX02` | Fail | 0.91 | Replace the hash/grid mark with the OSPSIX02 six-minute vector tick/line geometry matching the reference line semantics. | wrong_shape, wrong_line_semantics, invented_detail, unsafe_ownship_confusion | Fail: the candidate is no longer a simple vector tick/line and introduces hash/grid semantics not present in the row reference. |
| `OWNSHP01` | Fail | 0.87 | Render OWNSHP01 as the reference constant-size ownship target, preserving the circular target/ring semantics and reference colour family without extra crosshair axes unless metadata explicitly requires them. | wrong_shape, wrong_colour_family, invented_detail, unsafe_ownship_confusion | Fail: the candidate is a recognisable ownship-like target, but it changes the reference colour family and adds crosshair axes that are not in the provider witness. |
| `OWNSHP05` | Fail | 0.93 | Use a scaled hull/ship outline matching OWNSHP05 reference geometry with a conning-position cue; do not substitute a generic triangular ownship arrow. | wrong_shape, wrong_colour_family, missing_scaled_hull, unsafe_ownship_confusion | Fail: conning-position intent is present, but the scaled vessel silhouette is replaced by a triangular target/arrow and the reference colour family is changed. |
| `PIER0001` | Pass pending human | 0.84 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human, with low confidence: the repair preserves the blue circular mark and an internal pier-extension cue, although the cue is simplified versus the small OpenCPN raster. No final approval implied. |
| `PLNPOS01` | Pass pending human | 0.93 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: ellipse shape and planned-position red/orange colour family are preserved. No final approval implied. |
| `PLNPOS02` | Fail | 0.89 | Replace the plus/crosshair with the PLNPOS02 planned-position crossline geometry, preserving the single-line/oriented-line semantics from the reference. | wrong_shape, wrong_line_semantics, invented_detail, missing_planned_route_annotation | Fail: the repair changes a line annotation into a crosshair/plus mark, altering the line semantics for the planned-position row. |
| `PLNSPD03` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human, with low confidence: rectangular speed-box shape and planned-route colour family are restored. The S label is treated as non-final Helm annotation and still needs human/crop review before any final approval. |
| `PLNSPD04` | Pass pending human | 0.85 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human, with low confidence: alternate planned-speed box meaning and orange colour family are present. The dashed outline/S label remain human-review details and this artifact grants no final approval. |
| `POSITN02` | Fail | 0.92 | Replace the diagonal X with the POSITN02 orthogonal position-fix crosshair/plus geometry while preserving the orange colour family. | wrong_line_semantics, wrong_shape, unsafe_ownship_confusion, reference_mismatch | Fail: colour and circular family are correct, but the diagonal X changes the position-fix crosshair semantics. |

## Pass Notes

- `NOTBRD12`: Pass pending human: required yellow board/post silhouette is present and the old diamond/ring placeholder is gone. Scale and stroke weight are Helm styling differences only; no final approval implied.
- `NOTMRK01`: Pass pending human: prohibition board shape, red/white/black colour family, and slash semantics are restored. No final approval implied.
- `NOTMRK02`: Pass pending human: the diamond placeholder is gone and the red regulation board with white field preserves the requested restriction-board semantics. No final approval implied.
- `PIER0001`: Pass pending human, with low confidence: the repair preserves the blue circular mark and an internal pier-extension cue, although the cue is simplified versus the small OpenCPN raster. No final approval implied.
- `PLNPOS01`: Pass pending human: ellipse shape and planned-position red/orange colour family are preserved. No final approval implied.
- `PLNSPD03`: Pass pending human, with low confidence: rectangular speed-box shape and planned-route colour family are restored. The S label is treated as non-final Helm annotation and still needs human/crop review before any final approval.
- `PLNSPD04`: Pass pending human, with low confidence: alternate planned-speed box meaning and orange colour family are present. The dashed outline/S label remain human-review details and this artifact grants no final approval.

## Failed Symbols

- `NOTMRK03`: Replace with the NOTMRK03 reference information/recommendation notice-board shape and preserve the blue/black reference colour family or provide explicit metadata justifying the alternate white-board convention.
- `OSPONE02`: Use the OSPONE02 one-minute vector tick as a short reference-aligned black tick/line, or record explicit orientation/colour metadata before rerun approval.
- `OSPSIX02`: Replace the hash/grid mark with the OSPSIX02 six-minute vector tick/line geometry matching the reference line semantics.
- `OWNSHP01`: Render OWNSHP01 as the reference constant-size ownship target, preserving the circular target/ring semantics and reference colour family without extra crosshair axes unless metadata explicitly requires them.
- `OWNSHP05`: Use a scaled hull/ship outline matching OWNSHP05 reference geometry with a conning-position cue; do not substitute a generic triangular ownship arrow.
- `PLNPOS02`: Replace the plus/crosshair with the PLNPOS02 planned-position crossline geometry, preserving the single-line/oriented-line semantics from the reference.
- `POSITN02`: Replace the diagonal X with the POSITN02 orthogonal position-fix crosshair/plus geometry while preserving the orange colour family.

## Evidence Notes

- Actual repaired SVGs were read from `pipeline/iconforge/assets/svg/owned_repair_batch43/`.
- Candidate day/dusk/night renders were present under `pipeline/iconforge/out/standard_repair_batch35/renders/`; day renders were compared against the OpenCPN reference day witnesses.
- Provider references used include each row's `semantic_brief`, S-57/S-52 instruction metadata, prior failed judge notes, OpenCPN local render references, and available source/provider coverage flags from `standard_source_table.json`.
- No S-101 or Aqua Map provider references were listed for these selected rows in the source table snapshot; OpenCPN references were treated as visual witnesses only, not copied artwork.
- Passes remain pass-pending-human only and do not grant final approval.
