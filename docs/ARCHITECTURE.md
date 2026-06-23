# Architecture

> Distilled from the architecture agent + adversarial feasibility review. Decisions are
> tracked as ADRs in [decisions/](decisions/).

## Shape

```
┌──────────────────────────────────────────────────────────────┐
│  Native Apple front-ends  (not a port, not a cross-UI toolkit) │
│   macOS  SwiftUI + AppKit   │  iPad  SwiftUI+Metal │ iPhone …   │
└───────────────┬──────────────────────────────────────────────┘
                │  (thin platform glue)
┌───────────────▼──────────────────────────────────────────────┐
│  Shared C++ nav core  (one codebase, all three targets)        │
│   chart access + quilting + chart groups                       │
│   S-57/S-52/CM93 ENC engine  (contained GPL OR GDAL rebuild)   │
│   GRIB 1/2 parse + weather rendering                           │
│   isochrone router + polar handling                            │
│   AIS + CPA/TCPA + guard zones + SART + MOB                    │
│   tides/currents harmonics                                     │
│   SignalK / NMEA0183 connection manager + normalization        │
│   GPX / ENC / mbtiles / polar / GRIB I/O                       │
└───────────────┬──────────────────────────────────────────────┘
                │
┌───────────────▼──────────────┐   ┌──────────────────────────┐
│  Hybrid renderer (Metal)      │   │  On-demand tiler          │
│   MapLibre Native:            │   │  (server / edge, NOT       │
│     raster · satellite ·      │   │   on-device)               │
│     weather · quilted mbtiles │   │  bbox → tiles → mbtiles    │
│   + S-52 ENC engine           │   │  see CHART-PIPELINE.md     │
│     composited on top         │   └──────────────────────────┘
└──────────────────────────────┘
```

## Why this stack

**Shared C++ core + native Apple UIs** — not a UI toolkit, not a port.

- **Rejected: fork OpenCPN / wxWidgets.** Desktop mouse toolkit; no iOS path; drags 20
  years of legacy onto a touchscreen.
- **Rejected: React Native.** JS-bridge overhead is wrong for a 60fps chart canvas.
- **Rejected: Flutter.** Non-native widgets undercut the "native macOS" goal and still
  need C++ FFI for the engine.
- **Acceptable fallback only: Qt** — C++-native but desktop-first ergonomics on iOS.
- **Chosen:** the platform-agnostic engine is C++ (chart math, GRIB, routing, AIS,
  S-52); each OS gets a native front-end (SwiftUI/AppKit on macOS, SwiftUI+Metal on
  iOS/iPadOS). This is how Aqua Map / qtVlm proved native iOS chartplotters work.

## The two-renderer design (load-bearing)

**MapLibre Native cannot render S-52.** It uses the Mapbox Style Spec and has no concept
of IHO symbology, safety contours, or Day/Dusk/Night palettes. So:

- **MapLibre Native (Metal)** handles everything raster: satellite, NOAA raster (NCDS),
  quilted mbtiles, and the weather heatmap/particle layers.
- **A dedicated S-52/S-57 engine** renders true vector ENC and is composited on top.

NOAA **NCDS raster mbtiles** let Phase 1 ship real charts *before* the S-52 engine
exists; live S-52 rendering is deferred to Phase 2.

## Connectivity (network-first on iOS)

iOS has **no serial/USB** for NMEA. Boat data is ingested over the network:

- **SignalK** (WebSocket) — primary.
- **NMEA 0183 over TCP/UDP** (port 10110) — fallback.
- **BLE** — handheld GPS.
- **Internal GPS** — phone/tablet.
- **Autopilot output** goes over the network on iOS.
- **Serial/USB** — macOS only.

Proven by Aqua Map, NMEAremote, qtVlm.

## The GPL boundary (critical)

OpenCPN is **GPLv2-or-later**. You cannot statically link GPL source into a closed
App Store binary (GPL is non-transferable vs. App Store terms — the "VLC problem").

Two compliant options for the ENC engine, gated on IP counsel:

1. **Arm's-length contained GPL component** behind a stable interface (firewalls the
   copyleft), or
2. **Rebuild S-52 on permissive GDAL/OGR + PROJ + a custom symbology layer** (clean IP).

Because the posture is "open now, maybe sell later," option 2 is favored — it keeps the
core relicensable. See [ADR-0002](decisions/0002-enc-engine.md) and
[ADR-0003](decisions/0003-license-posture.md). **No OpenCPN code in the core until
counsel signs off.**

## Offline-first / sync

- Charts and GRIB cache to device permanently once downloaded.
- Optional route/waypoint cloud sync (CloudKit or own backend) — but **imported
  PredictWind routes/GRIB are excluded** from any sync/share path (license-bound;
  device-local only). See [LEGAL](LEGAL.md).
