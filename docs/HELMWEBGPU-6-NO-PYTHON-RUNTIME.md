# HELMWEBGPU-6 No-Python Renderer Runtime Proof

`HELMWEBGPU-6` ties the Vulkan/OpenCPN native proof, Helm WebGPU browser
artifacts, and the HELMC++ runtime policy into one checked guardrail.

## Boundary

The shipped stack keeps three runtime roles separate:

| Surface | Runtime role | Python status |
| --- | --- | --- |
| `helm-server`, `helm-packd`, `helm-envd` | Boat-side chart, pack, and environmental source services | C++ required runtime; no Python daemon |
| `web/chart-artifact-webgpu.js` and `web/wx-field-texture-artifact.js` | Browser JavaScript/WebGPU artifact consumers | No Python runtime |
| OpenCPN/VSG proof paths | Native C++/CMake renderer proof artifacts | No Python runtime |
| `scripts/wx_pack_factory.py`, `scripts/wx_bake_openmeteo.py`, pipeline tests | Tooling, reference/oracle, offline bake, fixtures | Allowed outside required runtime |

This does not mean every helper script is C++. It means no renderer or artifact
launch path that Helm/OpenCPN must run for the product requires Python,
`uvicorn`, FastAPI, Docker, or a virtual environment.

## Checked Inventory

The machine-readable inventory is
[`helmwebgpu-render-runtime-inventory.json`](helmwebgpu-render-runtime-inventory.json).
It covers:

- browser chart artifact consumer: `helm.render.artifact.v1`;
- browser environmental field texture artifact:
  `helm.env.fieldTexture.artifact.v1`;
- C++ source services that feed those artifacts: `helm-server`, `helm-packd`,
  and `helm-envd`;
- native OpenCPN/VSG proof artifacts and the Helm headless adapter boundary;
- Python tooling/reference paths that remain explicitly outside runtime.

Validate it with:

```bash
node scripts/check-helmwebgpu-runtime-artifacts.mjs
node scripts/check-helmwebgpu-runtime-artifacts.mjs --negative-smoke-python-runtime
```

The guard also cross-checks
[`runtime-inventory.json`](runtime-inventory.json) so the HELMWEBGPU proof cannot
drift away from HELMC++: `helm-server`, `helm-packd`, and `helm-envd-target`
must stay classified as C++ required-runtime entries that do not allow Python.

## Runtime Evidence

The existing HELMC++ runtime harness remains the end-to-end proof for launched
boat services:

```bash
HELM_SERVER_BIN=/path/to/helm-server \
HELM_PACKD_BIN=/path/to/helm-packd \
HELM_BASEMAP_CACHE_BIN=/path/to/helm-basemap-cache \
HELM_ENVD_BIN=/path/to/helm-envd \
scripts/helmcxx-no-python-runtime.sh
```

That harness launches the required C++ services directly on private ports,
probes chart/catalog/nav/pack/environment contracts, and inspects each process
tree for Python/FastAPI/uvicorn daemons.

For HELMWEBGPU-specific static evidence, the guard proves:

- HELMWEBGPU-5 artifacts declare no Python runtime dependency and are browser
  JS/WebGPU consumers;
- the boat-side artifact source services map back to HELMC++ C++ runtime
  inventory entries;
- the OpenCPN/VSG proof path is C++/CMake-shaped and not a Helm browser
  architecture dependency;
- Python remains named as tooling/reference/fixture/offline-bake only.

## CI

The HELMC++ runtime guard workflow runs the HELMWEBGPU guard on changes to this
inventory, the checker, the HELMWEBGPU-5/6 docs, runtime inventory, or WebGPU
artifact modules. This catches accidental promotion of a Python path into the
renderer/artifact runtime before review.
