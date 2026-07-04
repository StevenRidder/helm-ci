# Standard Repair Batch 6 / Owned Repair Batch 14

Owned redraws for the current 9-row standard repair queue.

- source_queue_rows: `9`
- expected_queue_rows: `9`
- failed_repaired: `4`
- blocked_or_skipped: `5`
- visual_parity: `repaired_pending_judge_rerun`

## Repaired

- `BOYCON74`: Redraw the green-white-green-white-green conical body with all band boundaries clipped inside the cone; no separator bars protrude outside the silhouette.
- `BOYCON81`: Use the local OpenCPN witness plus semantic brief to keep the blue-red-white-blue special-purpose conical cross-stripe cue while clipping all grid marks inside the cone.
- `BOYPIL78`: Redraw the red-white checkered pillar with the checker grid clipped inside the pillar body.
- `BOYSPH79`: Replace the wrong spherical body with a semantic conical/nun buoy body using red over green; keeps missing-reference reason codes pending visual rerun.

## Blocked / skipped

- `BCNCON81`: hard_blocked_missing_exact_reference - BCNCON81 needs an exact local reference crop/render first; then redraw against that crop rather than approving a generic black post.
- `BOYLAT52`: blocked_missing_opencpn_day_render - Regenerate/verify out/opencpn_s52_reference/BOYLAT52__day.png before promoting this row.
- `BOYLAT53`: blocked_missing_opencpn_day_render - Regenerate/verify out/opencpn_s52_reference/BOYLAT53__day.png before promoting this row.
- `BOYSPR02`: blocked_missing_opencpn_or_s101_reference - Regenerate or attach the exact OpenCPN/S-101 reference for BOYSPR02 before passing visual parity.
- `BOYSPR03`: blocked_missing_opencpn_or_s101_reference - Regenerate or attach the exact OpenCPN/S-101 reference for BOYSPR03 before passing visual parity.

Rows remain pending judge rerun; none are final-approved.
