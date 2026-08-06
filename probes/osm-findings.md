# OSM / Overpass — Findings (Probe 2)

**Date:** 6 Aug 2026
**Repo:** sinkmac/glencoe-dossier
**Script:** `probes/probe_osm.py` (summary: `probes/osm-summary.json`)
**Status:** COMPLETE (partial — see rate-limit blockers below)

---

## 1. Source and access URL

- Public Overpass instance (POST): `https://overpass-api.de/api/interpreter`
- OSM licence/copyright page: `https://www.openstreetmap.org/copyright`
- OSMF API Usage policy: `https://operations.osmfoundation.org/policies/api/`
- Queries were Overpass QL `[out:json]` against a bounding box per atom.

## 2. Auth

**None required.** Overpass is open — no key, no login. Confirmed by successful
unauthenticated queries. Not a blocker.

## 3. Raw sample

Verbatim, unedited (kirriemuir, `historic` — first 3 elements):

```json
{"type": "node", "id": 1663389840, "lat": 56.7326371, "lon": -3.0288281, "tags": {"historic": "memorial", "memorial": "sculpture", "name": "Captain Scott and Dr Wilson Memorial Cairn", "ref:GB:HER:Angus": "NO36SE0004"}}
{"type": "node", "id": 2216941355, "lat": 56.5990287, "lon": -3.1621561, "tags": {"1860name": "Deanfield Bleach Works", "Pont": "no", "Stobie1783": "yes", "designation": "Historic mill", "historic": "archaeological_site", "name": "Deanfield", "source": "OS Six inch 1st series"}}
{"type": "node", "id": 2218451207, "lat": 56.6365632, "lon": -3.1669588, "tags": {"1860name": "Mill of Cumna (Corn)", "Pont": "no", "Stobie1783": "yes", "designation": "Historic mill", "historic": "archaeological_site", "name": "Mill of Cumno", "source": "OS Six inch 1st series"}}
```

`name:gd` sample (kirriemuir bbox, first 3):

```json
{"type": "node", "id": 387099673, "lat": 56.6443013, "lon": -2.888212, "tags": {"alt_name:gd": "Baile Fharfair", "burgh": "royal", "name": "Forfar", "name:ga": "Farfar", "name:gd": "Farfar", "name:sco": "Farfar", "place": "town", "population": "13801", "wikidata": "Q996509"}}
{"type": "node", "id": 471989811, "lat": 56.7438996, "lon": -2.8457875, "tags": {"is_in": "Angus", "name": "Fern", "name:gd": "Feàrn", "old_name": "Fearn", "place": "village"}}
{"type": "node", "id": 1042815076, "lat": 56.5884737, "lon": -3.1625103, "tags": {"name": "Meigle", "name:gd": "Mìgeil", "name:sco": "Miggle", "old_name": "Migdele", "place": "village", "wikidata": "Q1018733"}}
```

Note: `name:gd` values in the raw sample are lowland/Angus examples (Forfar, Fern,
Meigle) — these are English-derived names with Gaelic forms, not naturally
Gaelic-speaking-area names. Worth flagging for the language layer: the *presence*
of `name:gd` is real, but its *quality* varies (some are transliterations).

## 4. Field inventory

Fields that actually appeared on returned elements (observed in raw output):
`type`, `id`, `lat`, `lon`, `center` (ways/relations), `tags`.
Tags observed: `name`, `historic`, `memorial`, `natural`, `tourism`, `amenity`,
`man_made`, `name:gd`, `name:ga`, `name:sco`, `alt_name:gd`, `old_name`,
`ref:GB:HER:Angus`, `designation`, `source`, `place`, `population`,
`population:date`, `is_in`, `burgh`, `wikidata`, `wikipedia`,
`1860name`, `Pont`, `Stobie1783`, `ref:GB:HER:*`.

**`ref:GB:HER:Angus` is a direct Canmore/HER join key** (e.g. `NO36SE0004`) —
this is the overlap signal (see §9).

## 5. Record counts — per atom, per tag family

| Atom | historic | natural | tourism | amenity | man_made | name:gd |
|---|---|---:|---:|---:|---:|---:|
| kirriemuir | 116 | 1940 | *T/O* | *T/O* | 146 | **115** |
| auchmithie | 56 | *T/O* | 57 | 961 | 382 | **19** |
| tiree | 47 | 1669 | 18 | *RL* | 31 | **77** |
| south-uist | **1258** | 2774 | 94 | 286 | 296 | *T/O* |

`*T/O*` = 504 Gateway Timeout; `*RL*` = 429 Too Many Requests (rate-limit — see §10).

