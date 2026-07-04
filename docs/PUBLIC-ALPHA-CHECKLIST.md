# Public Alpha Checklist

This is the release gate for showing Helm to the OpenCPN / cruiser community
without accidentally giving up the future Helm Cloud business or overclaiming
legal readiness.

## The posture

Helm should be introduced as a technical alpha and an invitation for feedback:

- OpenCPN-derived engine work stays GPLv2-or-later and source-visible.
- Helm-authored web/backend code is source-available under BSL 1.1 today and
  converts to Apache-2.0 later.
- Personal boat use, self-hosting, modification, redistribution, and
  contribution are allowed now.
- Competing hosted or managed commercial services are the one reserved use
  until the BSL change date.
- The durable business is Helm Cloud: hosted tiling, GRIB/weather delivery,
  route/mark sync, community backend, remote watch, AI inference, and future
  layer-marketplace rails.

Say "source-available" when talking about BSL. Do not call the BSL-covered
client "open source" until it converts to Apache-2.0.

## What to publish first

- Screenshots and a short demo video of the browser client.
- The architecture: headless OpenCPN model/ boat server, thin browser/mobile
  clients over /nav and /chart, and auxiliary services around the safety core.
- The OpenCPN-derived engine patch series/fork under GPLv2-or-later.
- The web client and backend with LICENSE, LICENSE.BSL, NOTICE, SAFETY.md, and
  clear "pre-alpha / not primary navigation" warnings.
- Build/run notes that use private dev ports and do not touch any stable live
  `:8080` instance.

## What not to publish yet

- Cached Google, Navionics, Esri, Bing, Windy, PredictWind, or other
  restricted commercial data.
- A downloadable appliance image or paid build before IP counsel reviews the
  GPL boundary, BSL wording, attribution register, and chart-data sources.
- A public macOS DMG before `native/macos/package-macos-dmg.sh --notarize`
  passes with a Developer ID identity, the notarization ticket is stapled, and
  counsel has reviewed the native-client notice bundle.
- A standalone phone-only promise. That path requires the clean-room renderer
  work tracked separately from the current headless OpenCPN engine.
- Claims that Helm is type-approved, certified, primary-navigation ECDIS, or a
  replacement for watchkeeping.
- Commercial S-100/storefront/AI-advisory claims beyond "future direction" and
  "advisory-only experiments".

## Give-back plan for OpenCPN

Giving back does not require merging Helm into the OpenCPN repository. The alpha
give-back should be:

- a public GPL patch series against the pinned OpenCPN commit;
- a short headless-build note for OpenCPN developers;
- upstreamable small seams where they are generally useful;
- clear attribution that OpenCPN remains the mature safety core Helm is building
  around;
- no pressure on upstream to accept a large web-client direction.

## Web client and browser code

The browser client is the showcase, but it must stay clean:

- Keep OpenCPN source expression out of web/.
- Keep GPL/LGPL/AGPL dependencies out of web/vendor/.
- Keep the client coupled to the engine only through documented HTTP/WebSocket
  protocol surfaces.
- Re-run docs/CLIENT-LICENSE-REGISTER.md audit steps before public release and
  on every browser dependency bump.
- Preserve all map/layer attributions visibly in the UI.

## Cruisers Forum voice

Lead with respect for OpenCPN and with working code:

- "I am building a modern browser/touch client around a headless OpenCPN-based
  boat server."
- "This is alpha, not a primary-navigation recommendation."
- "The OpenCPN-derived engine work stays GPL and visible as a separate patch
  series/fork."
- "The web/backend code is source-available, self-hostable, and intended to
  keep a future Helm Cloud option open."
- "I am looking for architecture feedback, tester interest, and advice on what
  seams would be useful upstream."

Avoid opening with legal argument. Keep the GPL/App Store and BSL details in the
repo docs unless someone asks directly.

## Pre-post checklist

- [ ] Reconcile local branch with origin/main before publishing code or making
      commit-specific claims.
- [ ] Publish from a clean branch/PR, not a dirty/diverged local `main`.
- [ ] Review or exclude local agent/live-machine files before public release:
      `.claude/`, `AGENTS.md`, launch configs, private ports, local absolute
      paths, live-machine config notes, and any scripts that touch a stable
      `:8080` instance.
- [ ] Run the client license audit in docs/CLIENT-LICENSE-REGISTER.md.
- [ ] Refresh docs/RUNTIME-LICENSE-REGISTER.md against the exact release
      engine/native artifacts.
- [ ] Refresh NOTICE with any new dependencies, fonts, map sources, and sample
      data.
- [ ] Confirm SAFETY.md is linked from README, release notes, and public demo
      material.
- [ ] Confirm public demo media contains no private route, MMSI, token, key, or
      location data you do not want public.
- [ ] Confirm public screenshots show supplemental-layer disclaimers and source
      attribution.
- [ ] Confirm the demo uses public/sample data or your own boat data only.
- [ ] Link docs/LEGAL.md from the public README.
- [ ] Link docs/posts/cruisersforum-opencpn-update.md from any launch issue or
      release note.
- [ ] Get IP counsel before any paid distribution or preloaded appliance.
