# Helm — LABS (experimental features)

> Status: spec v1 · 2026-06-26 · Owner: Steve Ridder
> Source: pro-maritime survey (S-100 layered charts, Furuno-style AR nav, AI lookout / machine
> vision, dynamic under-keel clearance, military Additional Military Layers).
> Companion: **[BUSINESS-MODEL.md §10](BUSINESS-MODEL.md)** — these are the layer marketplace's
> hero exhibits — plus [VISION.md](VISION.md), [COMPETITIVE.md](COMPETITIVE.md),
> [LEGAL.md](LEGAL.md), [FEATURE-TRACKER.md](FEATURE-TRACKER.md).

---

## 1. What "Labs" is

`LABS` is a flag-gated, **advisory-only** surface for experimental navigation features that ride
the existing **lazy-isolated Lab loader** (`OFFLINE-2`). They are *not* part of the trusted
nav core. Each Lab is a proving ground: it graduates into a real workstream — or becomes a
sellable marketplace layer — only after it is boat-tested and its guardrails are verified.

**The through-line.** Nearly every advanced feature in the professional maritime world is the
same shape: *fusion + a new layer*. That is exactly Helm's thesis and exactly the layer
marketplace ([BUSINESS-MODEL.md §10](BUSINESS-MODEL.md)). The pro standard **S-100** (IMO-enabled
from 2026) reframes the chart as a layered data canvas — an S-101 base ENC plus plug-in product
specs (S-102 bathymetry, S-104 water levels, S-111 currents, S-124 nav warnings, S-129
under-keel clearance). The big players are spending millions to arrive where Helm's architecture
already points. LABS is where we prove the cruiser-grade version of each.

---

## 2. Ownership (collision boundary)

Per [CLAUDE.md] / [EPICS.md](EPICS.md), each epic owns its files so parallel agents don't fight.
**LABS owns an isolated namespace:**

- `web/labs/**` — all Lab UI, layers, and views (mounted only via the lazy-isolated Lab loader)
- `backend/labs/**` — Lab-only services (UKC model, CV-inference adapter, layer-exchange)
- `docs/LABS.md` — this spec

**Hard rule:** a Lab consumes the core only through existing seams (the nav stream, the alarm
schema `CONTRACT-10`, the layer/probe contract `AI-5`/`AI-17`, source-tagging `ENGINE-7`, the
`SHELL` registration hooks). A Lab **must not edit another epic's files.** If a Lab needs a core
change, it files a task against that core epic and depends on it — it does not reach in.

---

## 3. Shared guardrail (non-negotiable — applies to every LABS task)

> Every Labs feature is **supplemental, never authoritative**; **source-tagged and
> confidence-labelled** (`ENGINE-7`, `TOOLS-6`); **never suppresses or overrides** an
> authoritative feed (real AIS / radar / official ENC); is **advise-don't-act** (`AI-13`); and
> is **off by default** behind the Labs flag. Any Lab that computes a safety margin (clearance,
> collision risk) must render its inputs, their freshness, and an explicit "verify locally"
> disclaimer. This is a safety-of-life domain; a Lab that cannot honor this contract does not
> ship.

---

## 4. Tasks

### LABS-1 · Labs framework & advisory guardrail `[BLOCKING]`

**Summary.** The flag-gated Labs surface and the enforcement of §3 for every Lab.

**What it does.** A single "Labs" toggle (per-feature enable/disable) that mounts Lab layers/views
through the lazy-isolated Lab loader (`OFFLINE-2`). Provides a reusable wrapper that stamps every
Lab layer with a supplemental badge + source/confidence chip, and a shared disclaimer affordance.

**Why.** Quarantines unproven nav features from the trusted core, and is the exact gate the
marketplace later reuses for "unverified third-party layer."

**Approach.** `web/labs/loader.js` (registration + flag state, persisted once `TOOLS-7` exists;
until then, session flag) and `web/labs/guardrail.js` (badge/disclaimer/source-chip wrapper).
Registers into the shell via `SHELL-1`/`SHELL-3` hooks.

