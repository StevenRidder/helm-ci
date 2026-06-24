# Helm — Living Briefings: "Along the Way" & "Once I Get There"

**Two briefings, both living. One tells you what to expect *en route*; one tells you what
to expect *at the destination*. Neither is a one-shot report — they ingest continuously and
update on a timeline as the picture changes.**

> Status: **Committed** ([ADR-0006](decisions/0006-destination-dossier-and-briefings.md)) ·
> spec v0.2 · 2026-06-24 · Owner: Steve Ridder
> The single most-requested capability, in Steve's words: *"Briefings — what to expect along
> the way, and what to expect once I get there — are my unmet need… It's what you need when
> sailing. We need this!!"* Wireframe:
> [mockups/destination-dossier.html](mockups/destination-dossier.html). Companion to
> [WEATHER-ROUTING.md](WEATHER-ROUTING.md) (the spacetime weather engine), [VISION.md](VISION.md)
> §8 (the copilot), and [integrations/noforeignland.md](integrations/noforeignland.md) (the
> community-data walls).
>
> **Honesty note:** briefings are **LLM-derived synthesis** over data Helm fetches. The LLM
> *summarizes, sequences, and narrates* — it never invents a forecast, a fee, a depth, or a
> review. Every claim is sourced, dated, and links back. Guardrails in §6.

---

## 1. The two briefings

| | **Along the Way** | **Once I Get There** |
|---|---|---|
| Question it answers | "What will the passage be like?" | "What's it like when I arrive?" |
| Primary data | weather + sea-state at the boat's projected position; tropical/climate; hazards | services, formalities, anchorage quality, community reports, climate, arrival weather |
| Engine | the spacetime weather model `W(P(t), t)` ([WEATHER-ROUTING.md](WEATHER-ROUTING.md)) | destination data fusion + RAG over community/blogs/guides |
| Cadence | continuous — re-runs on every new GRIB | continuous — refreshes as you approach + as community/weather data changes |
| View | the route-weather **timeline** | the destination **dossier**, on the same timeline |

They share **one timeline**. Scrub it and *both* update: the en-route weather and the
arrival picture move together, because "what it's like there" depends on *when* you get
there.

> Both briefings are the **spacetime probe** ([SPACETIME-PROBE.md](SPACETIME-PROBE.md) ·
> [ADR-0007](decisions/0007-spacetime-probe.md)) at different geometries: "along the way" is the
> probe along your path `P(t)`; "once I get there" is the probe at a destination + ETA. Any
> layer in the slice is fair game for either briefing.

---

## 2. "Along the Way" — the passage briefing

Already specified in [WEATHER-ROUTING.md](WEATHER-ROUTING.md); summarized here as one half of
the pair. **[LLM]** narration over a **deterministic** core:

> *"You'll motor out of the lagoon into light SE, build to 18–22 kt by Tuesday night, then a
> front Thursday afternoon brings 30 kt on the nose for ~12 h before it eases. Seas peak ~3 m
> @ 11 s. No tropical activity on the route through Friday; the Sunday picture is climatology
> only — low confidence, recheck en route."*

Built from: wind / gust / swell / sea-state sampled along the worldline, the tropical-cyclone
layer, and the climatology tier for the part of the passage beyond forecast skill. Confidence
and horizon are always shown. **[honesty]**

---

## 3. "Once I Get There" — the destination dossier

This is the genuinely new surface. When you set a destination (or click a waypoint/port),
Helm assembles a **living dossier** of what to expect on arrival:

- **Arrival weather & sea-state** — the forecast valid at *your ETA*, plus the approach
  conditions (swell into the pass, wind over the anchorage, tide/current at the entrance).
