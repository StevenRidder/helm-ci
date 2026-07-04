# Helm Icon Style Contract

This is the house look for generated-owned Helm chart symbols.

## OpenBridge-Inspired Thin Style

- Primary stroke: `1.8`
- Caps and joins: round
- Colours: semantic CSS variables only, rendered through the Helm/OpenBridge palettes
- Geometry: simple, centered, chart-symbol-first construction
- Detail level: readable at small chart sizes; avoid decorative micro-detail
- Typography: Arial/Helvetica/system sans only when a symbol genuinely requires text

## Do Not

- Do not turn chart symbols into app icons.
- Do not use cartoon, doodle, sketch, mascot, emoji, or Comic-style forms.
- Do not add props or flourishes that are not present in the reference symbol family.
- Do not make borders heavy just to make the symbol feel polished.
- Do not enlarge naturally tiny chart marks into pictograms unless the reference family requires it.

## QA Gates

- `standard_style_audit` checks SVG hygiene and style metadata.
- `standard_craft_audit` checks rendered readability, centering, and visible craft risks.
- `standard_recognition_judge_queue` packages Helm candidates, references, semantic metadata, and the no-doodle judge contract for visual review.

The output can be beautiful, but it must still read as a nautical chart symbol first.
