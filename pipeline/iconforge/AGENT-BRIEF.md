# FORGE — agent handoff brief

Self-contained briefing for an agent picking up the Icon Forge lane. Full
backstory: [`CONTEXT-THREAD.md`](CONTEXT-THREAD.md). Plan:
[`../../docs/VULKAN-ICON-FORGE.md`](../../docs/VULKAN-ICON-FORGE.md).

## What this is

`FORGE` generates the IHO S-52 / U.S. Chart No.1 nautical symbol library as
**owned, multi-style SVG** — the "Presentation Asset Pack" that feeds the Helm
engine's `SYM-2` atlas (`engine/vendor/cli/helm_s52_atlas*.cpp`). It replaces
hiring an artist to hand-trace Chart No.1: a code-orchestrated pipeline re-draws
a fixed, **safety-critical** catalog with the *style* varied only on the
non-semantic axis, machine-checked by a vision + sibling-discrimination verifier.

## Where things are

- Repo: `StevenRidder/Helm`  ·  Branch: `claude/s52-57-icon-extraction-48o9k7`
  ·  PR: **#229** (base `main`).
- Code: `pipeline/iconforge/` — `forge/{schema,model,render,verify,atlas,contact,run,judge_live}.py`,
  `catalog/` (5 specs), `stylepacks/` (2), `fixtures/` (recorded model output),
  `samples/` (committed results).

## State (done)

- POC runs end-to-end over 5 symbols × 2 styles × 3 palettes + 1 broken case.
  **10/11 accepted**; the broken north-cardinal (cones flipped) is rejected as a
  south cardinal by the sibling test.
- Deterministic stages (render, structural verify, atlas/manifest) run live.
- LLM stages (compose SVG, vision verdict) are recorded `claude-opus-4-8` output;
  `LiveModel` swaps them for live API calls when `ANTHROPIC_API_KEY` is set.
- Live-judge path (`forge/judge_live.py`) is wired; offline wiring test is green.

## Run it

```bash
cd pipeline/iconforge
pip install cairosvg pillow
python3 -m forge._seed_fixtures            # write recorded fixtures
python3 -m forge.run                       # full pipeline -> out/
python3 -m forge.tests.test_live_judge_wiring   # offline plumbing check (no key)
ANTHROPIC_API_KEY=... python3 -m forge.judge_live   # the REAL vision judge
```

## Non-negotiable constraints

1. **Safety:** a wrong colour or flipped topmark is a navigation hazard. The
   verifier is the safety mechanism — strengthen it, never weaken it for speed.
   Every symbol must pass structural + vision + sibling checks before it ships.
2. **Clean-IP:** generate **own artwork** from public-domain U.S. Chart No.1. Do
   **not** copy/extract OpenCPN's GPL `rastersymbols-*.png` into the owned pack.
   `FORGE-10` is the IP-counsel gate.
3. **No silent caps:** failures go to a logged human "hard pile," never dropped.
4. **Determinism:** content-hash `(spec + stylepack + primitives + prompt_version
   + model_id)`; regenerate only changed inputs.
5. Output must stay in the `helm_s52_atlas` manifest shape — entries keyed
   `(name, kind, palette)` with `pixel_rect`/`uv`/`anchor` — plus the `style`
   axis. Don't break that contract.

## Pick one next task

**(A) Observe the live judge** (cheapest, highest signal). Run
`python3 -m forge.judge_live` with a key; confirm a real vision pass rejects the
flipped-cone case and clears the ten good symbols. Record agreement in
`out/live_judge_report.json`. If the schematic SVGs are too rough for a strict
judge, that's the signal to do (B) first.

**(B) FORGE-2 — real catalog geometry.** Replace the hand-built schematic SVGs
with `SymbolSpec`s and primitives driven from real `chartsymbols.xml` metadata +
U.S. Chart No.1 reference crops. Keep CSS-var colours, the anchor/pivot, and the
sibling lists. Acceptance: the existing 5 symbols regenerate and still pass the
verifier, with geometry traceable to a source reference (provenance recorded).

**(C) Widen the set** to ~20 symbols including a conditional-symbology pair
(e.g. dangerous vs non-dangerous wreck) to stress the verifier's discrimination.
Acceptance: verifier accept-rate reported per symbol; any rejects land in the
hard-pile with reasons.

## Definition of done for the lane proof

The verifier's measured accept-rate — not vibes — gates the bulk run. Before
fanning the full ~1,000-symbol set through the Batch API: live judge observed
(A), real geometry in place (B), ~20-symbol batch clean (C), and the `FORGE-10`
clean-IP counsel note resolved.
