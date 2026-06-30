# Icon Forge — full context thread

> Reconstructed narrative of the working session that produced the `FORGE` lane
> and POC. Authored from the conversation (not a verbatim system transcript:
> tool-call noise and reminders are omitted). Use this to onboard a fresh agent
> to the complete context. Companion: [`AGENT-BRIEF.md`](AGENT-BRIEF.md).

## Phase 1 — the ask and what was reachable

**Request:** "Extract all S-52/57 icons from NOAA Chart 1 so we can save them in a
DB and render them on demand." (The user first wrote "DV"; clarified to "DB".)

**Plan-repo access:** the user asked us to read the Helm repo and the project
plan (`plan.taikunAI.com`). The plan MCP server was **not connected** to the
session and the site returned **403** to a direct fetch — so all context came
from the Helm repo itself. (If a Switchboard/plan API + token is provided, this
gap closes.)

**Key finding:** S-52/S-57 symbols don't live *in* NOAA Chart No.1 as a graphics
source. They live in the **IHO S-52 Presentation Library** that the Helm engine
already consumes — `data/s57data/chartsymbols.xml`, `rastersymbols-{day,dusk,
night}.png`, `S52RAZDS.RLE` — copied in at build time by `engine/bootstrap.sh`
(not committed to the repo; absent in a fresh container). NOAA Chart No.1 (the
booklet) is the human-readable *catalog* of what each symbol means.

## Phase 2 — how NOAA "Chart No.1 online" embeds icons (researched)

- **U.S. Chart No.1** is a publication (PDF, 13th ed.), documenting NGA paper +
  IHO ECDIS/S-52 symbols side by side — a reference catalog, not a sprite source.
- **The NOAA ENC Online Viewer** (the interactive map) is an Esri/ArcGIS app
  backed by a NOAA **Maritime Chart Service** extension on a MapServer
  (`gis.charttools.noaa.gov/arcgis/rest/services/MCS/ENCOnline/MapServer/exts/
  MaritimeChartService`). It **renders ENC features into raster tiles
  server-side using IHO S-52 Presentation Library ed. 3.4** ("ECDIS symbology").
- So the browser never receives a folder of icon PNGs — the symbols are burned
  into the tiles by a server-side S-52 renderer. The true origin is the IHO S-52
  Presentation Library — the same asset OpenCPN/Helm use. You cannot scrape clean
  icons out of the rendered tiles.

## Phase 3 — how symbols flow through Helm's Vulkan path (repo synthesis)

- Source of symbol graphics: the OpenCPN-shipped S-52 Presentation Library
  (`chartsymbols.xml` + `rastersymbols-*.png`), parsed by `s52plib`.
- An atlas builder already exists: `engine/vendor/cli/helm_s52_atlas*.cpp`
  (Vulkan board `SYM-2`) — packs symbols into per-palette sheets + a JSON
  manifest keyed `(name, kind, palette)` with `pixel_rect`/`uv`/`anchor`. **But
  it currently runs off a synthetic 3-entry fixture, not the real library.**
- The audit `docs/VULKAN-S52-SEMANTICS-AUDIT.md` (`SYM-1`) names real-library
  extraction as deferred `SYM-2` work.
- **Licensing constraint:** extracting the *real* OpenCPN symbols carries
  GPLv2-or-later provenance (`docs/VULKAN-RENDER-LICENSE-BOUNDARY.md`). Symbol
  extraction is engine-side GPL work; the web/mobile client must stay
  arm's-length.

## Phase 4 — the two-stage architecture (user's strategy + our feedback)

The user shared their production strategy: a two-stage chart architecture
(Source → Converter → **Portable Nautical Package** → Presentation Compiler →
**Neutral Render Model** → machine-local **GPU artifact cache** → Backend), with
production lanes FORMAT/CONVERT/PRESENT/CACHE/BACKEND/DEBUG/PERF/QA/UPSTREAM
thrown at agents on their **Switchboard** platform, and a "keep it tiny" next
proof.