**Deps:** `OFFLINE-2`, `AI-13`, `ENGINE-7`, `SHELL-1`, `SHELL-3`.
**Effort:** S. **Status:** Not Started (blocks all other LABS tasks).

**Acceptance:** a dummy Lab layer can be toggled on/off; while on it shows the supplemental badge
+ source chip; with the Labs flag off, no Lab code path runs or renders.

---

### LABS-2 · Reef & Bar Pass Advisor — cruiser-grade dynamic under-keel clearance `[FLAGSHIP]`

**Summary.** Tells a cruiser the best confidence-banded window to transit a reef pass or
river/harbour bar, and the predicted clearance margin, by fusing charted depth + the `TIDES-5`
Pass Condition Estimator + swell + the boat's draft.

**What it does (UX).** User taps a pass/bar (or a point on the active route). Helm shows a
**tide-window timeline** of predicted under-keel clearance for the next N hours — green/amber/red
— with a plain-language readout: *"Best predicted window 09:40–12:10; minimum clearance 0.6 m at
11:05; verify visually."* Along an active route, render a **clearance corridor** (green/amber/red
shading per leg).

**Why.** This is the pros' Dynamic Under-Keel Clearance (OMC DUKC), shrunk to the cruiser's real
fear: putting a keel on coral in a swell-loaded pass. No competitor ships it for recreational
craft; it is pure fusion of data Helm already has; it is native to where Steve actually sails
(Fiji reef passes).

**Inputs.**
- *Have:* charted depth (`CHART-7` depth-on-satellite + S-57 `SOUNDG`/`DEPARE`/`DEPCNT`); swell
  Hs + period and wind-wave (`WX` / Open-Meteo); boat draft (`BOAT-1`).
- *Need:* pass condition sample (`TIDES-5`) including tide-height prediction (`TIDES-2`), predicted
  vs observed current (`TIDES-3`), nearest-station distance, datum, local slack delay, wind/wave
  lagoon-fill residual, and confidence; pass geometry/orientation (from chart or a short user-drawn
  segment); chart-datum handling (soundings are to LAT / chart datum).

**Model (v1 — deliberately simple and honest; refine after boat-testing):**
```
available_depth(t) = charted_depth(to chart datum/LAT) + tide_height(t)
required_depth     = static_draft + safety_margin + dynamic_allowance
dynamic_allowance  ≈ swell_factor · Hs        (heave/pitch in the pass; dominant term)
                   + squat(speed)             (minor below ~8 kn, but included)
clearance(t)       = available_depth(t) − required_depth
confidence(t)      = min(tide/source confidence, pass-model confidence, chart-depth confidence)
→ flag time windows where clearance(t) ≥ user threshold, with green/amber/red + confidence band
```
`safety_margin`, `swell_factor`, and the speed used for squat are user-tunable (boat profile).

**Split.** The math is **deterministic, offline, and unit-tested** in `backend/labs/ukc.py` (or
engine-side if it must run with no backend) — never LLM-derived. It consumes the `TIDES-5` pass
condition result instead of raw tide height. The copilot may only *narrate* the already-computed
result (advisory). Rendering (timeline + corridor) in `web/labs/`. Extends the existing `ALARM-8`
safety-contour check rather than duplicating it.

**Deps:** `LABS-1`, `BOAT-1`, `TIDES-2`, `TIDES-5`, `WX-1`, `CHART-5`, `CHART-7`, `ROUTE-2`,
`ALARM-8`.
**Effort:** M–L. **Status:** Not Started.

**Specific guardrail.** Charted depths in remote reefs and satellite-derived bathymetry are
**unreliable**; show the source + a confidence band per the honesty rules; present a hard
"verify locally / eyeball pilotage" disclaimer. This is a planning aid, **never** a clearance
authority.

**Acceptance:** given a draft, a tide curve, a pass-condition confidence sample, a swell forecast,
and charted depth for a known pass, the advisor produces a green/amber/red window timeline whose
worst-case clearance matches a hand-computed value; sources + confidence + "verify visually / Plan B"
warning are always visible; works offline.

