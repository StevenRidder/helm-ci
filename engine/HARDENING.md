# Chart-core hardening — turning the spike into a production renderer

The headless S-52 renderer was first proven as a *spike* (extract a slice of OpenCPN's `gui/`,
prop it up with stubs). For a life/death navigation tool that's not good enough. This tracks the
work to make it production-grade — **no hacks, no faked symbols, correct safety features**. Driven by
a file-by-file read of OpenCPN's real source.

## The key finding
OpenCPN **already renders charts to bitmaps headlessly** — `s57chart::BuildThumbnail`
(`gui/src/s57chart.cpp:2982`) renders into a plain `wxMemoryDC` via `DoRenderViewOnDC` →
`ps52plib->RenderAreaToDC` with **no window, no GL context, no ChartCanvas**. So we are not faking a
capability that doesn't exist — the supported render-to-bitmap path is real. The *only* reason the
spike needs ~450 lines of stubs is that `s57chart.cpp` is compiled into the **monolithic `opencpn`
executable**, not a reusable library, so a headless consumer must re-link a slice and satisfy a few
app globals. **Recommendation: Option A — extract a first-class `ocpn::chart-render` static library
(upstream a headless seam)**, rather than running OpenCPN offscreen (Option B).

## Status

| # | Item | Status |
|---|------|--------|
| 1 | **Native-scale → SCAMIN / safety-contour** (SAFETY) | ✅ **done + verified** |
| 2 | **Sever faked `ChartPlugInWrapper` RTTI** (the loader landmine) | ✅ **done + verified** |
| 3 | `HeadlessTopFrame` (~79 no-op virtuals) → structurally dead / real `GetBestVPScale` | ⬜ next (~1 day) |
| 4 | Platform `GetDisplayDPmm()` hardcoded `4.0` → real `BasePlatform::GetDisplayDPmm()` | ⬜ next (~0.5 day) |
| 5 | **ChartDB + quilting** (real multi-cell, not one hardcoded cell) | ⬜ larger (~1.5–3 wk) |
| 6 | Extract `ocpn::chart-render` library; vendor OpenCPN + maintained patches (Option A) | ⬜ larger (~1–2 wk) |

### ✅ 1 — Native-scale / safety-contour fix (the dangerous one)
`s57chart::BuildRAZFromSENCFile()` ingested the SENC but **never copied the decoded native
(compilation) scale back into the chart**, so `GetNativeScale()` returned the constructor default `1`.
The GUI hides this via a separate header-only pass; our headless full-Init path exposed it. With
scale `1`, `s52plib`'s SUPER_SCAMIN test (`chart_ref_scale * 4 = 4`) culls **DEPCNT / DEPARE / SOUNDG**
— i.e. the **safety contour and dangerous soundings silently disappear**.
Fix: copy `sencfile.getSENCReadScale()` into `m_Chart_Scale` (and surface a bad scale loudly — never
render silently at `1`). See [`patches/0001-s57chart-headless-correctness.patch`](patches/).
**Verified:** `GetNativeScale()` now returns the true `1:40000`; previously SCAMIN-culled tiles went
from ~777 B (near-blank) to ~10 KB (full soundings + depth contour) at z13/z15.
*This is a genuine OpenCPN latent bug — the patch is upstreamable.*

### ✅ 2 — Sever the faked RTTI
The spike emitted a **fake `typeinfo for ChartPlugInWrapper`** (`chart_typeinfo.cpp`) so a
`dynamic_cast<ChartPlugInWrapper*>` would link — a same-named stand-in class whose layout differs from
the real one: a latent crash if ever actually dereferenced. Those casts live only in **light-sector
helpers** that take a `ChartCanvas*` (cursor interaction, never the tile-render path) and only fire for
**plugin charts**, which a headless engine never loads. Fix: guard them out under `OCPN_HEADLESS`
(`target_plugin_chart = NULL`) — structural severance, not a fake — and drop `chart_typeinfo.cpp`.
**Verified:** links with no undefined typeinfo; tiles still render correctly; no `__ZTI18ChartPlugInWrapper`.

## Patches
`patches/` holds the OpenCPN source changes (against the upstream clone). They are deliberately small,
real, and upstreamable — not workarounds. The build still happens against a clone today; **Step 6**
moves this to a vendored OpenCPN + maintained patch series + a real `ocpn::chart-render` library.
