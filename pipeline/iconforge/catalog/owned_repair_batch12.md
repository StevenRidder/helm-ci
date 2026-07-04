# Standard Repair Batch 4 / Owned Repair Batch 12

Owned redraws for the current 12-row standard repair queue.

- source_queue_rows: `12`
- expected_queue_rows: `12`
- failed_repaired: `9`
- blocked_or_skipped: `3`
- visual_parity: `repaired_pending_judge_rerun`

## Repaired

- `BOYCAN81`: Redraw as a can/cylindrical buoy with two ordered horizontal bands: orange over white.
- `BOYCON74`: Redraw the conical body with five distinct green-white-green-white-green bands.
- `BOYCON81`: Redraw the conical body with explicit blue-red-white-blue striping in both axes; keep pending visual rerun because the exact special-purpose pattern still needs judge confirmation.
- `BOYINB01`: Replace the filled generic buoy body with an installation-buoy line symbol: top circle, lower ring, baseline, and trapezoid frame.
- `BOYISD12`: Replace the black/red/black buoy body with the simplified isolated-danger cue: two red disks with black outlines.
- `BOYMOR01`: Replace the filled spherical substitute with the mooring line cue: lower ring, top ring, baseline arms, and arched body stroke.
- `BOYMOR11`: Replace the target-ring substitute with a compact filled mooring facility symbol: black trapezoid body plus top disk.
- `BOYPIL78`: Redraw the pillar body as a clear red/white squared/checkered pattern.
- `BOYSAW12`: Replace the split buoy/topmark substitute with the compact safe-water red disk and center mark.

## Blocked / skipped

- `BCNCON81`: hard_blocked_missing_exact_reference - BCNCON81 needs an exact local reference crop/render first; then redraw against that crop rather than approving a generic black post.
- `BOYLAT52`: blocked_missing_opencpn_day_render - Regenerate/verify out/opencpn_s52_reference/BOYLAT52__day.png before promoting this row.
- `BOYLAT53`: blocked_missing_opencpn_day_render - Regenerate/verify out/opencpn_s52_reference/BOYLAT53__day.png before promoting this row.

Rows remain pending judge rerun; none are final-approved.
