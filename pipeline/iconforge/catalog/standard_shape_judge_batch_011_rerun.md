# Standard Shape Judge Batch 011 Rerun

- Source batch: `catalog/owned_repair_batch11.json`
- Selection: `helm_candidate.candidate_status == repaired_pending_shape_rerun` and `helm_candidate.source_batch == catalog/owned_repair_batch11.json`
- Verdicts: 4 total, 4 pass, 0 fail
- Scope: semantic family/shape/topmark/color order only; no SVG edits
- Blockers: none

| Symbol | Pass | Confidence | Required change | Safety reason codes |
| --- | --- | ---: | --- | --- |
| `BOYBAR01` | PASS | 0.91 | No shape-semantic repair required; continue to visual parity/final approval if needed. | - |
| `BOYCAN62` | PASS | 0.92 | No shape-semantic repair required; continue to visual parity/final approval if needed. | - |
| `BOYCAN79` | PASS | 0.97 | No shape-semantic repair required; continue to visual parity/final approval if needed. | - |
| `BOYCON01` | PASS | 0.91 | No shape-semantic repair required; continue to visual parity/final approval if needed. | - |

## Notes

- `BOYBAR01` now preserves the barrel body and carries the current semantic-brief red/black colour pair.
- `BOYCAN62` now preserves the can/cylindrical body and carries the current semantic-brief green/black colour pair.
- `BOYCAN79` now preserves the can/cylindrical body and uses orange rather than the earlier yellow.
- `BOYCON01` now preserves the conical/nun body and carries the current semantic-brief red/black colour pair.
- The S-101/OpenCPN witnesses for `BOYBAR01` and `BOYCON01` remain outline-style references, but this shape-semantic gate treats the current semantic brief as authoritative for required load-bearing colours.
