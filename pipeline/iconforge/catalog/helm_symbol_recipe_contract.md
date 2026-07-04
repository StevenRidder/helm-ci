# Helm Symbol Recipe Contract

Status: `provisional_symbol_recipe_contract_ready`

This FORGE-28 artifact defines the backend-owned recipe vocabulary that
connects semantic evidence rows to Helm-flavored symbol rendering. It
does not approve runtime export.

- rows: `824`
- versions: `{'recipe': 'helm_symbol_recipe_v1', 'palette': 'helm_palette_v1', 'pattern': 'helm_pattern_v1', 'shape_family': 'helm_shape_family_v1', 'style': 'helm_style_contract_v1'}`
- status_counts: `{'manual_exception_required': 206, 'recipe_missing': 44, 'recipe_ready': 574}`
- shape_family_counts: `{'ais_target': 5, 'anchoring_symbol': 6, 'area_pattern': 26, 'beacon_general': 69, 'beacon_stake': 1, 'buoy_barrel': 4, 'buoy_can': 28, 'buoy_cone': 25, 'buoy_generic': 24, 'buoy_pillar': 16, 'buoy_spar': 22, 'buoy_sphere': 14, 'buoy_super': 5, 'conditional_portrayal': 18, 'daymark_panel': 121, 'generic_chart_symbol': 166, 'isolated_danger_mark': 6, 'line_style': 57, 'notice_mark': 63, 'rock_symbol': 1, 'topmark_standard': 39, 'tower_lighthouse': 81, 'wreck_symbol': 27}`
- pattern_counts: `{'diagonal_stripes': 5, 'horizontal_bands': 134, 'line_dash': 9, 'missing': 250, 'notice_pictogram': 63, 'ordered_sequence': 43, 'solid': 259, 'squared': 6, 'vertical_stripes': 55}`
- color_token_counts: `{'black': 320, 'blue': 8, 'brown': 7, 'gray': 43, 'green': 115, 'magenta': 18, 'orange': 44, 'red': 232, 'white': 268, 'yellow': 78}`

Consumer rule: the backend resolves shape family, color tokens, pattern
tokens, style version, and palette version. Browser and proof UI code may
display these fields and images, but must not derive colors, patterns, or
fallback recipes from filenames or JavaScript heuristics.

Known unresolved recipe states stay visible as `manual_exception_required`,
`shape_family_missing`, or `recipe_missing` and remain blocked for runtime
promotion until later gates approve them.
