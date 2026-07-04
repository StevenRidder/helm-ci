# Standard Repair Batch 5 / Owned Repair Batch 13

Owned redraws for the current 35-row standard repair queue.

- source_queue_rows: `35`
- expected_queue_rows: `35`
- failed_repaired: `29`
- blocked_or_skipped: `6`
- visual_parity: `repaired_pending_judge_rerun`

## Repaired

- `BOYSPH01`: Remove invented blue/grey and redraw a spherical buoy with red-over-black semantic bands only.
- `BOYSPH65`: Rotate the red/white spherical buoy body to vertical stripes.
- `BOYSPH66`: Add the missing lower red band so the spherical buoy reads red-green-red.
- `BOYSPH70`: Add the missing lower black band so the spherical buoy reads black-yellow-black.
- `BOYSPH71`: Add the missing lower yellow band so the spherical buoy reads yellow-black-yellow.
- `BOYSPP11`: Replace the generic black lower body with a simplified yellow pillar special-purpose buoy cue.
- `BOYSPP15`: Replace the generic body with a simplified yellow conical TSS starboard buoy cue.
- `BOYSPP25`: Replace the generic body with a simplified yellow can/cylindrical TSS port buoy cue.
- `BOYSPR01`: Remove invented blue and redraw the spar using only white/black semantic colours.
- `BOYSPR70`: Add the missing lower black band so the spar reads black-yellow-black.
- `BOYSPR71`: Add the missing lower yellow band so the spar reads yellow-black-yellow.
- `BOYSPR72`: Add the missing lower black band so the spar reads black-red-black.
- `BOYSUP01`: Remove invented blue/grey and redraw the super-buoy with red/black semantic colours only.
- `BOYSUP02`: Remove the blue/grey lower fill so the super-buoy is black only.
- `BOYSUP03`: Add a LANBY/super-buoy top cue and remove the invented blue field.
- `BOYSUP65`: Rotate the red/white super-buoy body to vertical stripes.
- `BRIDGE01`: Replace the diamond placeholder with an opening-bridge ring/circular silhouette.
- `BRTHNO01`: Replace the diamond placeholder with a berth-number circular reference cue.
- `BUAARE02`: Replace the dashed square placeholder with a built-up-area block cluster cue.
- `BUIREL01`: Replace the diamond placeholder with a Christian religious-building cross/church silhouette.
- `BUIREL04`: Replace the diamond placeholder with a non-Christian religious-building temple/dome silhouette.
- `BUIREL05`: Replace the diamond placeholder with a mosque/minaret silhouette.
- `BUIREL13`: Use the conspicuous Christian religious-building silhouette in black.
- `BUIREL14`: Use the conspicuous non-Christian religious-building silhouette in black.
- `BUIREL15`: Use the conspicuous mosque/minaret silhouette in black.
- `BUISGL01`: Replace the diamond placeholder with a brown single-building square/roof cue.
- `BUISGL11`: Replace the diamond placeholder with a black conspicuous single-building square/roof cue.
- `BUNSTA01`: Replace the diamond placeholder with a diesel bunker-station fuel-pump cue.
- `BUNSTA02`: Replace the diamond placeholder with a water bunker-station tap/drop cue.

## Blocked / skipped

- `BCNCON81`: hard_blocked_missing_exact_reference - BCNCON81 needs an exact local reference crop/render first; then redraw against that crop rather than approving a generic black post.
- `BOYLAT52`: blocked_missing_opencpn_day_render - Regenerate/verify out/opencpn_s52_reference/BOYLAT52__day.png before promoting this row.
- `BOYLAT53`: blocked_missing_opencpn_day_render - Regenerate/verify out/opencpn_s52_reference/BOYLAT53__day.png before promoting this row.
- `BOYSPH79`: blocked_missing_opencpn_day_render - Replace the spherical body with the required conical/nun red/green buoy and regenerate/verify the OpenCPN reference render before promotion.
- `BOYSPR02`: blocked_missing_opencpn_or_s101_reference - Regenerate or attach the exact OpenCPN/S-101 reference for BOYSPR02 before passing visual parity.
- `BOYSPR03`: blocked_missing_opencpn_or_s101_reference - Regenerate or attach the exact OpenCPN/S-101 reference for BOYSPR03 before passing visual parity.

Rows remain pending judge rerun; none are final-approved.
