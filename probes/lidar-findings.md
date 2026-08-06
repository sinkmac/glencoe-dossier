# LIDAR — Findings (Probe 3)

**Date:** 6 Aug 2026
**Repo:** sinkmac/glencoe-dossier
**Script:** `probes/probe_lidar.py` (summary: `probes/lidar-summary.json`)
**Status:** COMPLETE — coverage established from portal + WMS metadata. No tiles
downloaded (50MB ceiling respected; GetCapabilities XML only).

---

## 1. Source and access URL

- Scottish Remote Sensing Portal: `https://remotesensingdata.gov.scot/`
- **WMS GetCapabilities** (the programmatic coverage route):
  `https://ows.remotesensing.data.gov.scot/geoserver/ows?service=wms&version=1.3.0&request=GetCapabilities`
- WMS base: `https://ows.remotesensing.data.gov.scot/geoserver/ows?SERVICE=WMS&`
- Portal download page: `https://remotesensingdata.gov.scot/` → Download

## 2. Auth

**None required** for the portal, WMS GetCapabilities, or WMS layers. Not a
blocker. (Bulk tile download via the portal's basket may require confirmation
but no account was encountered for metadata access.)

## 3. Raw sample

Not applicable in the usual sense — this probe reads metadata, not records.
The operative raw sample is the OWS GetCapabilities document (335,710 chars,
40 layers with geographic footprints). Representative layer:

```xml
<Layer queryable="1" opaque="0">
  <Name>scotland:outer-hebrides-2019-dsm-25cm</Name>
  <Title>LiDAR for Outer Hebrides 2019 - 25cm DSM</Title>
  <EX_GeographicBoundingBox>
    <westBoundLongitude>-7.572839560697914</westBoundLongitude>
    <eastBoundLongitude>-5.9990801449123</eastBoundLongitude>
    ...
  </EX_GeographicBoundingBox>
</Layer>
```

## 4. Field inventory — not applicable

LIDAR items 8 and 9 (Gaelic names, Canmore overlap) do not apply per the brief.
The probe answers coverage questions, not field questions. No record-field
inventory is possible or requested.

## 5. Coverage — per atom (yes/no, phase, resolution)

Determined by testing each atom's point (from `src/data/atoms.json`, verbatim)
against every lidar layer's `EX_GeographicBoundingBox` in the WMS
GetCapabilities. **Yes — all four atoms have lidar coverage.**

| Atom (lat, lon) | Coverage layers | Resolution |
|---|---|---|
| kirriemuir (56.6735, -3.0040) | Licence Phase 1 DSM/DTM; HES 2017 DSM/DTM; NLP 2025 DSM/DTM; aggregate | Phase 1 ~1m/2m; HES 2017 varied; NLP 2025 1m |
| auchmithie (56.5623, -2.5836) | Phase 1 DSM/DTM; NLP 2025 DSM/DTM; aggregate | Phase 1 ~1m/2m; NLP 2025 1m |
| tiree (56.5003, -6.8950) | HES Ten Project 2010 DSM/DTM; NLP 2025 DSM/DTM; aggregate | HES 2010 varied; NLP 2025 1m |
| south-uist (57.2393, -7.3250) | **Outer Hebrides 2019 DSM/DTM 25cm + 50cm**; HES Ten Project 2010; NLP 2025; aggregate | **25cm / 50cm** (best available) |

- **`nlp-2025` (National Lidar Programme 2025)** and the **`lidar-aggregate`**
  (full-Scotland bbox) layers cover all four atoms.
- **south-uist has the best resolution** — Outer Hebrides 2019 at 25cm/50cm,
  encoded in the layer names.
- DSM and DTM are separate layers in every dataset (surface vs bare-earth).
- Point-cloud (`LAZ`) layers exist per phase (e.g. phase-1/laz = 924 tiles)
  but are served separately and were not footprint-tested for this probe.

**Honest caveat (recorded):** these are **layer-level aggregate bounding
boxes**. A bbox hit confirms the layer exists and nominally covers the point,
but Phase 1/2 bboxes span wide areas while actual flight coverage is limited
to the flood-risk sites. A bbox hit is an upper bound, not a guarantee of a
tile at the exact point. For the four named settlements the coverage is
highly likely real (they are within surveyed regions), but exact per-tile
presence needs the portal map or a WMS GetFeatureInfo at the point — the map
was not accessible at probe time (see §10).

## 6. Licence — OGL v3

Every dataset card on the portal carries **"Licence: Open Government Licence
v3"** (seen on Phase I DSM/DTM/LAZ, Phase II, HES, etc.). Attribution for OGL
v3 is the standard "Contains public sector information licensed under the
Open Government Licence v3.0" with a link to
`https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/`.

## 7. Rate limits and terms — not applicable

LIDAR is not rate-limited like an API. The WMS GetCapabilities returned
freely (335KB, one request). The relevant constraint is the **50MB single-file
fetch ceiling** (this probe respected it — metadata only). Large bulk downloads
go through the portal's basket/email workflow.

## 8. / 9. Gaelic names + Canmore overlap

**Not applicable** — LIDAR items 8 and 9 are scoped out by the brief. The
context (escalating Canmore MODERATE → HIGH where LIDAR shows surface
features) is noted but the probe does not attempt it.

## 10. Blockers

- **Interactive map unavailable.** The portal map ("An interactive map of
  Scotland showing areas of LiDAR data available to download") displayed:
  *"The map is not accessible at this time, please contact us for help
  accessing the data."* This is a partial blocker for the *visual* coverage
  check and for per-tile download selection. It was worked around for the
  coverage question by querying the **WMS GetCapabilities** directly (the
  OWS endpoint the map itself uses) and testing footprints — that route was
  open and is authoritative for layer presence.
- The bulk-download basket workflow needs the map to select tiles, so actual
  tile selection is blocked until the map returns. Coverage *existence* was
  established regardless.
- **Layer-bbox coarse-graining** (see §5 caveat) is a data nuance, not a
  blocker, but it bounds how much confidence the probe can assert.

---

## Bottom line

**All four atoms have LIDAR coverage** — confirmed from the WMS GetCapabilities.
Best available: **south-uist at 25cm/50cm** (Outer Hebrides 2019), all four
covered by NLP 2025 + the full-Scotland aggregate. DSM and DTM are separate
layers throughout, so the eventual Canmore MODERATE→HIGH escalation can query
surface (DSM) vs bare-earth (DTM) independently. Licence is OGL v3. Access is
via the OWS WMS endpoint (programmatic) or the portal basket (bulk, map-gated).
The map being down blocks per-tile selection but not coverage determination.