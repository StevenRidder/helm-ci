# ADR-0003 — License posture: open now, sellable later

- **Status:** Proposed
- **Date:** 2026-06-23

## Context

Stated posture: "open-source for now, I might sell it later if allowed." That single
sentence has a hard technical consequence: if Helm's own code is GPL (e.g. by forking
OpenCPN into the core), it can never become a closed commercial product. To keep both
doors open, the core must stay **GPL-free**.

## Decision (proposed)

- **Helm's own code:** **Business Source License (BSL) 1.1** — source-available now,
  permits use/modification/self-host, restricts competing commercial hosting, and
  **auto-converts to Apache-2.0** after a set change-date (commonly 3–4 years). This is the
  standard "open now, monetize later" instrument (Sentry, MariaDB MaxScale, etc.).
  - Alternative if maximal openness is preferred: **Apache-2.0**, monetizing via a closed
    hosted/premium layer on top.
- **No GPL in the core:** the S-52 engine is rebuilt on permissive GDAL/PROJ
  ([ADR-0002](0002-enc-engine.md)) or kept as an arm's-length optional component the user
  opts into — never statically linked into a distributed Helm binary.

## Consequences

- Preserves the commercialize-later option.
- BSL is *source-available*, not OSI "open source" — set expectations with the cruiser
  community accordingly (it still converts to true open source on the change-date).
- Dependencies stay permissive (GDAL/PROJ = MIT/X-style; MapLibre = BSD).

## Open

- Pick the BSL change-date and "additional use grant" wording, or commit to Apache-2.0.
  Defer until there's code to license; commit a `LICENSE` before the repo goes public.