---

### LABS-3 · Camera-as-a-Layer AI Lookout (machine-vision collision aid)

**Summary.** An optional forward camera whose computer-vision detections are fused with the
existing AIS/CPA pipeline to flag hazards that carry no AIS — small craft, fishing floats,
containers, an unlit boat at night.

**What it does (UX).** Camera-detected targets appear as bearing/range marks on the chart and in
the AR view (`LABS-4`), fed into the existing CPA risk + alarm. Plain-language alert: *"Unlit
vessel, ~200 m, fine on the starboard bow."*

**Why.** Sees what AIS misses; SEA.AI and Orca AI prove the recreational market (≈70% fewer false
alarms vs radar+AIS alone). Crucially, shipping the **detector as a Lab layer/plugin** makes it
the marketplace's hero exhibit and exercises the probe/SDK contract end-to-end.

**Architecture.** camera source (USB / RTSP / phone `getUserMedia`) → detector (YOLO-class model;
on-device WASM or Core ML, or backend GPU) → detections normalized to `{bearing, est_range,
class, confidence}` → fused in the engine alarm pipeline alongside AIS targets → rendered. The
detector conforms to the layer/probe contract (`AI-5`/`AI-17`) so third parties can supply one.

**Inputs.**
- *Have:* AIS + CPA/TCPA (`ENGINE-4`), alarm schema (`CONTRACT-10`), guardrails (`AI-13`),
  offline-AI mode (`AI-14`).
- *Need:* camera-ingest driver (extend `CONN`); a vision model + monocular range estimation
  (the hard part); AR projection (shared with `LABS-4`).

**Split.** Inference in `backend/labs/` (GPU) or on-device; fusion uses the existing alarm seam;
UI in `web/labs/`.

**Deps:** `LABS-1`, `ENGINE-4`, `ALARM-5`, `CONTRACT-10`, `AI-13`, `AI-14`, `CONN-1`, `AI-5`,
`AI-17`. **Effort:** L (range estimation + model quality are the risk). **Status:** Not Started.

**Specific guardrail.** Supplemental; **never suppresses a real AIS or radar target**; labelled
"camera-detected, unverified"; on-boat processing by default (privacy). Advise-don't-act.

**Acceptance:** with a recorded forward-view clip, the Lab detects and plots vessels as
bearing/range targets, raises a CPA-style advisory, and never downgrades or hides a concurrent
real AIS target.

---

### LABS-4 · AR Heads-Up Pilotage Overlay

**Summary.** A live phone/tablet camera view with navigation data painted onto the real world —
Furuno ENVISION for cruisers.

**What it does (UX).** Forward camera shows AIS targets + names, route/waypoints, the reef edge
and hazard objects, anchored-boat labels, and your swing circle, placed by bearing/range over the
live video. Best entering a crowded anchorage or lining up a reef pass.

**Why.** "Explain-this, pointed at the water." High-impact demo that reads as *modern* to the
OpenCPN crowd; the natural display surface for `LABS-3`.

**Approach.** Pose from GPS + magnetometer heading + IMU tilt (`deviceorientation` on web,
CoreMotion on native) → camera intrinsics → horizon + projection → place chart/AIS features.
Includes a compass-offset calibration flow (the real at-sea hard part). View in `web/labs/`;
native camera path via `NATIVE-2`/`NATIVE-5`.

**Inputs.**
- *Have:* AIS (`AIS-1`), route (`ROUTE-2`), chart object query (`CHART-10`), heading
  (`OWNSHIP-1`).
- *Need:* camera + pose fusion, the projection layer, calibration UX. Shares projection code with
  `LABS-3`.

**Deps:** `LABS-1`, `AIS-1`, `ROUTE-2`, `CHART-10`, `OWNSHIP-1`; native camera `NATIVE-2`/`NATIVE-5`.
**Effort:** M (web prototype) → L (native, stabilized). **Status:** Not Started.

**Specific guardrail.** Compass error shown live; "do not rely on AR alignment for clearance or
collision decisions."

