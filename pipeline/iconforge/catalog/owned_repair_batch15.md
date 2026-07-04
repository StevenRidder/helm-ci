# Standard Repair Batch 7 / Owned Repair Batch 15

Owned redraws for a high-confidence subset of the current 75-row standard repair queue.

- source_queue_rows: `75`
- expected_queue_rows: `75`
- failed_repaired: `35`
- blocked_or_skipped: `40`
- visual_parity: `repaired_pending_judge_rerun`

## Repaired

- `BOYSPR01`: Clip the white-over-black spar banding inside the spar silhouette; no external separator strokes.
- `BOYSPR70`: Clip the black-yellow-black spar banding inside the spar silhouette; no external separator strokes.
- `BOYSPR71`: Clip the yellow-black-yellow spar banding inside the spar silhouette; no external separator strokes.
- `BOYSPR72`: Clip the black-red-black spar banding inside the spar silhouette; no external separator strokes.
- `BRTHNO01`: Redraw as a magenta berth-number circular cue and remove the invented baked text.
- `BUAARE02`: Redraw as a brown filled built-up-area dot/cluster cue without a square frame or pictorial blocks.
- `BUIREL01`: Redraw to a brown Christian cross/church schematic cue rather than a filled building silhouette.
- `BUIREL04`: Redraw to a brown non-Christian religious-building schematic cue.
- `BUIREL05`: Redraw to a brown mosque/minaret crescent cue and avoid a generic building silhouette.
- `BUIREL13`: Redraw to the conspicuous black Christian cross/church schematic cue.
- `BUIREL14`: Redraw to the conspicuous black non-Christian religious-building schematic cue.
- `BUIREL15`: Redraw to the conspicuous black mosque/minaret crescent cue.
- `BUISGL01`: Redraw as a compact brown square/building reference silhouette with no roof/door pictogram.
- `BUISGL11`: Redraw as a compact black square/building reference silhouette with no roof/door pictogram.
- `BUNSTA02`: Redraw to a water bunker-station bucket/tap cue rather than a generic droplet pictogram.
- `BUNSTA03`: Redraw to a black ballast-station cube/box service symbol rather than a diamond.
- `CBLARE51`: Replace the area placeholder with a magenta submarine-cable zig-zag line symbol.
- `CHCRDEL1`: Replace the diamond placeholder with an orange diagonal manual-delete line symbol.
- `CHCRID01`: Replace the diamond placeholder with an orange vertical update marker and ring base.
- `CHINFO06`: Replace the diamond with a circular magenta exclamation-note symbol.
- `CHINFO07`: Replace the area placeholder with a square magenta information-note symbol and i glyph.
- `CHINFO08`: Replace the diamond with a square orange information-note symbol and i glyph.
- `CHINFO09`: Replace the diamond with a circular orange exclamation-note symbol.
- `CHINFO10`: Replace the diamond with a square olive/brown information-note symbol and i glyph.
- `CHINFO11`: Replace the diamond with a circular olive/brown exclamation-note symbol.
- `CHKSYM01`: Replace the diamond with a solid black square size-check symbol.
- `CURSRA01`: Replace the diamond with an orange plus-shaped cursor.
- `CURSRB01`: Replace the diamond with a segmented open-centre orange cursor.
- `CUSTOM01`: Redraw as a circular red/white customs mark rather than a buoy-like diamond.
- `DANGER51`: Replace the diamond with a dotted black danger boundary symbol.
- `DANGER52`: Replace the diamond with a dotted black danger boundary symbol with a stronger central hazard dot.
- `DAYSQR01`: Redraw as a square/rectangular daymark panel with the stem/attachment.
- `DAYTRI01`: Redraw as an upright triangular daymark with a stem; preserve point-up orientation.
- `DAYTRI05`: Redraw as an inverted triangular daymark with a stem; preserve point-down orientation.
- `EBLVRM11`: Replace the diamond with the filled orange circular EBL/VRM origin marker.

## Blocked / skipped

