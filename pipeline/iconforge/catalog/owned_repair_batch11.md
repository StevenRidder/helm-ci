# Standard Repair Batch 3 / Owned Repair Batch 11

Owned redraws for the 35-row standard repair queue.

- source_queue_rows: `35`
- failed_repaired: `34`
- blocked_or_skipped: `1`
- visual_parity: `repaired_pending_judge_rerun`

## Repaired

- `BOYBAR01`: Render the barrel buoy with red/black semantic colours from the current semantic_brief; keep pending rerun because the provider reference conflict still needs judge arbitration.
- `BOYCAN62`: Render the can buoy with green/black semantic colours from the current semantic_brief; keep pending rerun because the generic-reference conflict still needs judge arbitration.
- `BOYCAN79`: Change BOYCAN79 body fill from yellow to orange while preserving the can body and black outline/stem.
- `BOYCON01`: Render the conical buoy with red/black semantic colours from the current semantic_brief; keep pending rerun because the provider reference conflict still needs judge arbitration.
- `BOYCON71`: Add the missing lower black band so the conical body reads black-yellow-black, not two-band black-yellow.
- `BOYCON72`: Add the missing lower yellow band so the conical body reads yellow-black-yellow, not two-band yellow-black.
- `BOYCON74`: Redraw with five ordered green/white/green/white/green bands on the conical body.
- `BOYCON78`: Change BOYCON78 to vertical red/white striping on the conical buoy, not horizontal bands.
- `BOYCON79`: Replace the conical buoy silhouette with the required stake/perch beacon geometry while preserving red-over-green order.
- `BOYCON80`: Add the missing lower white band so the conical body reads white-orange-white.
- `BOYCON81`: Add the missing final blue segment and resolve the required horizontal/vertical striping pattern against the exact reference before approval.
- `BOYDEF03`: Redraw as the default buoy symbol family from S-101/OpenCPN, including the default/unknown cue; do not substitute a magenta generic buoy.
- `BOYGEN03`: Remove invented magenta/blue fills and redraw as the black default buoy family shown by the references.
- `BOYINB01`: Redraw the installation buoy silhouette from the provider references while keeping black as the load-bearing colour.
- `BOYISD12`: Redraw BOYISD12 with the isolated-danger visual cue from S-101/Aqua Map/OpenCPN, including the paired red danger marks/topmark treatment as applicable.
- `BOYLAT13`: Add the missing lower green band to the conical buoy.
- `BOYLAT14`: Add the missing lower red band to the conical buoy.
- `BOYLAT23`: Use a can/cylindrical buoy body and add the missing lower green band.
- `BOYLAT24`: Use a can/cylindrical buoy body and add the missing lower red band.
- `BOYLAT26`: Match the narrow segmented BOYLAT26 reference silhouette while preserving white-over-red order.
- `BOYLAT27`: Match the narrow segmented BOYLAT27 reference silhouette while preserving white-over-green order.
- `BOYLAT52`: Add the missing lower red band and obtain/verify the exact local OpenCPN render before promoting.
- `BOYLAT53`: Add the missing lower green band and obtain/verify the exact local OpenCPN render before promoting.
- `BOYMOR01`: Remove the invented blue fill and redraw as the black spherical/barrel mooring buoy from the reference.
- `BOYMOR11`: Redraw the simplified mooring facility/buoy symbol, not a generic can buoy.
- `BOYPIL01`: Remove the invented blue lower fill and make the full pillar body black.
- `BOYPIL66`: Add the missing lower red band to the pillar body.
- `BOYPIL67`: Add the missing lower green band to the pillar body.
- `BOYPIL70`: Add the missing lower black band to the pillar body.
- `BOYPIL71`: Add the missing lower yellow band to the pillar body.
- `BOYPIL72`: Add the missing lower black band to the pillar body.
- `BOYPIL73`: Change BOYPIL73 to vertical red/white striping on the pillar body.
- `BOYPIL78`: Replace horizontal bands with the red/white squared/checkered pattern on the pillar body.
- `BOYSAW12`: Redraw BOYSAW12 to match the safe-water simplified reference cue and remove the misleading black lower body.

## Blocked / skipped

- `BCNCON81`: hard_blocked_missing_exact_reference - BCNCON81 needs an exact local reference crop/render first; then redraw against that crop rather than approving a generic black post.

Rows remain pending shape/visual judge reruns; none are final-approved.
