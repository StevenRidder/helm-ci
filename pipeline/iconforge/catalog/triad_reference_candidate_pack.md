# Triad Reference Candidate Pack

S-57/S-52 icon rows mapped to S-101, Aqua Map, and OpenCPN references.

## Summary

- triad_rows: `824`
- generated_candidate_svgs: `824`
- reference_backed_judge_queue_rows: `783`
- hard_pile_no_svg_candidate: `0`
- s101_rows: `244`
- aquamap_rows: `109`
- opencpn_rows: `777`
- reference_gap_candidate_rows: `41`
- rendered_candidate_pngs: `0`

## Outputs

- JSON: `catalog/triad_reference_candidate_pack.json`
- CSV table: `catalog/triad_reference_candidate_table.csv`
- Judge queue: `out/triad_reference_candidate_pack/judge_queue.json`

## Policy

- S-101, Aqua Map, and OpenCPN are reference inputs for shape/semantic matching.
- Canonical Helm candidates are generated-owned SVGs under `assets/svg/triad_generated/`.
- No row is visually approved until the one-symbol LLM judge passes it.
- Rows with references but no SVG renderer/candidate stay in the hard-pile.