**Acceptance:** on a phone, real AIS targets and the active route appear at the correct bearing
over the camera feed within the stated compass-accuracy band; calibration adjusts the offset;
disclaimer always visible.

---

### LABS-5 · S-100 Layer Ingestion Spike + contract alignment

**Summary.** A research spike: can Helm natively ingest S-100 product specs, and what must the
layer contract add to do so?

**Scope.** Assess open S-100 tooling maturity (GDAL S-102/BAG, S-104/S-111 GML, S-124); map each
product spec to an existing Helm layer — **S-102 → bathymetry/contours, S-104 → tides, S-111 →
currents, S-124 → nav warnings, S-129 → UKC / pass conditions (= `TIDES-5` + `LABS-2`)**; decide
the additions the layer/probe contract needs to consume an S-100 dataset as just another layer.

**Why.** S-100 is the pro standard from 2026 and *is* the layered-data-canvas model = our
marketplace. Aligning now means official layers and marketplace layers travel one pipe, and Helm
becomes the first *consumer* chartplotter surfacing S-100 layers to cruisers.

**Deps:** `LABS-1`, `CHART-3`, `AI-5`, `AI-17`, `TIDES-2`, `WX-1`. **Effort:** M (spike).
**Status:** Not Started. **Output:** an ADR in `docs/decisions/` + a sample S-102/S-104 dataset
rendered through the Lab loader; no production UI claim until a real dataset renders.

**Competitive implications (why this spike matters beyond the feature).**

- **Standards tailwind, not a proprietary bet.** S-100 *is* the layered-data-canvas model =
  our marketplace, and it's the IMO-mandated direction. Aligning the layer contract to S-100
  makes Helm the only *recreational* client speaking the professional chart language across
  S-57 (past) / S-52 render (present) / S-101 (future) — *ahead of* OpenCPN, which is slow on
  S-100. That strengthens the OpenCPN-refugee pitch rather than competing with it.
- **Lowers marketplace integration cost.** A provider publishes a *standard* S-102/S-104
  product rather than a Helm-specific adapter, so some tier-2 ("yes at scale") rev-share
  answers get easier (see [BUSINESS-MODEL.md §10](BUSINESS-MODEL.md)).
- **Makes the flagship standards-native.** The S-104→S-101 safety-contour interop *is* the
  pass advisor (`LABS-2`) + `ALARM-8`, first-class rather than stitched from heterogeneous
  sources — more robust and more defensible.
- **An honesty edge unique to Helm.** Source-tagging (`ENGINE-7`) + advise-don't-act (`AI-13`)
  let us stack a licensed S-101 base + a premium S-102 layer + an unofficial cruiser layer
  (`LABS-6`) in one view with per-layer provenance shown — commercial ECDIS can't (regulatory),
  the recreational apps won't (opaque).

> **Guardrail — data model YES, commercial ECDIS NO.** Adopt the S-100 *data model and
> ingestion* for the cruiser/bridge use case (real-time, on-the-boat, offline). Do **not** drift
> toward a type-approved / SOLAS commercial ECDIS or a fleet-route-optimization "office" product
> — that arena (Furuno, Wärtsilä/Transas, NAVTOR, ChartWorld) is regulated, liability-heavy, and
> a different buyer. The standard's commercial origin *will* pull this way; resisting it is the
> positioning. Near-term scope stays the **Hybrid Bridge**: free NOAA S-57/S-52 base + the free
> S-100 overlays that exist + BYO — not a bet on global S-101 coverage (years out, tooling early,
> many layers licensed).

---

### LABS-6 · Shareable Cruiser Layers (the AML / NUDL pattern) + RTZ route exchange

**Summary.** Package and exchange cruiser local knowledge as signed, source-tagged layers; make
routes interoperable via the ISO **RTZ** format.

**What it does (UX).** Bundle marks/tracks/notes/verified-passes into a "cruiser layer"; share it
boat-to-boat, via the cruising net, or through the backend; import it with provenance shown and a
trust prompt. Routes import/export as RTZ for interop with other plotters.

