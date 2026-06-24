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

## Feature wireframes

| File | Screen |
|---|---|
| [destination-dossier.html](destination-dossier.html) | **Destination dossier + living timeline** — the "once I get there" briefing (arrival weather, formalities, anchorage, services, community reports, climate) beside the "along the way" briefing, on a two-axis timeline (valid-time scrubber + issue-time updates). Interactive: drag the timeline to move the boat and watch the arrival forecast firm up; Day/Dusk/Night. See [../BRIEFINGS.md](../BRIEFINGS.md). |
| [nfl-giveback-experimental.html](nfl-giveback-experimental.html) | **Give back + NFL read (experimental) + Where-to-go** — the honest two-direction model: stable, sanctioned give-back (push track→NoForeignLand, contribute→OpenSeaMap, Helm pins) vs. reading NFL data in, gated under an **Experimental Features** group (personal · unofficial · may break). Plus the LLM "Where to go" card that runs on open + owned + RAG, with NFL shown as a *locked enrichment*. See [../integrations/noforeignland.md](../integrations/noforeignland.md). |
| [saved-places-sync.html](saved-places-sync.html) | **Saved places — pin on phone, POI on the plotter** — the cross-device flow: a "Pin to chart" save sheet (category + note + auto-attached source link) → a Saved-places list of collections marked "on chart · synced" → the helm showing pins as a toggleable Saved POI layer with a note/source callout and "Add to route". Research → bookmark → POI → waypoint. See [../BRIEFINGS.md](../BRIEFINGS.md) §3c · [ADR-0006](../decisions/0006-destination-dossier-and-briefings.md). |
| [companion-deepread.html](companion-deepread.html) | **iOS companion — deep read** — the lean-back tier of the dossier: photo hero, an AI briefing with tappable citations, full formalities with **linked source cards** (Noonsite/blogs/Helm, badged open/cited/owned), and an anchorage page with mini-map + real cruiser reviews + "add your report". The quick-notes-at-the-helm / deep-read-on-the-phone split from [ADR-0006](../decisions/0006-destination-dossier-and-briefings.md). |

## Earlier explorations

| File | Notes |
|---|---|
| [macos-weather-overlay.html](macos-weather-overlay.html) | First hero — emphasizes the composited weather-layer catalog over a stylized chart. Kept for the layers/weather-panel detail. |