- `BCNCON81`: hard_blocked_missing_exact_reference - BCNCON81 needs an exact local reference crop/render first; then redraw against that crop rather than approving a generic black post.
- `BOYLAT52`: blocked_missing_local_reference_render - Regenerate/verify out/opencpn_s52_reference/BOYLAT52__day.png before promoting this row.
- `BOYLAT53`: blocked_missing_local_reference_render - Regenerate/verify out/opencpn_s52_reference/BOYLAT53__day.png before promoting this row.
- `BOYSPR02`: blocked_missing_local_reference_render - Regenerate or attach the exact OpenCPN/S-101 reference for BOYSPR02 before passing visual parity.
- `BOYSPR03`: blocked_missing_local_reference_render - Regenerate or attach the exact OpenCPN/S-101 reference for BOYSPR03 before passing visual parity.
- `BOYSUP01`: skipped_batch15_lower_confidence_or_geometry_heavy - Redraw as the super-buoy platform/trapezoid/ring reference silhouette while preserving red/black load-bearing colours.
- `BOYSUP02`: skipped_batch15_lower_confidence_or_geometry_heavy - Redraw BOYSUP02 as the black super-buoy platform/trapezoid reference silhouette.
- `BOYSUP03`: skipped_batch15_lower_confidence_or_geometry_heavy - Redraw with the super-buoy platform silhouette and the LANBY star/asterisk topmark cue; preserve red/black colour semantics.
- `BOYSUP65`: skipped_batch15_lower_confidence_or_geometry_heavy - Redraw on the super-buoy platform/trapezoid reference body while preserving vertical red/white order.
- `BRIDGE01`: skipped_batch15_lower_confidence_or_geometry_heavy - Remove the invented black crosshair/target detail and redraw the opening-bridge ring to match the S-101/OpenCPN witness.
- `CAIRNS01`: skipped_batch15_lower_confidence_or_geometry_heavy - Redraw as the cairn beacon: three stacked/ring-like cairn stones with the small base marker, removing the blue diamond body.
- `CAIRNS11`: skipped_batch15_lower_confidence_or_geometry_heavy - Redraw as the black cairn beacon with three stone/ring lobes and the base marker shown in the references.
- `CGUSTA02`: skipped_batch15_lower_confidence_or_geometry_heavy - Redraw as the coastguard CG sign/box in the reference style, preserving the white/purple reference treatment and point marker.
- `CHIMNY01`: skipped_batch15_lower_confidence_or_geometry_heavy - Redraw as the chimney structure silhouette, including the vertical stack, base ring, and top/smoke form.
- `CHIMNY11`: skipped_batch15_lower_confidence_or_geometry_heavy - Redraw as the black conspicuous chimney silhouette with vertical stack, base ring, and top/smoke form.
- `CRANES01`: skipped_batch15_lower_confidence_or_geometry_heavy - Redraw as the crane silhouette shown by S-101/OpenCPN/Aqua Map, not a buoy-like diamond.
- `CTNARE51`: skipped_batch15_lower_confidence_or_geometry_heavy - Replace the dashed area placeholder with the magenta caution-note circle/exclamation marker.
- `CTYARE51`: skipped_batch15_lower_confidence_or_geometry_heavy - Replace the dashed box/plus with the magenta caution-note circle/exclamation marker.
- `CURDEF01`: skipped_batch15_lower_confidence_or_geometry_heavy - Redraw as the vertical current arrow with side question marks, preserving the reference grey/blue stroke treatment.
- `CURENT01`: skipped_batch15_lower_confidence_or_geometry_heavy - Replace the diamond with the current arrow/barb silhouette.
- `DANGER53`: blocked_missing_reference_or_exact_crop - Locate/render the authoritative DANGER53 reference, then replace the generic diamond with that hazard silhouette before any visual pass.
- `DAYSQR21`: skipped_batch15_lower_confidence_or_geometry_heavy - Replace the diamond with the square/rectangular daymark panel and stem/cross detail.
- `DGPS01DRFSTA01`: blocked_missing_reference_or_exact_crop - Resolve the exact reference for DGPS01DRFSTA01 and replace the generic diamond with that station symbol.
- `DIRBOY01`: skipped_batch15_lower_confidence_or_geometry_heavy - Replace the diamond with the direction-of-buoyage arrow/approach symbol and circles.
- `DIRBOYA1`: skipped_batch15_lower_confidence_or_geometry_heavy - Redraw the direction-of-buoyage symbol with the arrow/approach body and correct red-left/green-right circle order.
- `DIRBOYB1`: skipped_batch15_lower_confidence_or_geometry_heavy - Redraw the direction-of-buoyage symbol with the arrow/approach body and correct green-left/red-right circle order.
- `DISMAR03`: skipped_batch15_lower_confidence_or_geometry_heavy - Replace the diamond with the distance-mark text/marker form shown by the reference.
- `DISMAR04`: skipped_batch15_lower_confidence_or_geometry_heavy - Replace the diamond with the distance-point text/marker form from OpenCPN.
- `DISMAR05`: skipped_batch15_lower_confidence_or_geometry_heavy - Replace the diamond with the black concentric distance target mark.
- `DISMAR06`: skipped_batch15_lower_confidence_or_geometry_heavy - Replace the diamond with the concentric 1 km distance target mark.
- `DNGHILIT`: skipped_batch15_lower_confidence_or_geometry_heavy - Replace the black stake with the translucent red danger-highlight square/border symbol.
- `DOMES001`: skipped_batch15_lower_confidence_or_geometry_heavy - Redraw as the dome silhouette with curved top and base marker.
- `DOMES011`: skipped_batch15_lower_confidence_or_geometry_heavy - Redraw as the black conspicuous dome silhouette with curved top and base marker.
- `DSHAER01`: skipped_batch15_lower_confidence_or_geometry_heavy - Redraw as the dish aerial with curved dish, support stand, and base marker.
- `DSHAER11`: skipped_batch15_lower_confidence_or_geometry_heavy - Redraw as the black conspicuous dish aerial with curved dish, support stand, and base marker.
- `DWRTPT51`: skipped_batch15_lower_confidence_or_geometry_heavy - Replace the diamond with the DW text route mark in the reference style.
- `DWRUTE51`: skipped_batch15_lower_confidence_or_geometry_heavy - Replace the dashed box/plus with the magenta vertical double-headed route arrow.
- `EBBSTR01`: skipped_batch15_lower_confidence_or_geometry_heavy - Replace the diamond with the vertical ebb-stream arrow symbol.
- `ERBLTIK1`: skipped_batch15_lower_confidence_or_geometry_heavy - Replace the diamond with the orange dashed range arc.
- `ESSARE01`: skipped_batch15_lower_confidence_or_geometry_heavy - Replace the dashed area placeholder with the ESSA/PSSA boundary text/line marker.

Rows remain pending judge rerun; none are final-approved.
