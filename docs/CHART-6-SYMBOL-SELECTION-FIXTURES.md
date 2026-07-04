# CHART-6 Symbol Selection Fixtures

CHART-6 defines the renderer fixture contract for selecting symbols from
normalized chart semantics rather than witness pixels, filenames, or raw color
appearance.

Primary fixture:

- `engine/test/fixtures/symbol-selection/fixtures.json`
- `engine/test/fixtures/vulkan-render/symbol-selection/`

Validation smoke:

```sh
engine/test-symbol-selection-fixtures.sh
```

The smoke loads:

- `pipeline/iconforge/catalog/runtime_evidence_snapshot.json`
- `pipeline/iconforge/proof/manifest.json`

It then checks the fixture cases against the CHART-5 C++ loader by
`symbol_id + normalized_object_class`.

Coverage:

- Direct S-101 asset: `ACHARE02`
- Attribute-driven buoy case: `BOYPIL60` as `BOYLAT`, with
  `buoyShape=pillar`, `colour=red`, and `colourPattern=solid`
- Rule-derived equivalent: `TOPSHQ28`
- Catalogue-rule-backed row: `BCNGEN76`
- Documented deviation: `ACHPNT01`
- Non-S-101 runtime overlay: `AISDEF01`
- Extension/profile-required row: `BORDER01`

Current runtime posture:

- All fixture rows remain `runtime_blocked`.
- `default_render_allowed` is false for every fixture.
- The default render lookup returns no fixture rows until approval and runtime
  gates explicitly promote them.

This task does not alter icon artwork. It gives CHART-7 and later renderer
checks a stable input set for proving object/attribute-driven symbol selection,
day/dusk/night palette expectation, and fail-closed runtime behavior.

The `vulkan-render/symbol-selection` fixture is a synthetic command-stream
wrapper with seven `place_symbol` commands. It exists so CHART-7 can render the
same cases through the Vulkan/VSG smoke path without inventing new fixture
selection semantics.