## 6. Licence — ODbL (flagged: different from everything else in the cellar)

**OpenStreetMap data is licensed under the Open Data Commons Open Database
License (ODbL) by the OpenStreetMap Foundation.** Not OGL. This is a different
licence from the rest of the cellar (Canmore=OGL, GBIF=CC BY, Wikidata=CC0).

Exact wording from the OSM copyright page (`https://www.openstreetmap.org/copyright`):
> "OpenStreetMap is open data, licensed under the Open Data Commons Open Database License (ODbL)... You are free to copy, distribute, transmit and adapt our data, as long as you credit OpenStreetMap and its contributors. **If you alter or build upon our data, you may distribute the result only under the same license.**"

The ODbL's **share-alike** obligation means any OSM-derived layer data, or the
OSM contribution to a derived layer, must be distributed under ODbL. This is a
**decision, not a finding** — this probe does not assess whether the site can
comply, but the share-alike term is flagged prominently here so a reader
skimming for blockers cannot miss it.

## 7. Rate limits and terms

- **OSMF API Usage policy** (`operations.osmfoundation.org/policies/api/`):
  "Commercial services, or those that seek donations, should be especially
  aware that access may be withdrawn at any point." Also references the
  attribution + licence requirements.
- **Public Overpass instance (overpass-api.de):** no hard published per-minute
  number on the page I reached, but the **observed behaviour in this probe is
  the authoritative evidence**: ~1.5s pacing was NOT enough to avoid
  throttling — the instance returned **504 Gateway Timeout** (queries too
  heavy/slow) and **429 Too Many Requests** under sequential load. Etiquette
  guidance (Overpass wiki) is to pace requests, keep queries small, and use
  `[timeout:...]` — and for production use, a dedicated or self-hosted instance
  is recommended over the public one.

## 8. Gaelic / alternate names

**PRESENT.** `name:gd` appears in 3 of 4 atoms (kirriemuir 115, tiree 77,
auchmithie 19; south-uist timed out). Examples:
- Forfar → `name:gd: Farfar`, `alt_name:gd: Baile Fharfair`
- Fern → `name:gd: Feàrn`
- Meigle → `name:gd: Mìgeil`

This is a **second viable route into the language layer** (GeoNames was blocked,
Probe 1). Caveat: quality varies — some values are English-name transliterations
rather than independently recorded Gaelic, and the densest Gaelic-speaking areas
(south-uist) didn't return (timeout). A real-language-layer adapter would need
to distinguish `name:gd` on naturally-Gaelic placenames from transliterations.

## 9. Overlap with Canmore

**Method:** hand spot-check of the kirriemuir `historic` raw sample (3 elements)
for Canmore/HER reference tags.

**Result: meaningful overlap signal.** 1 of 3 spot-checked kirriemuir historic
nodes carried `ref:GB:HER:Angus` (`NO36SE0004`, Captain Scott memorial) — a
direct HER/Canmore join key. Several others carried `historic: archaeological_site`
with OS-first-edition sourced names (Deanfield, Mill of Cumno) that correspond
to Canmore site types.

**Estimate:** not a hard number (the brief says estimate by hand, no matching
algorithm). The `ref:GB:HER:*` tag is sparse but present; the bigger overlap is
category-level — OSM `historic=` monuments map to Canmore record types. The
OSM layer's distinctive value is therefore the **living present tense**
(paths, benches, slipways, car parks, amenity=961 in auchmithie) rather than
heritage, which Canmore already covers with far greater depth.

## 10. Blockers

- **Transient 504 Gateway Timeout** on several queries (large bboxes: natural/
  tourism/amenity on kirriemuir, natural on auchmithie, name:gd on south-uist).
  The public instance drops or times out heavy queries. Recorded, not worked
  around — the probe retried once then recorded the gap.
- **429 Too Many Requests** on one query (tiree amenity) under sequential load.
- Neither blocks the layer concept; they bound the public instance's usefulness
  for a build-time adapter (would need pacing, smaller bboxes, or a dedicated
  instance).

---

## Bottom line

OSM/Overpass is **fully usable, no auth**, and answers both the brief's open
questions positively:
- **`name:gd` is present** — a real second route into the Gaelic language layer
  (GeoNames was blocked).
- **`ref:GB:HER:*` gives a Canmore overlap signal**, but OSM's distinctive value
  is the living present tense, not heritage.
- **Licence is ODbL, share-alike** — flagged separately from the general
  licence section because it differs from everything else in the cellar and
  carries a distribution obligation. Compliance is a decision, not a finding.