**Why.** The military transfers user-defined layers between units (NATO NUDL); in undersurveyed
waters (e.g. Fiji) cruiser local knowledge *is* the chart. Direct community + marketplace fuel.

**Approach.** A layer manifest that extends the marketplace layer contract; export/import in
GeoJSON/GPX (+ RTZ for routes); provenance via source-tagging (`ENGINE-7`); an import-trust model
(imported layers are unofficial/advisory by default, never silently overwriting official data).

**Inputs.** *Have:* places/pins CRUD (`PLACES-2`), source-tagging (`ENGINE-7`), route store
(`ENGINE-6`/`ROUTE-3`), shell registration (`SHELL-1`). *Need:* the manifest format, RTZ
read/write, the import-trust UX.

**Deps:** `LABS-1`, `PLACES-2`, `ENGINE-7`, `ROUTE-3`, `SHELL-1`, `NATIVE-14`. **Effort:** M.
**Status:** Not Started.

**Specific guardrail.** Provenance always shown; imported layers advisory/unofficial by default;
no silent overwrite of official chart data.

**Acceptance:** export a set of marks + a route to a cruiser-layer file; re-import on a clean
instance with provenance intact; a round-tripped RTZ route opens correctly in OpenCPN.

---

### LABS-7 · RTK / precise-positioning spike (anchor-drop & bommie avoidance) `[optional]`

**Summary.** Bring centimetre-class positioning to the helm via NTRIP/RTCM, honestly surfaced.

**Scope.** NTRIP/RTCM3 ingest as a `CONN` driver; surface fix quality (RTK fixed / float /
DGPS / autonomous) truthfully; a precise anchor-drop mark and sub-metre track for coral piloting.

**Why.** Pro Pilot Portable Units use cm-RTK for docking; the hardware is cheap now; the hacker
crowd loves it.

**Deps:** `LABS-1`, `CONN-1`, `ENGINE-7`. **Effort:** M (spike). **Status:** Not Started.

**Specific guardrail.** Always display fix-type + accuracy estimate; **never imply precision the
fix doesn't have.**

---

## 5. Build order & dependencies

`LABS-1` (framework) gates everything. The hero trio is `LABS-2` (pass advisor), `LABS-3` (AI
lookout), `LABS-4` (AR) — and `LABS-3`/`LABS-4` share the AR projection work, so build `LABS-4`'s
projection first and `LABS-3` reuses it.

| Task | Fit for the niche | Effort | Key existing deps | Status |
|---|---|---|---|---|
| LABS-1 framework | enabler `[blocking]` | S | OFFLINE-2, AI-13, SHELL-1 | Not Started |
| LABS-2 pass advisor | ★ flagship | M–L | BOAT-1, TIDES-2, WX-1, CHART-7, ALARM-8 | Not Started |
| LABS-3 AI lookout | ★ high differentiation | L | ENGINE-4, CONTRACT-10, AI-14, CONN-1 | Not Started |
| LABS-4 AR pilotage | ★ demo-magic | M→L | AIS-1, CHART-10, OWNSHIP-1 | Not Started |
| LABS-5 S-100 spike | strategic | M | CHART-3, AI-5/17, TIDES-2 | Not Started |
| LABS-6 shared layers | community moat | M | PLACES-2, ENGINE-7, NATIVE-14 | Not Started |
| LABS-7 RTK | optional | M | CONN-1, ENGINE-7 | Not Started |

---

## 6. Graduation criteria (when a Lab leaves Labs)

A Lab graduates into a real workstream — or becomes a sellable marketplace layer — when:

1. it is **boat-tested** on real data (not just sim/replay);
2. its **guardrails are verified** (source-tagged, advisory-only, degrades gracefully offline,
   never overrides an authoritative source);
3. its **contract is stable** (for layer-shaped Labs, it conforms to the frozen probe/layer
   contract `AI-17`, so a third party could supply the same layer); and
4. counsel has cleared any new data source it introduces ([LEGAL.md](LEGAL.md)).

Until all four hold, it stays behind the Labs flag.
