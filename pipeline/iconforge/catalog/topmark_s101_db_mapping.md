# S-101 Topmark DB Mapping

- Row-level mappings: 284
- Asset-level mappings: 155
- Shape-safe row mappings: 190
- Shape-safe asset overlays: 129
- Source rule: PortrayalCatalog/Rules/TOPMAR02.lua
- Source URL: https://github.com/iho-ohi/S-101_Portrayal-Catalogue/blob/main/PortrayalCatalog/Rules/TOPMAR02.lua

## Row Status
- context_required: 81
- default_witness_not_shape_safe: 5
- mapped_shape_witness: 190
- missing_shape_code: 8

## Asset Status
- context_required: 13
- default_witness_not_shape_safe: 3
- manual_review_ambiguous_asset: 7
- missing_shape_code: 3
- unambiguous_shape_witness: 129

## Notes
- `TMARDEF1` and `TMARDEF2` are recorded as S-101 rule outputs but are not shape-safe drawing witnesses.
- Asset-level overlays are only emitted when the row-level evidence has one unambiguous shape-safe S-101 witness.
