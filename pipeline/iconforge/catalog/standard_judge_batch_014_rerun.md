# Standard Judge Batch 014 Rerun

- Project: `vulkan`
- Task: `FORGE-18`
- Agent: `codex/FORGE-18-visual-rerun-batch14-local`
- Selection: `repaired_pending_judge_rerun` from `catalog/owned_repair_batch14.json`
- Counts: 4 judged, 1 pass, 3 fail, 0 final-approved

| Symbol | Pass | Confidence | Observed | Required change | Safety reason codes |
|---|---:|---:|---|---|---|
| `BOYCON74` | `false` | 0.82 | Conical/nun body is clipped cleanly and the previous external separator bars are gone, but the visible symbol still reads as white-green-white with only tiny apex/base green slivers. It does not clearly preserve the required green-white-green-white-green five-band sequence. | Redraw or proportion the conical body so the five ordered green-white-green-white-green bands are visibly present inside the cone; keep the clipping/no-external-strokes fix. | missing_visible_colour_bands, wrong_colour_order_readability, reference_mismatch |
| `BOYCON81` | `false` | 0.76 | Conical/nun body is clipped and includes blue/red/white/blue colours, but the semi-transparent vertical overlays and internal grid produce a muddy cross-stripe pattern that still does not match the OpenCPN witness or the simpler source-priority rendering. | Redraw BOYCON81 against the OpenCPN/reference witness so the blue-red-white-blue horizontal/vertical stripe pattern is unambiguous; remove any internal grid lines or translucent overlays that are not part of the reference symbol. | wrong_pattern, unsafe_special_purpose_confusion, reference_mismatch |
| `BOYPIL78` | `true` | 0.84 | Pillar buoy body with red/white checkered squares clipped inside the silhouette, black outline, and stem; the previous external checker/grid spill is gone. | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| `BOYSPH79` | `false` | 0.78 | Candidate now uses a conical/nun red-over-green body, fixing the prior spherical Helm render relative to the semantic brief. However, the OpenCPN reference render is absent locally and the available source-priority/Chart No.1 witnesses still show a circular/spherical red-green cue, so visual parity cannot be proven. | Regenerate or attach the exact OpenCPN/S-101 reference for BOYSPH79 and reconcile the row's conical-versus-spherical contract; then rerun visual judging before any pass. | missing_reference_render, conflicting_reference_witness, approval_blocked_reference_gap |

No rows are final-approved by this rerun.