Our feedback (the load-bearing points):
1. The portable-vs-disposable split is **also their GPL-containment boundary** —
   Presentation Compiler = GPL-heavy; Neutral Render Model = the arm's-length
   published seam; GPU cache + backend = Helm's own (WebGPU). Architecture and
   licensing reinforce each other.
2. **The diagram is missing a third durable input:** the symbol/colour/lookup
   **Presentation Asset Pack** — the style sheet, distinct from chart truth and
   GPU cache. That pack is exactly what "icons → DB → render on demand" produces.
   Version it by presentation-library edition (NOAA versions theirs "S-52 PresLib
   ed 3.4"); key it `(presLib_edition, name, kind, palette)`.
3. Other pushes: the Neutral Render Model is the crux (don't let it inherit
   DC-specific artifacts); give the GPU cache a content-addressed escape hatch
   (don't cold-rebuild atlases per client); the portable package needs namespaced
   per-object-class extensions (S-101 will stress it); elevate the **Object
   Inspection Trace** to a co-equal deliverable (provenance is the trust
   mechanism); make the tiny proof exercise the **symbol path** (a buoy +
   conditional-symbology case), not just `AreaFill`.

## Phase 5 — Fiverr → LLM reframe and the build design

User: normally they'd hire a Fiverr artist to copy U.S. Chart No.1; they want an
LLM to do it instead, in multiple styles ("open bridge" look vs "USA" look).

The reframe that makes it safe and beats Fiverr:
- A chart symbol's **meaning is load-bearing** (green-vs-red, topmark shape, light
  flare, distinguishing geometry, anchor/pivot) — those are **invariant,
  machine-checked**. Stroke weight, rounding, fill style, house look are the
  **free aesthetic axis** = "style."
- **Generate SVG, not PNG** (LLMs are good at SVG-as-code; scalable, restyleable
  via CSS vars → palettes for free, diffable, reviewable).
- **Compose from per-style primitives** so the set is one coherent family.
- **The verifier is the centre of gravity**, not the generator: structural checks
  + a vision judge against a per-symbol checklist + a **sibling-discrimination**
  forced choice (catches subtle-but-dangerous confusions a "looks like a buoy?"
  check passes). Bounded repair loop; a logged human "hard pile" for failures
  (no silent caps).
- **Clean-IP unlock:** generating *own* artwork from the **public-domain** U.S.
  Chart No.1 (a U.S. Government work), rather than extracting OpenCPN's GPL
  rasters, yields a library Helm **owns** — turning a GPL liability into an owned,
  relicensable asset (subject to a counsel note; symbol *shapes* are functional
  IHO-standard, the booklet is public domain, fresh artwork is Helm's).
- **Economics:** prompt-cached per-style prefix + Batch API (50%) ≈ $0.03–0.06
  per (symbol, style); ~$40–80 for a 1,000-symbol library in one style, ~$150–250
  across three, regenerable. A contractor is ~$1–3K per style, not regenerable.
- Model: `claude-opus-4-8` (vision-capable) for compose and judge; structured
  outputs for typed results; the whole thing is a code-orchestrated workflow, not
  an open-ended agent.

## Phase 6 — the FORGE lane plan

Scoped onto the **Vulkan board** (right home — it feeds `SYM-2`), matching the
board's `docs/VULKAN-*.md` + `Status: Vulkan board \`CODE\`` convention:
**`docs/VULKAN-ICON-FORGE.md`** — the Presentation Asset Pack generator. Two-axis
model, six-stage pipeline, owns/collision boundary (`pipeline/iconforge/**`),
`FORGE-1`..`FORGE-11` tasks, the tiny proof, clean-IP licensing (`FORGE-10`
counsel gate), determinism, cost, and the `(catalog_id, style, palette)` →
`helm_s52_atlas` manifest mapping. Commit `ba8e557`.

## Phase 7 — the POC (executed)

Built `pipeline/iconforge/` and ran it. Five region-independent, unambiguous
symbols: **north cardinal buoy, south cardinal beacon, safe-water buoy,
restricted-area pattern, dangerous wreck** × **2 styles** (`us-paper`,
`open-bridge`) × **day/dusk/night**, plus one **deliberately-broken** north
cardinal (topmark cones flipped down).

Sandbox had **no API key**, so the two LLM stages (compose SVG, vision verdict)
ran as **recorded `claude-opus-4-8` output** (fixtures), while the deterministic
stages ran live: SVG→PNG render via cairosvg, structural checks, atlas pack +
manifest, contact sheet.

**Result: 10/11 accepted.**
- The broken north cardinal is **REJECTED** — the sibling-discrimination judge
  identifies it as a **south cardinal** (wrong-quadrant grounding hazard) despite
  being structurally valid. This is the intended demonstration.
- The **structural** verifier also caught a genuine mistake mid-run: the wreck
  was first drawn in the `ink` token while its load-bearing invariant colour is
  `black`, so `invariant_colours_used` failed until the artwork referenced
  `black` — exactly the silent error a contractor would ship.
- The atlas manifest came out in the `helm_s52_atlas` shape + a `style` axis.

Commit `a6e817f`. Artifacts under `pipeline/iconforge/samples/`
(`contact_sheet.png`, atlas sheets, manifests, `report.json`).

## Phase 8 — wiring the live judge

User chose "wire the live judge." Since no key was present, we made the path
**injectable and proven without a key**:
- `forge/judge_live.py` — runs the real `claude-opus-4-8` vision judge against the
  recorded renders (incl. the broken case) and reports live-vs-recorded
  agreement. Isolates the judge from compose so the only live variable is the
  verdict. Degrades gracefully without a key.
- `forge/tests/test_live_judge_wiring.py` — stubs the client to assert the
  request build (model id, `json_schema` structured output, base64 vision block,
  per-symbol checklist with the topmark invariant + sibling forced-choice list)
  and the verdict parse are correct. **Green.**

The live model's *agreement* is **unobserved** until someone runs
`ANTHROPIC_API_KEY=… python3 -m forge.judge_live` on a keyed machine — the single
cheapest highest-signal next step. Commit `9ac5004`.

## Phase 9 — PR

PR **#229** opened against `main` from
`claude/s52-57-icon-extraction-48o9k7`, body to the repo PR template.
<https://github.com/StevenRidder/Helm/pull/229>

## Constraints to carry forward

- **Safety-critical:** a wrong colour/topmark is a navigation hazard. The verifier
  is the safety mechanism — never weaken it for throughput.
- **Clean-IP:** generate own artwork from public-domain U.S. Chart No.1; do **not**
  extract OpenCPN's GPL rasters into the owned pack. `FORGE-10` is the counsel
  gate; until cleared, keep the pack engine-side of the license boundary.
- **No silent caps:** failures go to a logged human hard-pile, never dropped.
- **Determinism:** content-hash inputs; only changed inputs regenerate.

## Artifact map

| Path | What |
|---|---|
| `docs/VULKAN-ICON-FORGE.md` | the lane plan (FORGE-1..11) |
| `pipeline/iconforge/forge/` | the program (schema, model, render, verify, atlas, contact, run, judge_live) |
| `pipeline/iconforge/catalog/` | 5 SymbolSpec JSON |
| `pipeline/iconforge/stylepacks/` | 2 StylePack JSON |
| `pipeline/iconforge/fixtures/` | recorded compose SVGs + verdicts |
| `pipeline/iconforge/samples/` | committed contact sheet, atlas sheets, manifests, report |
| `pipeline/iconforge/README.md` | how to run |
| `pipeline/iconforge/AGENT-BRIEF.md` | the fresh-agent handoff |
