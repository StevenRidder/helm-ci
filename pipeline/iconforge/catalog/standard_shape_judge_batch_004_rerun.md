# Standard Shape Judge Batch 004 Rerun

- Source batch: `catalog/owned_repair_batch10.json`
- Selection: `helm_candidate.candidate_status == repaired_pending_judge_rerun` and `helm_candidate.source_batch == catalog/owned_repair_batch10.json`
- Verdicts: 20 total, 16 pass, 4 fail
- Scope: semantic family/shape/topmark/color order only; no SVG edits
- Blockers: none

| Symbol | Pass | Confidence | Required change | Safety reason codes |
| --- | --- | ---: | --- | --- |
| `BCNTOW90` | PASS | 0.84 | No shape-semantic repair required; optional lattice/detail polish can wait for visual/style QA. | - |
| `BLKADJ01` | PASS | 0.98 | No semantic repair required. | - |
| `BORDER01` | PASS | 0.96 | No semantic repair required. | - |
| `BOYBAR01` | FAIL | 0.72 | Resolve the brief/reference conflict, then render the barrel buoy with the required red/black colour semantics if the current semantic_brief is authoritative. | wrong_colour, missing_required_colour, brief_reference_conflict |
| `BOYCAN01` | PASS | 0.86 | No shape-semantic repair required. | - |
| `BOYCAN62` | FAIL | 0.78 | Add the required green/black colour semantics, or correct the semantic_brief if BOYCAN62 is intentionally an uncoloured generic/paper-style can. | wrong_colour, missing_required_colour, brief_reference_conflict |
| `BOYCAN72` | PASS | 0.97 | No semantic repair required. | - |
| `BOYCAN73` | PASS | 0.97 | No semantic repair required. | - |
| `BOYCAN74` | PASS | 0.86 | No shape-semantic repair required; later visual QA may decide whether the full repeated source colour list needs more than the rendered RWR cue. | - |
| `BOYCAN76` | PASS | 0.98 | No semantic repair required. | - |
| `BOYCAN77` | PASS | 0.88 | No semantic repair required. | - |
| `BOYCAN78` | PASS | 0.98 | No semantic repair required. | - |
| `BOYCAN79` | FAIL | 0.93 | Change BOYCAN79 body fill from yellow to orange while preserving the can body and black outline/stem. | wrong_colour |
| `BOYCAN81` | PASS | 0.84 | No shape-semantic repair required; keep this row flagged for later visual QA if the source colour order ambiguity must be resolved. | - |
| `BOYCAN82` | PASS | 0.86 | No shape-semantic repair required; later visual QA may decide whether the full repeated source colour list needs more than the rendered RWR cue. | - |
| `BOYCAN83` | PASS | 0.85 | No shape-semantic repair required; later visual QA may decide whether the full repeated source colour list needs more than the rendered RWR cue. | - |
| `BOYCON01` | FAIL | 0.72 | Resolve the brief/reference conflict, then render the conical buoy with the required red/black colour semantics if the current semantic_brief is authoritative. | wrong_colour, missing_required_colour, brief_reference_conflict |
| `BOYCON63` | PASS | 0.98 | No semantic repair required. | - |
| `BOYCON66` | PASS | 0.97 | No semantic repair required. | - |
| `BOYCON67` | PASS | 0.97 | No semantic repair required. | - |

## Notes

- The repaired batch fixes the utility/border families and the critical can/cone three-band sequences.
- Failures are color/brief issues, not wrong-symbol-family issues: `BOYBAR01`, `BOYCAN62`, and `BOYCON01` now have the right body families but do not carry all colours required by the current semantic brief; `BOYCAN79` uses yellow where the brief requires orange.
- Repeated red/white source lists such as `red/white/red/white/red` were accepted where the repaired render and OpenCPN witness encode the visible `red/white/red` lateral cue from the prior repair contract.
