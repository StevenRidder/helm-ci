# ADR-0010 — Distribution & packaging posture (open-core; BSL backend; proprietary clients)

- **Status:** Proposed (the BSL terms + the GPL boundary need IP-counsel sign-off before any *paid* launch — see [ADR-0003](0003-license-posture.md), [LEGAL](../LEGAL.md))
- **Date:** 2026-06-26
- **Builds on:** [ADR-0001](0001-successor-not-fork.md) · [ADR-0003](0003-license-posture.md) · [ADR-0009](0009-arms-length-gpl-containment.md) · [BUSINESS-MODEL](../BUSINESS-MODEL.md) · relates to `NATIVE-12`

## Context

Helm spans three things that must ship under three different licenses:

1. The **engine** (`helm-server`) reuses OpenCPN's `model/` + `s57chart`, so it is **GPLv2-or-later** — its source is necessarily public.
2. The **backend** (FastAPI: places / weather / intelligence / community) is Helm's own code and is going to a **public GitHub repo**.
3. The **clients** (web today; native macOS/iPad/iPhone later) are the proprietary UX we want to keep — and we want to **reserve the ability to monetize later**.

The load-bearing enabler is already built: [ADR-0009](0009-arms-length-gpl-containment.md) — clients couple to the GPL engine **only over the network protocol** (nav WS + chart HTTP), never by linking/bundling it. That arm's-length boundary (enforced by `engine/containment-check.sh`) is what lets the clients carry *any* license we choose. Lose it and the client becomes a GPL derivative.

The revenue thesis ([BUSINESS-MODEL.md](../BUSINESS-MODEL.md)) is the Home-Assistant playbook: **free/open software is the on-ramp; the money is the cloud subscription** (hosted tiling, GRIB, sync, AI copilot inference, community, remote watch), with an optional near-cost appliance. So the licensing job is not to hide the clients — it is to **protect the cloud business** while keeping the on-ramp open.

## Decision

### Per-component licensing

| Component | License | Distribution | Rationale |
|---|---|---|---|
| **Engine** (`helm-server`) | **GPLv2-or-later** (forced) | Source public; ships as a standalone process on the boat | OpenCPN-derived, commodity; not the moat |
| **Backend** (public repo) | **BSL 1.1 → Apache-2.0** | Public GitHub | Source-available, but commercial competing-hosting reserved to us until the change-date — the key "reserve money" lever |
| **Web client** | **BSL 1.1 → Apache-2.0** | Hosted SaaS (login-gated) and/or served by the boat engine (offline) | JS is inherently readable; the moat is the cloud it calls, not the source |
| **Native clients** | **Proprietary (closed binary)** | iOS: App Store thin client · macOS: notarized DMG | Compiled → genuinely closeable; engine stays a separate process (App-Store-clean) |
| **Cloud services / infra** | **Proprietary** | Hosted only (never shipped) | The durable business |

### The BSL 1.1 parameters (the monetization reservation)

Applied to the backend (and the web client):

- **Change License:** Apache-2.0.
- **Change Date:** the **fourth anniversary** of the publication of each released version (rolling per-version, MariaDB-style).
- **Additional Use Grant:** *"You may make production use of the Licensed Work, provided your use does not include offering the Licensed Work to third parties as a hosted or managed commercial service that competes with Helm Cloud."* (Self-host, personal use, internal use, and non-commercial use are all permitted now; only a competing commercial SaaS is reserved — and even that frees up on the change-date.)

This is the standard "open now, monetize later" instrument (MariaDB, Sentry, HashiCorp). It keeps the community on-ramp open (inspect, self-host, contribute, fork for non-competing use) while reserving the Helm Cloud business for up to four years per release.

### Distribution channels

- **Web:** hosted at an app origin behind auth/subscription, **and/or** shipped on the boat-server (offline-first) as *mere aggregation* next to the GPL engine — permissible because the coupling is the network protocol, not linkage ([ADR-0009](0009-arms-length-gpl-containment.md)).
- **macOS:** **notarized DMG, not the App Store** — sidesteps the GPL-vs-App-Store "VLC problem" entirely (the engine is a contained process). macOS is the strongest reuse path ([BUSINESS-MODEL.md §3](../BUSINESS-MODEL.md)).
- **iOS/iPadOS:** App Store **thin network client**; the GPL engine stays on the boat (Mac mini / Pi), so nothing GPL ships through the App Store.
- **Appliance:** Mac mini + marine touchscreen, pre-configured, sold **near cost** — convenience on-ramp, not the revenue.

### Where the money is

Per [BUSINESS-MODEL.md](../BUSINESS-MODEL.md): the **Helm Cloud subscription** (weather/GRIB, AI copilot inference, sync, community, remote watch) is the revenue engine, protected by the BSL backend + our hosting/ops/brand. Native app sales and the appliance are secondary. The open engine and open-ish clients are the wedge that brings OpenCPN refugees in.

## Consequences

- We can put the backend on public GitHub **today** without giving away the cloud business — BSL reserves competing commercial hosting for up to four years per release.
- Proprietary native binaries are genuinely closeable; the web client is source-visible but its value (the cloud) is not, so "proprietary web client" means *restrictively licensed*, not *secret* — and that's sufficient.
- A regression that linked/bundled the GPL engine into a client would make that client GPL; the [ADR-0009](0009-arms-length-gpl-containment.md) guard fails the build before that ships.
- BSL is *source-available*, not OSI "open source" — set expectations with the cruiser community accordingly (it converts to true Apache-2.0 on the change-date).
- Dependencies must stay GPL-compatible-or-permissive in the engine, and license-clean in the clients (GDAL/PROJ = MIT/X-style; MapLibre = BSD).

## Open

- **IP counsel** to ratify the BSL Additional-Use-Grant wording, the four-year change-date, and the GPL boundary before any paid launch.
- Decide whether the **web client** is BSL (reserves it) or Apache from day one (maximal wedge, rely entirely on cloud + native for revenue) — default here is BSL; revisit if web adoption matters more than reservation.
- A `LICENSE` + `LICENSE.BSL` header policy per repo, committed before any repo goes public.
- Chart/imagery source tiering in a *distributed* product remains bound by [LEGAL.md](../LEGAL.md) (BYO-only sources never ship in a sold build).
