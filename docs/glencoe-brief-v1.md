# Hermes Brief — Glencoe Dossier Prototype (first consumer of the Layer Contract)

**From:** Sink / Fable scoping session, 21 Jul 2026
**Attached:** `layer-contract-v0.1.md` (governing document — read first)
**Status:** Approved for build. Constraints below are decisions, not preferences.

## What this is

A single standalone page — one Scottish place, all live layers we hold about it, one view. It is simultaneously (a) the cross-layer value experiment you proposed, and (b) the first integration test of the Layer Contract. If the page is compelling, the joins are real and the eventual shell inherits a proven pattern. If it's flat, we've spent a page, not a platform.

Working title: **the Glencoe dossier**. No product name, no brand, no domain decision yet — deploy to a plain Netlify preview URL.

## Ruling on the EarthOS document

The EarthOS block is external stimulus pasted in from another session — treat it as provocation, not as the design brief. The design brief is the Layer Contract. Do not build toward EarthOS's seven layers; several (Future Simulator, wellbeing prediction) are outside our claims-we-can-stand-behind line and stay out permanently.

## Hard constraints

1. **BiteForecast is a face, not a shell.** Nothing is built *into* BiteForecast. Its only involvement is publishing its existing per-destination output in contract-compliant shape (envelope + where/when/what keys). The Bampot's register does not touch civic or heritage data. The dossier *reads* BiteForecast's JSON; it does not live there.
2. **Own stack, no fork.** SvelteKit on Netlify, consistent with the estate. No World Monitor code (AGPL propagation + settled own-shell decision). Their patterns — single layer config, progressive disclosure — may be imitated freely; their code may not be copied.
3. **Contract-shaped inputs only.** The dossier renders exclusively from contract cores (`where` / `when` / `what` + envelope). It never reaches into any layer's `payload`. If the page can't be built without payload access, that is a contract finding — report it, don't work around it.
4. **Live layers only in v1.** Midge risk (BiteForecast), summit windows (munro.json, once the v2 fetch script is deployed), vigil countdowns (standing-stones JSON API). Explicitly excluded from v1: SIMD/deprivation indices, land ownership, planning applications — static-reference or claims-adjacent, wrong test material. Disaster Index: **skip in v1** (three real joins prove the thesis; a fourth section dilutes the experiment). **Expectation, set now:** the v1 Glencoe dossier may be sparse — a handful of lines plus one honest absence. That is a valid experimental outcome, not a failure; do not pad it.
5. **Staleness is enforced, not styled.** Items past `when.end`, or layers older than two cadences, do not render. No "last updated 3 days ago" apologetics — absent means absent.

## Build steps (order matters)

0. **Test harness before any real adapter.** One script emitting a fake contract-compliant `items` array — one condition, one window, one countdown, all on Glencoe atoms — so the page and the contract are tuned together against a known-good target before pipeline code exists. Contract findings from the harness are cheaper than findings from three built adapters.
1. **Contract adapters (the real work).** Three small scripts/endpoints that emit contract-shaped JSON:
   - BiteForecast: wrap existing per-destination forecast as `condition/midge-risk` items, `where.atom` per destination, `when` = fetch-to-next-fetch window.
   - Munro Windows: wrap munro.json results as `condition/summit-window` items (already near-shape; add `atom`, `what`, envelope).
   - Vigil: map alignment countdowns to `when.kind: countdown`, `what.type: culture/alignment`.
   Each adapter also populates `what.headline` (≤60 chars, human) and `what.status` from the closed set.
2. **Atom resolution.** Glencoe-relevant atoms only: the Glen Coe destination atom, nearby Munros (Bidean nam Bian group, Buachaille Etive Mòr etc. as present in MUNROS config). **Vigil canon gap — acknowledged in advance:** no canon site is near Glen Coe (nearest is Ballochroy, Kintyre, ~80 miles south). The vigil section therefore renders *honest absence with a pointer* — "No vigil site near Glen Coe. Nearest: Ballochroy, ~80 miles south, next alignment in N days." — not an empty section and not a fudged inclusion. This absence-with-pointer pattern is the house style for all future gaps. Record as finding: "canon gap — no vigil site in the West Highlands" (product note: Temple Wood / Kilmartin Glen, already in the stones later-research bucket, is the nearest candidate fix). `atom: null` items may exist but won't surface in the dossier — note how many fall out, that number is a finding.
3. **The page.** One route, one place. Sections render generically from cores grouped by `what` family: conditions now, windows ahead, countdowns beyond. Order by `when.start`. A dossier is a *briefing*, not a dashboard — sparse, readable, one glance per item.
4. **Ship + verdict note.** Netlify preview URL plus a short written verdict: did cross-layer assembly produce something a single layer couldn't? What did the contract make easy, and where did it chafe? Proposed v0.2 contract amendments, if any.

## Design register

Interim only — no design language exists yet ("lighthouse keeper's desk" direction is parked, not settled). Plain, calm, text-first; no map in v1 (the dossier is the map's future click-through, and testing the joins doesn't need tiles). No brand voice. The disclaimer from each layer's envelope displays with its section.

## Acceptance

- Page renders entirely from three (±one) contract-compliant sources with zero payload access.
- Every displayed item shows headline, status, and honest time context derived from `when`.
- Expired/stale content provably absent (test by feeding a stale file).
- Verdict note delivered.

## Out of scope — do not build

Map rendering, multiple places, the shopfront, any face branding, Seeker integration, events/curation layers, the good-cause face, region gazetteer finalisation (v0.2 question), user accounts, analytics beyond a simple page-view counter.

*One page, three joins, one honest verdict. Everything else waits.*