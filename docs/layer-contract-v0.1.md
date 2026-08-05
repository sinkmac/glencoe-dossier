# The Layer Contract — v0.1.2

One page defining the minimal shape every live layer must publish so that joins — place dossiers, the living calendar, the weekend engine, need-anticipation — fall out later instead of being built. A layer that honours this contract can be rendered by any face, joined to any other layer, and retired without breaking anything. The contract governs the *envelope and the join keys only*; each layer's payload stays its own business.

## The envelope

Every layer publishes one JSON file (or endpoint) shaped like this:

```json
{
  "contract": "0.1",
  "layer": "munro_windows",
  "face": "conditions",
  "source": "open-meteo",
  "cadence_hours": 12,
  "updated_at": "2026-07-21T06:00:00Z",
  "disclaimer": "Forecast guidance only. Not a substitute for MWIS, SAIS, or your own judgement.",
  "items": [ ... ]
}
```

`layer` is the stable machine name. `face` declares which family the layer belongs to (`conditions`, `causes`, `culture`, `mood`) — a face renders its own layers by default and may borrow others deliberately. `cadence_hours` plus `updated_at` lets any renderer compute staleness and refuse to display expired data; a layer that misses two cadences is dark, not stale-but-shown. `disclaimer` is optional but travels with the data, not the UI. A layer may also declare an optional envelope-level `gap` object for honest-absence rendering when a queried area has no coverage — e.g. `"gap": {"nearest_atom": "ballochroy", "distance_km": 130, "next_event": "2026-12-21"}` — which renderers turn into the pointer sentence ("No vigil site near here. Nearest: Ballochroy, ~80 miles south."). Absence is data, never hardcoded copy.

## The item — three join keys plus a payload

Every entry in `items` carries the same four-part core. Everything else lives under `payload` and belongs to the layer alone.

```json
{
  "id": "munro_windows:ben-lawers:2026-07-25",
  "where": {
    "atom": "ben-lawers",
    "lat": 56.545, "lon": -4.221,
    "region": "perthshire",
    "precision": "exact"
  },
  "when": {
    "start": "2026-07-25T09:00:00+01:00",
    "end": "2026-07-25T15:00:00+01:00",
    "kind": "window"
  },
  "what": {
    "type": "condition/summit-window",
    "status": "good",
    "headline": "6-hour window from 09:00"
  },
  "payload": { }
}
```

**`id`** — globally unique, deterministic: `layer:atom:when.start` (the start of the window the item *describes*, never the fetch time — a re-fetch of the same window overwrites the same ID; a new window mints a new one). Stable in exactly the way registers and analytics need.

**`where` — the place key.** `atom` is the join field: a slug resolving to the Bonnie Elsewhere Atom Taxonomy. If no atom exists yet for a location, the layer still ships — `atom: null` with coordinates is legal — but a null atom is a to-do, not a norm, because unjoined items appear on maps yet never in dossiers. `precision` is `exact`, `fuzzed` (wells, fragile sites — fuzzing happens *before* publication, never in the renderer), or `area` (region-level facts like the Disaster Index, which set `atom: null`, `region` only). `region` uses one agreed gazetteer list (draft: the 32 council areas plus a small set of cultural regions — to be fixed in v0.2 and then never casually edited).

**`when` — the time key.** Every item is an event, even "current conditions" (a short window from fetch time to fetch time + cadence). `kind` is `instant` (a sighting, a tend), `window` (summit window, warm space open hours), `recurring` (a well's ritual date, a weekly session — `start` holds the next occurrence), or `countdown` (solstice at a stone — `start` is the event moment, `end` closes its visibility window, typically start + 24h; a fleeting event that renders for its day and then vanishes is correct behaviour, not a bug). Items past their `end` expire from live views automatically; expiry is the contract's answer to the stale-need problem — nothing lingers by default.

**`what` — the type key.** `type` is a two-level vocabulary, `family/specific`: `condition/midge-risk`, `condition/summit-window`, `cause/food-need`, `cause/warm-space`, `culture/event`, `culture/ritual-date`, `culture/alignment`, `mood/index`. The family list is closed (adding one is a contract revision); the specific list is open. `status` is the one-glance value, drawn from a closed set *scoped per family* — `condition`: `good | fair | poor | severe`; `culture`: `upcoming | live | met`; `cause`: `open | urgent | met`; `mood`: `good | fair | poor | severe`. Renderers clamp by family and treat an out-of-family status as invalid. `headline` is a human sentence under 60 characters, written by the layer, so any renderer can display any layer without knowing its payload; headlines never claim safety ("safe" is a banned word — windows and conditions describe weather per published rules, not permission).

## Rules

1. **Join keys are populated at write time, by the fetch script — never inferred by a renderer.** The pipeline that knows the data best does the joining.
2. **Payload is private.** Faces render from the core; only a layer's own face may reach into its payload. This is what keeps layers retirable.
3. **Expired means invisible.** No renderer shows an item past `end`, and no layer past two cadences. Honesty is enforced by the envelope, not by discipline.
4. **Fuzzing is upstream.** Sensitive coordinates are degraded before publication; published JSON is assumed public forever.
5. **The contract only grows by need.** A field enters v0.2 when a second layer needs it, not when it might be nice.

## Retrofit cost (current layers)

BiteForecast: add envelope + keys to its existing per-destination output — small. `munro.json`: already close; wrap results as items, add `atom` and `what` — an hour. Vigil site: alignments API already item-shaped; map countdowns to `when.kind: countdown` — small. Disaster Index: single `area`-precision item — trivial. Everything not yet built inherits the contract for free.

---
*v0.1.2 — drafted mid-scoping, 21 Jul 2026; amended same day after two Hermes executor critiques (per-family status sets; countdown `end` semantics; "safe" banned from headlines; `id` keyed on `when.start` not fetch time; envelope `gap` object for honest absence). Step 0 rulings: atom taxonomy stub of 4 atoms is in scope; `region` uses council areas only for v1. Open questions for v0.2: cultural regions in the gazetteer; naming of the `culture` face.*