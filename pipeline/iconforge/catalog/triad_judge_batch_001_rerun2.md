# Judge Batch 001 Rerun 2 After Repair Batch 8

Judged the first 30 items from the current `pipeline/iconforge/out/triad_reference_candidate_pack/judge_queue.json` against available S-101, Aqua Map, and OpenCPN references. Helm style is allowed, but no row is final-approved here.

## Summary

- Pass: 29
- Fail: 1
- Final-approved: 0

## Passes

ACHARE02, ACHARE51, ACHBRT07, ACHPNT01, ACHRES61, ACHRES71, ADDMRK01, ADDMRK02, ADDMRK05, AIRARE02, AISDEF01, AISONE01, AISSIX01, AISSLP01, AISVES01, ARPATG01, ARPONE01, ARPSIX01, BCNCAR01, BCNCAR02, BCNCAR03, BCNCAR04, BCNDEF13, BCNGEN01, BCNGEN03, BCNGEN05, BCNGEN60, BCNGEN61, BCNGEN64

## Fails

BCNCON81

## Remaining Repair Needs

- `BCNCON81` must stay failed until an exact, inspectable OpenCPN/S-52/S-101 source crop is present. The current candidate is plausible beacon artwork, but the queue does not provide enough visual evidence to pass it under strict judge rules.
- The passed anchorage/AIS/ARPA/beacon rows are semantic passes, not final approvals. Most remaining comments are scale/stroke/native-proportion cleanup, especially where OpenCPN renders the source symbol as a tiny chart glyph.

## Notes

Repair batch 8 materially changed the first-30 result: the anchorage family now has the right anchor/restriction/information cues, AIS/ARPA are no longer generic placeholders, and the general beacon rows have their source-recognized base/circle/crossbar/question cues restored. Nothing here is marked `final-approved`; this batch only says which candidates are good enough to move past semantic repair.
