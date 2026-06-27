# Cruisers Forum - OpenCPN Channel Post Draft

Plain text on purpose: Cruisers Forum runs vBulletin, so keep the posted
version simple. This draft is deliberately less legalistic than the repo docs.

---

Title: Alpha: headless OpenCPN core with a modern browser chartplotter client

Hey everyone,

I have been building an alpha chartplotter UI around a headless OpenCPN-based
boat server, and I would love technical feedback from people who know OpenCPN
well.

This is not a replacement for OpenCPN, and I am not asking upstream to take a
giant UI rewrite. The idea is separate: keep OpenCPN's battle-tested navigation
core and S-52/S-57 rendering on the boat, running headless, then serve a modern
browser/touch client over the local network.

What is working in my alpha:

- one-origin boat server for the UI, nav stream, and chart tiles
- live nav stream over WebSocket
- S-52 chart tiles over HTTP into a MapLibre browser client
- AIS targets and CPA/TCPA data
- route create/save/activate using OpenCPN navobj persistence
- track recording
- NMEA 0183 over TCP/UDP and SignalK input, tested against my Vesper Cortex
- weather, places, and community-style layers in the web client

The architecture is:

- Engine on the boat: OpenCPN model/ + chart rendering, headless, GPL, offline,
  owns nav, AIS, routes, tracks, alarms, and chart tiles.
- Browser/mobile clients: thin UI over HTTP/WebSocket. No OpenCPN code in the
  browser.
- Auxiliary services: weather, places, dossiers, sync, and future cloud
  features around the safety core. If those services are offline, navigation is
  still local.

The bit I am most excited about is the fused screen: official chart data,
satellite-style context, weather, AIS, routes, and instruments in one browser UI
instead of bouncing between several apps.

The OpenCPN-derived engine work will stay GPL and visible as a separate
fork/patch series. I am keeping the browser/backend code separate and
source-available so it can be inspected, self-hosted, and tested while still
leaving room for a future hosted cloud service if this turns into something
larger. I am not trying to make the licensing debate the headline here; I just
want the boundary to be clear and respectful.

This is alpha software. It is not a primary-navigation recommendation, not
type-approved ECDIS, and I am still cross-checking everything against stock
OpenCPN, official charts, instruments, and normal seamanship.

What I would most like feedback on:

- whether the headless model/ + renderer approach seems useful to OpenCPN users
- what parts of the headless patch series might be worth upstreaming as small,
  general-purpose seams
- whether the browser-client architecture feels useful on a real boat
- what would make this interesting, unacceptable, or worth testing for OpenCPN
  power users

Happy to share screenshots/video and architecture notes first, then code once
the public license/attribution cleanup is squared away.
