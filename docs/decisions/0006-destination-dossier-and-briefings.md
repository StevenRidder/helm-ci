# ADR-0006 — Destination dossier & living briefings (committed)

- **Status:** Accepted
- **Date:** 2026-06-24

## Context

The single most-requested capability from real passage-making: two briefings —
**"along the way"** (what the passage will be like) and
**"once I get there"** (what landfall will be like) — that **update continuously** instead
of forcing the sailor to re-download GRIB, open many pages, and re-derive everything by
hand. The wireframe ([../mockups/destination-dossier.html](../mockups/destination-dossier.html))
landed it; this ADR commits us to building it. Full spec: [../BRIEFINGS.md](../BRIEFINGS.md).

A key refinement from review: the dossier shown **on the chart / at the helm is "quick
notes"** — glanceable, decision-useful, legible underway. **Deep reading happens on the iOS
companion app**, where there's room for full text, photos, and outbound links to the
original sources. The two tiers are the same data at two depths, not two products.

## Decision

**We are building the destination dossier + living briefings.** Specifically:

1. **Two briefings, one timeline.** "Along the way" (the spacetime weather engine,
   [../WEATHER-ROUTING.md](../WEATHER-ROUTING.md)) and "once I get there" (the destination
   dossier) share a single, continuously-updating timeline with two axes: **valid-time**
   (where the boat is, when) and **issue-time** (how the picture changed as data arrived).
2. **Two depths, one dataset — the quick-notes / companion split.**
   - **At the helm (chartplotter / chart canvas):** terse, glanceable **quick notes** —
     key facts, source + freshness chips, color-coded status. Optimized for a glance
     underway, not for reading.
   - **iOS companion app:** the **deep read** — full briefing text, photos, reviews, and
     **outbound links** to the original sources (Noonsite, blogs, forums, charts). This is
     where you research, dockside or off-watch.
   - The companion may also be where heavier RAG synthesis and link-following live, while
     the helm shows the distilled result.
3. **Honest source tiers (inherits [ADR-0005](0005-community-places-overlay.md)).**
   Built on **open** (OSM/Overpass, OpenSeaMap) + **owned** (Helm pins/reviews) + **cited
   RAG** over public web (Noonsite, blogs, forums — summarize + attribute + link, never
   wholesale republish). **NoForeignLand** push-only / partnership-pull; **SeaPeople** not
   integrable — serve the *need* from allowed sources. Every claim is **sourced, dated, and
   links back** (links surfaced primarily in the companion).
4. **LLM-derived, deterministic-cored.** Briefings are LLM synthesis/narration over
   **computed** facts (position, ETA, arrival weather values, tide/current). The LLM never
   invents a forecast, fee, depth, or review; unknowns are labelled "verify locally," never
   guessed. Guardrails per [../BRIEFINGS.md](../BRIEFINGS.md) §6 and
   [../WEATHER-ROUTING.md](../WEATHER-ROUTING.md) §7.
5. **Continuous & offline-aware.** Background ingestion whenever there's a pipe; **diff,
   don't dump** (surface what changed and whether it matters, silent otherwise); cached
   dossier + smaller on-device model offshore, always explicit about data age.

## Consequences

- A genuinely differentiated, safety-relevant feature that targets the exact pain of ocean
  passage-making — and one incumbents can't easily match because it depends on the fused
  data + the owned-community layer, not a walled garden.
- Requires the **iOS companion app** to carry the deep-read tier (full text, photos, links)
  — a first-class platform role, not an afterthought. The helm surface must stay terse.
- Requires the **owned reviews backend** (from ADR-0005) and a **RAG pipeline** with strict
  citation/attribution/ToS handling — the largest new engineering + legal surface here.
- Inherits the satellite/community honesty posture: "verify locally," never an official
  clearance; respect every source wall.
- **Saved places (cross-device pins).** Research on the companion produces pins that sync to
  the helm as a toggleable POI/bookmark layer, carrying note + source link, promotable to
  waypoints (research → bookmark → POI → waypoint). Owned data, offline-first, private by
  default. Spec: [../BRIEFINGS.md](../BRIEFINGS.md) §3c; wireframe:
  [../mockups/saved-places-sync.html](../mockups/saved-places-sync.html).
- Build order is staged in [../BRIEFINGS.md](../BRIEFINGS.md) §7: open+owned dossier card →
  arrival weather → living timeline → RAG narrative → contribution loop.

## Related

- Spec: [../BRIEFINGS.md](../BRIEFINGS.md)
- Wireframe: [../mockups/destination-dossier.html](../mockups/destination-dossier.html)
- Weather engine: [../WEATHER-ROUTING.md](../WEATHER-ROUTING.md)
- Community data walls: [ADR-0005](0005-community-places-overlay.md),
  [../integrations/noforeignland.md](../integrations/noforeignland.md)
