# Mockups

Hand-authored UI for Helm. Each file is a self-contained HTML document — open in any
browser. Toggle **Day / Dusk / Night** (top-right on desktop/iPad, the sun button on
iPhone) to see the three real S-52 chart schemes.

## Canonical UI (pixel-perfect set) — the reference design

The shipped look, the same chart scene (Baie de Cook, Moorea) re-laid-out per device:

| File | Screen |
|---|---|
| [macos.html](macos.html) | **macOS** — full-bleed chart, floating glass toolbar / rail / route inspector / instrument bar, zoom + compass. |
| [ipad.html](ipad.html) | **iPadOS** — landscape, touch targets, floating toolbar, status bar + home indicator. |
| [iphone.html](iphone.html) | **iOS** — portrait, underway: dynamic island, glance card, route bottom-sheet, tab bar. |

These three are the **canonical visual reference** for the product: palette, typography,
chart conventions (depth shading, contours, soundings, buoys `R "4"`/`G "3"`, lit beacon
with `Fl(2) 10s` + light sector, marina/anchorage symbols, current arrow, wind barbs), the
own-ship heading/COG vectors, the magenta route with per-leg labels, the mint PredictWind
route, AIS with CPA highlight, and the source-attribution line.

> Fidelity note: in the shipped app the chart is rendered live by the S-52 engine from real
> ENC data. These files are a faithful hand-built representation of that output at one
> moment, not the live renderer.

## Earlier explorations

| File | Notes |
|---|---|
| [macos-weather-overlay.html](macos-weather-overlay.html) | First hero — emphasizes the composited weather-layer catalog over a stylized chart. Kept for the layers/weather-panel detail. |