- **Formalities & check-in** — customs/immigration, fees, flag/quarantine, hours, ports of
  entry. *(This is the [Noonsite](https://www.noonsite.com)-shaped need — the #1 thing
  cruisers research before a new country.)*
- **Anchorage / marina intelligence** — holding, shelter by wind direction, depth, room,
  hazards, mooring availability, "exposed to SW swell."
- **Services & provisioning** — fuel, water, repairs, chandlery, haul-out, groceries,
  laundry, medical, fresh produce, SIM/data.
- **Community reports & sentiment** — recent cruiser experiences: what's current, what
  changed, what to watch. *(The NoForeignLand / SeaPeople / cruiser-blog need.)*
- **Climate & seasonal context** — is it the right season, cyclone risk, typical conditions
  this month.
- **Hazards & local knowledge** — reef passes, bar crossings, surge, theft reports, no-go
  zones.

Rendered as a card on the chart and a section on the timeline, **[LLM]**-written from the
sources in §4, always with citations and "last updated."

---

## 3b. Two depths, one dataset — quick notes at the helm, deep read on the companion

The dossier exists at **two depths of the same data**, matched to where you are and what you
can safely do:

| | **At the helm** (chartplotter / chart canvas) | **iOS companion app** |
|---|---|---|
| Purpose | a **glance** while sailing — decide, don't read | **research** — dockside, off-watch, in the bunk |
| Content | terse **quick notes**: key facts, status, source + freshness chips | full briefing text, **photos**, reviews, and **outbound links** to sources |
| Form | the dossier card + timeline (the wireframe) | scrollable articles, the cited originals (Noonsite/blogs/charts) |
| Reading load | seconds, arm's-length legible | minutes, lean-back |
| Where the heavy work runs | shows the distilled result | can run heavier RAG / link-following |

This is the model Steve named: *"even if the iOS companion app is where you read stuff with
links for more info, and these are more quick notes."* **Same dataset, two presentations —
not two products.** The helm surface must stay terse (a wall of text underway is a failure);
the companion is where depth and links live. Committed in
[ADR-0006](decisions/0006-destination-dossier-and-briefings.md).

## 3c. Pin it — research becomes pins on the plotter (saved places)

The deep-read loop has an **output**: saved places. While researching on the phone, tap
**Pin to chart** on any spot — an anchorage, a snorkeling reef a blog raved about, a
chandlery, a "check the bar at half-tide" hazard. It **syncs to the helm** and shows up as a
POI/bookmark on the plotter, carrying the **note** and the **source link** you saved it from.
Bookmarks you can sail up to. This is the feature Steve named: *"as I read and research, pin
locations from my phone that stick on the Helm plotter — bookmarks that become POIs/waypoints
to check out."*

**Data model — a Saved Place:**
- location (a point, or attached to a known POI), title, **category + icon** (anchorage ·
  snorkel · provisioning · fuel · repair · hazard · must-see · sundowner …),
- a **note** (your words, or the quote you pinned), **source link(s)** auto-attached from the
  deep-read (the Noonsite/blog page), optional photos,
- **status** (to-check · visited · skip), created-on device + time, color.

**Behavior:**
- **Owned · synced · offline-first.** Lives in Helm's backend (the *owned* tier of
  [ADR-0005](decisions/0005-community-places-overlay.md)); syncs **phone ↔ iPad ↔ helm**;
  created offline, queued, flushed on reconnect — same discipline as the NFL push. **Private
  by default**, optionally shared with buddy boats / fleet.
