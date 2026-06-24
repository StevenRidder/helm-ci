# ADR-0007 — The spacetime probe: every layer is part of the narratable slice

- **Status:** Accepted
- **Date:** 2026-06-24

## Context

We had described data fusion only per-domain: the *weather* field
([WEATHER-ROUTING.md §1](../WEATHER-ROUTING.md), `W(lat,lon,t)`) and the *destination* dossier
([BRIEFINGS.md](../BRIEFINGS.md)). In practice the data lives as discrete visual layers
(MapLibre + the S-52 engine) and discrete backend tools. Steve's framing generalized it:
*"I want any layer to be part of that space/time slice"* — pick a point in space and time and
have the agent narrate the weather, climate, community/NFL data, depth, etc., all at once.

A first cut already exists in code ([backend/context.py](../backend/context.py)
`resolve_context` + `/context` + `/narrate`, narrated by
[backend/agents.py](../backend/agents.py) `narrate_context`), but the primitive was unnamed
and the architectural rule unstated.

## Decision

Adopt the **spacetime probe** as a core architectural primitive, and make this binding:

1. **Any layer is part of the space/time slice.** Every Helm layer has two faces — a *visual*
   face (how it draws) and a *probe* face: a uniform `sample(lat, lon, t)` contract returning
   `{ value, source, sourceRef, freshness, confidence, horizon?, locked? }`. **A layer is not
   done until it can be sampled.** If it can be drawn, it can be sliced; if it can be sliced,
   it can be narrated.
2. **One resolver, one slice.** A point/path/region + time resolves to a single source-tagged
   **Slice** = the samples of all (enabled) layers there.
3. **Selectable layers double as slice filters.** The toggle that shows/hides a layer also
   includes/excludes it from the slice — the user composes both the view and the narration.
4. **One narrator.** The ReAct agent speaks the slice in plain language. Deterministic facts
   are computed; the agent only sequences and narrates them.
5. **Honesty is structural.** Never invent a value; cite source + freshness on every clause;
   carry forecast horizon/confidence; keep walled layers (NFL) *locked and named as locked*;
   satellite/SDB stay supplemental; degrade offline and say so.
6. **Query modes are geometries of one primitive.** Point, point+time, path `P(t)`
   (passage briefing / route-weather), destination (dossier), and region (where-to-go) are all
   resolve→narrate over the same slice.

Full spec: [SPACETIME-PROBE.md](../SPACETIME-PROBE.md).

## Consequences

- **The slice is the single substrate** under narration, briefings, the dossier, where-to-go,
  and "explain this" — they stop being separate engines.
- **New layers must implement the probe contract** (incl. plugins) to be narratable — a clear,
  enforceable bar.
- Inherits and centralizes the project's honesty posture (cite/date/confidence, walled-source
  gating, supplemental imagery, offline-awareness).
- Some layers are **stubbed/TODO** for the probe face today (depth-at-point, tides/currents,
  AIS, full weather catalog, real climatology) even where they already draw — tracked in
  [SPACETIME-PROBE.md §7](../SPACETIME-PROBE.md).
- NFL remains a **locked slot** in the slice ([ADR-0005](0005-community-places-overlay.md)).

## Related

- Spec: [SPACETIME-PROBE.md](../SPACETIME-PROBE.md)
- Weather field: [WEATHER-ROUTING.md §1](../WEATHER-ROUTING.md)
- Destination/path fusion: [BRIEFINGS.md](../BRIEFINGS.md), [ADR-0006](0006-destination-dossier-and-briefings.md)
- Code: [backend/context.py](../backend/context.py), [backend/agents.py](../backend/agents.py)
