# GeoNames — Findings (Probe 1)

**Date:** 6 Aug 2026
**Repo:** sinkmac/glencoe-dossier
**Script:** `probes/probe_geonames.py`
**Status: BLOCKED** — auth wall, prerequisite unmet. Probe reports and stops per the brief.

---

## 1. Source and access URL

- Endpoint tested: `http://api.geonames.org/findNearbyPlaceNameJSON`
- Also of interest per brief: `findNearby`, `search` (same API host, same auth requirement)
- API documentation: GeoNames web services (username required on every call)

## 2. Auth

**Required — registered username on every call.** The free tier must be
explicitly enabled after registration. **Blocked the probe.**

No GeoNames username exists in this environment — confirmed absent from:
- environment variables (`env | grep -i geonames` → none)
- `~/projects/glencoe-dossier/.env*` (no .env files present)
- `~/.netrc` (absent)
- config tokens / project config (none found)

Per the brief's prerequisite — *"If this blocks the probe, report it and stop —
do not sign up for an account or work around it"* — the probe stops here. No
account was created, no workaround attempted.

## 3. Raw sample

The block is reproducible and identical across all four atoms. Verbatim HTTP
401 response body (kirriemuir, representative):

```
{"status":{"message":"Please add a username to each call in order for geonames to be able to identify the calling application and count the credits usage.","value":10}}
```

All four atoms returned the same `HTTP 401`, `status.value: 10`.

## 4. Field inventory

**None obtained.** No records could be retrieved behind the auth wall, so no
field inventory is possible from live data. No claim is made about fields
the documentation asserts but the live source was not reachable to confirm.

## 5. Record counts

**None.** All four atoms blocked at HTTP 401. No counts obtainable.

## 6. Licence

**Not reached.** The licence terms live on the GeoNames site / data download
pages, which were not reachable as part of this probe (auth wall on the API,
and this probe did not access the licence page). Recorded as not-assessed.

## 7. Rate limits and terms

**Not reached.** GeoNames free-tier daily/hourly credit limits are published
on the site after registration. This probe did not register, so the limits
were not independently confirmed. Recorded as not-assessed.

## 8. Gaelic / alternate names

**Not assessed.** This was the point of the probe — whether `alternateNames`
carries Gaelic forms. It could not be evaluated behind the auth wall. No
claim either way.

## 9. Overlap with Canmore

**Not assessed.** No GeoNames records were obtainable.

## 10. Blockers

- **Primary:** GeoNames requires a registered username (free tier must be
  explicitly enabled after registration). No username available in this
  environment. The brief explicitly forbids signing up or working around —
  so the probe stopped at the wall.
- This is a blocker recorded, not routed around. A future probe can unblock
  by obtaining a GeoNames username (Sink decision) and re-running
  `probe_geonames.py`.

---

## Bottom line

GeoNames is **not usable as-is** for the language-layer probe without a
registered username. The Gaelic-alternate-name question it was meant to
answer remains open pending either (a) a GeoNames username, or (b) another
source. OSM/Overpass (Probe 2) remains a viable second route into the
language layer and was not blocked by this — see `probe-osm-findings.md`.