- **Distinct from waypoints — until you want them to be.** Saved places are *aspirational*
  ("go check this out"), rendered as a toggleable **Saved / Bookmarks** POI layer, visually
  distinct from active route waypoints. One tap **promotes** a pin to a waypoint ("Add to
  route" / "Navigate here"). The pipeline: **research → bookmark → POI → waypoint.**
- **Collections.** Group pins into lists ("Fiji must-dos", "Provisioning run", "Before we
  leave") — Google-Maps-"Saved"-style; lists are shareable.

This closes the loop the whole product implies: you **read** on the phone, **pin** what
matters, and it's **waiting on the chart** when you arrive — and every pin is owned community
data that, with permission, enriches the next sailor's dossier. Wireframe:
[mockups/saved-places-sync.html](mockups/saved-places-sync.html).

## 4. Destination data sources — the honest map

The hard truth from [integrations/noforeignland.md](integrations/noforeignland.md) and
[COMPETITIVE.md](COMPETITIVE.md): **the richest community sources are walled.** So the dossier
is built primarily on **open + owned** data, enriched by **RAG over public web** content, and
uses walled sources only where sanctioned.

| Source | Wall | Path in Helm |
|---|---|---|
| **OpenStreetMap / Overpass** | open (ODbL) | primary services/marinas/fuel/docks — already fetched by `pipeline/fetch_places.py` |
| **OpenSeaMap** | open (ODbL) | seamarks, harbours, anchorage marks |
| **Helm user pins + reviews** | **owned** | our backend — the community asset we control; grows into the moat |
| **Noonsite** (port info, formalities) | website, no open API | **RAG**: retrieve + summarize + **cite/link**, never wholesale republish; honor ToS |
| **Cruiser blogs / forums / guides** | public web | **RAG** with attribution + links (deep-research style synthesis) |
| **Climate / pilot charts / tropical** | open (NOAA/COGOW/NHC/JTWC) | the climatology + tropical tiers from [WEATHER-ROUTING.md](WEATHER-ROUTING.md) |
| **NoForeignLand** | semi-walled (no read API) | **push** official; **pull** only via partnership, or personal-experimental flag — never scraped in a shipped product |
| **SeaPeople** | walled (no public API) | **not integrable** — capture the *need*, serve it from open+owned+RAG instead |
| **ActiveCaptain / Navily** (anchorage DBs) | walled (Garmin / partnership) | partnership only; the gold-standard card design is the thing to *emulate*, not scrape |

**[honesty]** The destination briefing must be excellent **without** NFL/SeaPeople, because
we can't legally depend on them. The strategy: open data for the map, **Helm-owned reviews**
for the community layer (so it becomes *ours* over time), Noonsite/blogs via cited RAG for
the narrative, and walled DBs only via partnership. SeaPeople's data is off the table; we
serve the same *need* — "what do other cruisers say about here" — from sources we're allowed
to use.

---

## 5. The living timeline — continuous downloads, continuous updates

The defining property: **briefings are not generated once.** They are living documents on a
timeline. There are **two time axes**, and both matter:

```
  VALID-TIME  ───────────────────────────────────►  (the passage: where the boat is, when)
   now ──── Tue ──── Wed ──── Thu(front) ──── Fri ──── arrival
            │
  ISSUE-TIME (revisions) ──────────────────────────►  (how the picture changed as data arrived)
   GFS 06z  →  ECMWF 12z  →  new community report  →  updated formalities
```

- **Scrub valid-time:** the boat ghost + weather + arrival dossier all move (§1).
- **Track issue-time:** see how successive downloads changed the story — *"yesterday's run had
  you clearing the front; the 12z shifted it 6 h earlier."* This is what turns the
  Maupiti→Fiji misery (re-download, re-read everything, re-derive) into **"here's what
  changed and whether you should care."**
- **Continuous ingestion in the background:** new GRIB, new community reports, updated
  formalities, fresh blog posts — fetched whenever there's a pipe (wifi at anchor, sat link
  offshore), queued and flushed on reconnect.
- **Diff, don't dump. [LLM]** Each update produces a short *delta*, not a fresh wall of data:
  > *"Update: ECMWF agrees with GFS on the Thursday front now (was diverging). Destination —
  > a cruiser reported the fuel dock at Savusavu is back open as of yesterday."*
- **Silent unless it matters:** most updates change nothing material → no interruption. The
  one that changes your departure or your landfall earns a notification.

The timeline is the same control that drives [WEATHER-ROUTING.md](WEATHER-ROUTING.md)'s
scrubber — briefings, weather, and route are three views of one continuously-updating model.

---

## 6. LLM / RAG architecture & guardrails

Briefings are the flagship **LLM-derived** feature; Steve has already named that this is
expected. **Default to the latest Claude models** for cloud-side synthesis; the structured
nav/weather + retrieved community text are an ideal tool-use + RAG substrate.

**How it's built:**
- **Deterministic facts first** — position, ETA, arrival weather values, tide/current,
  distances are computed; the LLM narrates them.
- **RAG for the narrative** — retrieve Noonsite/blog/forum/own-review text for the
  destination, ground the summary in it, **cite + link every claim** (the deep-research
  pattern).
- **Two-axis state** — the model is fed both the current data and the *delta* since last
  issue, so it can write "what changed" not just "what is."

**The guardrails (non-negotiable):**
1. **Never invent.** No fabricated fees, depths, formalities, reviews, or forecasts. If a
   fact isn't in a source, the briefing says "unknown / verify locally," never a guess.
   **[honesty]**
2. **Cite, date, link.** Every destination claim shows its source and age. "Fuel dock open"
   is worthless without "reported 3 days ago by ⟨source⟩." **[honesty]**
3. **Respect the walls.** Noonsite/blogs: summarize + attribute + link, don't republish
   wholesale; honor ToS. NFL: partnership/personal only. SeaPeople: not used. **[honesty]**
4. **Owned > scraped.** Prefer Helm's own pins/reviews; they're legal, fresh, and compound
   into the moat. Encourage contribution (a review you write enriches the next sailor's
   dossier).
5. **Advise, don't act.** Briefings inform; they never auto-change a route or clear you into
   a country.
6. **Offline-aware, and says so.** Full RAG dockside; cached dossier + smaller on-device model
   offshore. Always explicit about freshness — a 5-day-old destination dossier must *say* it's
   5 days old.

---

## 7. Build order

1. **Destination dossier card** from open+owned data (OSM/OpenSeaMap/Helm pins) — the
   ActiveCaptain/Navily-grade card, ours, legal, offline. *(Extends `fetch_places.py`.)*
2. **Arrival weather** — bind the destination to its ETA forecast (reuse the spacetime
   engine).
3. **The living timeline** — continuous background ingestion + valid-time/issue-time scrub +
   diff notifications.
4. **RAG narrative** — Noonsite/blog/forum synthesis with citations, plus the [LLM] passage +
   destination briefings.
5. **Community contribution loop** — Helm pins/reviews write-back; NFL push; partnership
   outreach for NFL/ActiveCaptain pull if/when commercial.

---

*The need is precise: tell me what the passage will be like, tell me what landfall will be
like, and keep both current without me downloading and re-reading everything. The weather
half is the spacetime engine; the landfall half is open+owned data plus cited RAG over the
cruiser web; and the magic is that both live on one continuously-updating timeline that only
interrupts you when the story actually changes.*
