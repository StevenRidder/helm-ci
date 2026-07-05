# HELMWEBGPU-5 Field Texture Convergence

`HELMWEBGPU-5` aligns the shipped WX WebGPU scene with the shared Vulkan/WebGPU
field-texture artifact contract without turning Helm into a custom chart
renderer. MapLibre remains the cockpit compositor. WebGPU is used only for the
environmental field overlay and particles.

## Mapping

| WX path | Shared artifact path |
| --- | --- |
| `wx-grid-pack-client.js` fetches a checked `helm.env.grid.v1` manifest and byte ranges. | Artifact `source` keeps `packId`, manifest URL, provider/model, generation time, advisory flags, and no-substitution policy. |
| `wx-grid-decode.js` decodes chunks into physical-value `Float32Array` bands and assembles a tier. | Artifact `field` keeps tier, layer, valid time, bbox, grid geometry, bands, and unit factor. |
| `wx-grid-scene.js` previously packed the assembled tier directly into an ad-hoc `rg32float` upload. | `wx-field-texture-artifact.js` now creates `helm.env.fieldTexture.artifact.v1`; the scene uploads that shared artifact. |
| `wx-grid-scene.js` renders the field into an offscreen canvas source. | Artifact `renderContract` says MapLibre is the compositor, WebGPU is the browser consumer, VSG/native is the compatible consumer, time interpolation is value-before-colour, alpha is premultiplied, and substitution is forbidden. |
| `wind-layer.js` / `wx-particles-webgpu.js` consume the same assembled u/v values for particles. | Vector artifacts declare `particles: same-vector-grid`; particles and colour still share one numeric source. |

## Vertical Slice

The wind field slice is:

1. `helm.env.grid.pack.v1` fixture data from `services/wx/fixtures/helm-env-grid-v1.json`.
2. `HelmWxGridDecode.assembleTier(...)` produces physical-value `u/v` arrays.
3. `HelmWxFieldTextureArtifact.createArtifact(...)` produces a
   `helm.env.fieldTexture.artifact.v1` wind artifact with `rg32float` payload,
   deterministic payload checksum, advisory/source metadata, and no-Python
   runtime classification.
4. `HelmWxGrid` uploads the artifact through
   `HelmWxFieldTextureArtifact.uploadTextureArtifact(...)` and lets MapLibre warp
   the rendered canvas as a raster layer below route/AIS/chart labels.

The node parity test byte-compares the new artifact payload with the previous
WX scene upload layout. Expected diff: zero bytes. Existing WX browser tests
continue to prove zoom/pan stability, fail-loud behavior, and local-only data
loading.

## Runtime Boundaries

- Required boat/runtime path: C++ pack serving and validation (`helm-envd` /
  `helm-packd` direction).
- Browser client path: JavaScript/WebGPU consumer and MapLibre composition.
- Python role: tooling, reference, fixture generation, and tests only.
- No product path may substitute precoloured PNGs, gateway rasters, live
  provider fetches, or placeholders for a missing grid artifact.

## Verification

```bash
node web/tests/wx-field-texture-artifact.test.js
node web/tests/wx-grid-shader.test.js
node web/tests/wx-grid-decode.test.js
npx --prefix web/test playwright test --config web/test/playwright.config.js web/test/e2e/wx33-grid-renderer.spec.js
```
