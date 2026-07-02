# WX Retirement Inventory (WX-35)

The compact-grid architecture (WX-30…WX-34) replaced the tile/gateway weather stack. This is the
**cleanup gate**: what is removed, what remains and under which label, and what still gates the
final removal. The machine-enforced half of this document is
[`web/tests/wx-retirement-gate.test.js`](../web/tests/wx-retirement-gate.test.js) — CI fails loudly
if a retired entrypoint creeps back.

## Removed by this gate

| What | Was | Why gone |
|---|---|---|
| `web/wx-live.js` | gesture-fetching "Live · fills view" viewport path (fetch-on-pan from the gateway) | Zero call sites since WX-19/WX-30; the definition of the pan/zoom→provider coupling the contract forbids. File deleted; script tag, service-worker precache entry, opacity/disable plumbing and health-panel flag removed. |
| legacy `data/wind.json` particle autoload (`index.html`) | pipeline-fixture VELOCITY JSON loaded on layer select and frame scrub | Fixtures never ship; it 404'd forever (console spam) and raced the Environmental Scene with an empty-but-visible particle engine (the WX-25 verification ghost). The scene (`wx-scene.js startParticles`) owns particle data AND visibility. |
| client viewport-materialize entrypoints (`materializeUrl`, `quantizeViewForMaterialize`) | on-demand view-sized bakes from pan/zoom | Removed by WX-30 (#258); the gate pins them out permanently. The off-edge path is a fail-loud `disabled` plan, never a fetch. |

## Remaining, by label

| Component | Label | Removal gate / C++ target |
|---|---|---|
| `web/wx-scene.js` + `wx-scene-webgpu.js` + `wx-controls.js` (prepared-bundle Environmental Scene) | **shipping bridge** — explicit primary path; fail-loud (WX-30), no silent substitution | Retired by **WX-26** once real grid packs flow end-to-end (needs a live source adapter in the pack factory — `open-meteo` adapter is `implemented: False` today). |
| `services/wx` (Python gateway :8093) | **dev/reference + shipping bridge** for the scene above | **WX-26 / WX-20**: C++ `helm-envd`/`helm-wxd` per [RUNTIME-SERVICES.md](RUNTIME-SERVICES.md); Python stays as oracle. |
| `web/wx-grid-*.js` (pack client, decode, WebGPU grid scene) | **grid path** — the replacement (WX-32/WX-33) | Becomes primary at WX-26; UI swap happens there, not here. |
| `scripts/wx_pack_factory.py`, `scripts/env_grid_pack.py` | **cloud job / packer** (WX-34) | Cloud/VM job; C++ path for productized backend per contract §10. |
| `helm-packd` | **required runtime, C++** (merged) | serves packs by range; owns no weather physics. |
| `web/wind-layer.js` + `wx-particles-webgpu.js` | **shared particle engines** (CPU + WebGPU compute), driven by whichever scene is active | Stay; both scenes feed them the same u/v values. |
| `web/radar.js` (RainViewer nowcast), `web/isobars.js`, `web/wx-grib*.js` + `wx-import.js` (PredictWind/GRIB import) | **explicit, user-invoked features** — radar states its online-only nature; import is device-local | Independent of the grid migration. |
| `pipeline/` value-tile generators | **dev/reference tooling** (demo/ensemble fixtures) | Never a runtime dependency; labeled by [RUNTIME-SERVICES.md](RUNTIME-SERVICES.md). |

## Contract pin added here

`helm.env.grid.v1` chunk headers now carry `grid.origin: "northwest"` (row 0 = north edge, col 0 =
west, band-major). Producers emit it (`env_grid_pack.make_chunk`, used by the pack factory), the
pack verifier and the browser decoder reject any other value (`unsupported_grid_origin`), and absent
means `northwest` (pre-pin v1 packs). See ENVIRONMENTAL-GRID-V1.md §6.

## Still gating WX-26 (final removal)

1. A **live source adapter** in the pack factory (`open-meteo` / GRIB) so real packs exist for the
   boat's region — today only fixture/local sources are implemented (deliberately: no surprise
   network fetches).
2. The **drawer/UI swap** from the prepared-bundle scene to `HelmWxGrid` once real packs flow.
3. C++ `helm-envd`/`helm-wxd` parity (WX-20) before the Python gateway can be deleted.
