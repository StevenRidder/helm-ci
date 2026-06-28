# Vulkan Render Fixtures

Status: POC fixture and regression contract for Vulkan board `SEAM-4`

This document defines the first fixture corpus and image-regression harness for
the shared Vulkan renderer seam. It builds on:

- [VULKAN-RENDERER-SEAM.md](VULKAN-RENDERER-SEAM.md)
- [VULKAN-RENDER-COMMAND-STREAM.md](VULKAN-RENDER-COMMAND-STREAM.md)
- [VULKAN-RENDER-ADAPTERS.md](VULKAN-RENDER-ADAPTERS.md)

The goal is to catch semantic drift before pixel drift: command stream hashes
must be stable for a known source/view/display tuple, and image hashes must be
stable for a known backend/target once renderer output exists.

## Corpus Shape

Fixture roots live under:

```text
engine/test/fixtures/vulkan-render/
```

Each fixture directory contains:

```text
chart-1/
  manifest.json          # fixture metadata, capture matrix, expected hashes
  source.json            # redistributable synthetic or source descriptor
  scene.commands.json    # RenderScene command stream fixture
  provenance.json        # source/object/transform/quilt provenance
  expected.ppm           # tiny dependency-free golden image placeholder
```

The fixture checker is a C++ CLI:

```bash
c++ -std=c++11 -O2 -Wall -Wextra \
  engine/vendor/cli/helm_vulkan_fixture_check.cpp \
  -o /tmp/helm-vulkan-fixture-check
/tmp/helm-vulkan-fixture-check --print-hashes
```

The same source is also built by `engine/bootstrap.sh` as the
`helm-vulkan-fixture-check` target, so the checker can run inside the normal
OpenCPN/Helm C++ build without introducing a scripting dependency.

It validates fixture shape, canonical JSON hashes, provenance references,
required command types, and expected image hashes.

## Redistributable Fixture Policy

Committed fixtures must be redistributable:

- repo-owned synthetic fixtures are allowed and should be small;
- public NOAA ENC cells may be referenced by id and downloaded during an
  explicit capture job, but the chart cell itself should not be committed;
- user/private chart packs, S-63 material, oeSENC output, private imagery, and
  generated SENC caches must not be committed.

The first committed fixture is `chart-1`, a synthetic scene that exercises the
schema without carrying any third-party chart data.

The first real ENC capture targets should be downloaded at runtime:

```text
US5FL4CR  Key West sample cell used by scripts/install-sample-enc.sh
US5FL96M  historical headless-render proof cell, if still publicly available
```

Record NOAA source URL, edition/update metadata, and downloaded cell hash in the
fixture manifest, but keep the raw cell outside Git.

## Capture Matrix

Every real capture should name the exact tuple that produced it:

```text
source epoch
render view: projection, bbox/tile, scale denominator, rotation, pixel size
display state: palette, display category, safety depths, text/soundings toggles
backend: command-stream fixture, VSG offscreen, OpenCPN onscreen test target
output format: command JSON, PNG, or debug PPM
```

Minimum matrix for the first real ENC fixture:

| Name | Palette | Display Category | Safety Depth | View |
|---|---|---|---|---|
| day-standard-z12 | day | standard | 10 m | one Key West tile |
| dusk-standard-z12 | dusk | standard | 10 m | same tile |
| night-standard-z12 | night | standard | 10 m | same tile |
| day-all-z13 | day | all | 10 m | detail tile |
| day-standard-safety20 | day | standard | 20 m | same as day-standard-z12 |

The first image baseline may be a small synthetic PPM so the harness is
dependency-free. Renderer-produced PNGs should be added when the VSG/offscreen
backend can replay the fixture.

## Regression Flow

1. Validate manifest and JSON schema shape.
2. Canonicalize `source.json`, `scene.commands.json`, and `provenance.json`.
3. Compare canonical SHA-256 values against `manifest.json`.
4. Validate every command `provenance_refs[]` id exists in `provenance.json`.
5. Validate required command types are present.
6. Compare committed expected image hashes.
7. When a renderer is available, compare generated output hashes against the
   manifest or write an explicit review artifact for human approval.

This lets failures point to the right layer:

- source hash change: fixture input changed;
- command hash change: semantic/conversion/order drift;
- provenance hash change: debug lineage changed;
- image hash change with stable command hash: backend/pixel drift.

## Acceptance For SEAM-4

SEAM-4 is complete when:

- the fixture corpus has a redistributable starter fixture;
- the harness passes in a clean checkout without network access;
- the fixture manifest records command/provenance/image hashes;
- docs identify the first real NOAA ENC capture targets and matrix;
- future renderer work has a concrete command/image regression path.
