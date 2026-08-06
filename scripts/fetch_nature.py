#!/usr/bin/env python3
"""
fetch_nature.py — GBIF Nature Layer Adapter, contract v0.1.2

Queries GBIF occurrence records around each atom (bounding box from centroid +
radius), surfaces NOTABLE_SPECIES occurrences, and writes a contract-compliant
nature.json per atom into src/data/<atom>/.

Source: https://api.gbif.org/v1/occurrence/search (REST, no auth). Public
aggregator — records from NatureScot, RSPB, BTO, iNaturalist, museums, etc.

TaxonKey handling (IMPORTANT):
  species are resolved by scientificName against a COMMITTED cache at
  scripts/taxon-keys.json (see resolve_taxon_keys.py). The taxonKey table in
  the original brief was wrong; /species/search returns a key that does NOT
  match occurrence-record speciesKey. The adapter reads the cache and never
  re-resolves at build. Refresh on demand with resolve_taxon_keys.py.

Licence handling (CC BY-NC — the rule most likely to bite):
  Licence lives at the DATASET level, not the record. For each species query we
  collect the contributing datasetKeys and look up each dataset's licence
  (cached per key). Any item whose occurrences include a CC BY-NC dataset is
  flagged carry_cc_bync:true — a commercial (ad-supported) surface MUST drop
  it; a non-commercial surface (Near Me Scotland) may show it. Attribution
  string is on the envelope.

Output contract v0.1.2 (per the nature layer brief):
  envelope: layer, atom, fetched_at, status, items, attribution, gap
  item: id (nature:<atom>:<taxonKey>:<first_seen_date>), name,
        scientific_name, taxon_class, conservation_status, last_recorded,
        occurrence_count, notable, dark_sky_proxy, carry_cc_bync,
        when {tense: present, label: Nature}

Usage:
  python3 fetch_nature.py                    # all atoms
  python3 fetch_nature.py --atom tiree       # single atom
"""

import json
import math
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

GBIF_ENDPOINT = "https://api.gbif.org/v1/occurrence/search"
DATASET_ENDPOINT = "https://api.gbif.org/v1/dataset"
USER_AGENT = "GoodPalantir/0.1 (heritagedata@hes.scot)"
CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "taxon-keys.json")

# Place atom -> (centroid lat, lon, radius_km). Matches the four place pages.
ATOMS = {
    "kirriemuir": (56.673, -3.005, 10.0),
    "tiree": (56.503, -6.877, 15.0),
    "south-uist": (57.270, -7.360, 20.0),
    "auchmithie": (56.543, -2.558, 8.0),
}

# Dark-sky proxy species: bats + owls (used by the Solas layer as a signal).
DARK_SKY_PROXIES = {"barn_owl", "pipistrelle_bat"}

ATTR = ("Occurrence data from GBIF (gbif.org), licensed CC BY 4.0. Individual "
        "dataset licences apply — see GBIF dataset pages for details.")

_licence_cache = {}


def _get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def get_dataset_licence(dataset_key):
    """Fetch (and cache) the licence for a GBIF dataset. Returns 'UNKNOWN' on failure.

    GBIF returns the licence either as an enum code (e.g. 'CC_BY_NC_4_0') or as
    a URL (e.g. 'http://creativecommons.org/licenses/by-nc/4.0/legalcode'). To
    make downstream checks robust to both, normalise the URL form down to the
    enum code here. See the carry_cc_bync verification (6 Aug 2026).
    """
    if dataset_key in _licence_cache:
        return _licence_cache[dataset_key]
    try:
        d = _get(f"{DATASET_ENDPOINT}/{dataset_key}", timeout=15)
        lic = d.get("license", "UNKNOWN") or "UNKNOWN"
        # 'https?://creativecommons.org/licenses/by-nc/4.0/...' -> 'CC_BY_NC_4_0'
        import re
        m = re.search(r"creativecommons\.org/licenses/by-nc/4\.0", lic)
        if m:
            lic = "CC_BY_NC_4_0"
    except Exception:
        lic = "UNKNOWN"
    _licence_cache[dataset_key] = lic
    return lic


def build_bbox(lat, lon, radius_km):
    """Bounding box dict from a centroid and radius."""
    lat_offset = radius_km / 111.0
    lon_offset = radius_km / (111.0 * math.cos(math.radians(lat)))
    return {
        "lat_min": lat - lat_offset,
        "lat_max": lat + lat_offset,
        "lon_min": lon - lon_offset,
        "lon_max": lon + lon_offset,
    }


def query_notable(taxon_key, bbox, year_min=2020, per_page=5):
    """Return occurrence stats for a species in a bbox, or None if absent.

    Returns: {count, last_recorded, iucn, taxon_class, has_cc_bync}
    Reads iucnRedListCategory + taxon class from the returned records, and
    determines whether any contributing dataset is CC BY-NC.
    """
    params = {
        "speciesKey": taxon_key,
        "decimalLatitude": f"{bbox['lat_min']:.4f},{bbox['lat_max']:.4f}",
        "decimalLongitude": f"{bbox['lon_min']:.4f},{bbox['lon_max']:.4f}",
        "hasCoordinate": "true",
        "hasGeospatialIssue": "false",
        "occurrenceStatus": "PRESENT",
        "year": f"{year_min},2026",
        "limit": str(per_page),
    }
    url = GBIF_ENDPOINT + "?" + urllib.parse.urlencode(params)
    try:
        data = _get(url)
    except Exception as e:
        print(f"    ✗ query failed for key {taxon_key}: {e}")
        return None
    results = data.get("results", [])
    count = data.get("count", 0)
    if count == 0:
        return None

    latest = max((r.get("eventDate") or "") for r in results)
    latest = latest.split("T")[0] if latest else None
    iucn = next((r.get("iucnRedListCategory") for r in results if r.get("iucnRedListCategory")), None)
    cls = next((r.get("class") for r in results if r.get("class")), None)
    # Common name for display (fall back to scientific name if absent).
    vernacular = next((r.get("vernacularName") for r in results if r.get("vernacularName")), None)

    # Licence check: any contributing dataset that is CC BY-NC flags the item.
    dataset_keys = {r.get("datasetKey") for r in results if r.get("datasetKey")}
    has_cc_bync = any(get_dataset_licence(k) == "CC_BY_NC_4_0" for k in dataset_keys)

    return {"count": count, "last_recorded": latest, "iucn": iucn,
            "taxon_class": cls, "has_cc_bync": has_cc_bync, "vernacular": vernacular}


def build_atom(slug, cache):
    lat, lon, radius = ATOMS[slug]
    bbox = build_bbox(lat, lon, radius)
    now = datetime.now(timezone.utc).isoformat()

    print(f"  {slug} (lat {lat}, lon {lon}, r {radius:.0f}km)")

    items = []
    for sp_slug, info in cache.items():
        if info.get("status") != "ok" or not info.get("taxonKey"):
            continue
        res = query_notable(info["taxonKey"], bbox)
        if not res:
            continue
        cc_bync = res.get("has_cc_bync", False)
        print(f"    ✓ {info['scientific_name']}: {res['count']:,} occurrences"
              + (" [CC BY-NC dataset present]" if cc_bync else ""))

        items.append({
            "id": f"nature:{slug}:{info['taxonKey']}:{res['last_recorded'] or 'ever'}",
            "name": res["vernacular"] or info["scientific_name"],
            "scientific_name": info["scientific_name"],
            "taxon_class": res["taxon_class"] or "unknown",
            "conservation_status": res["iucn"],
            "last_recorded": res["last_recorded"],
            "occurrence_count": res["count"],
            "notable": True,
            "dark_sky_proxy": sp_slug in DARK_SKY_PROXIES,
            "carry_cc_bync": cc_bync,
            "when": {"tense": "present", "label": "Nature"},
        })

    envelope = {
        "layer": "nature",
        "atom": slug,
        "fetched_at": now,
        "status": "ok",
        "items": items,
        "attribution": ATTR,
        "gap": None if items else {"reason": "no_notable_species", "pointer": "https://gbif.org"},
    }

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "data", slug)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "nature.json")
    with open(out_path, "w") as f:
        json.dump(envelope, f, indent=2)
    print(f"    → {out_path} ({len(items)} items)")
    return items


def main():
    args = sys.argv[1:]
    with open(CACHE_PATH) as f:
        cache = json.load(f)

    slugs = []
    if "--atom" in args:
        i = args.index("--atom")
        slugs.append(args[i + 1])
    else:
        slugs = list(ATOMS.keys())

    total = 0
    for slug in slugs:
        if slug not in ATOMS:
            sys.stderr.write(f"✗ unknown atom {slug!r}\n")
            continue
        total += len(build_atom(slug, cache))
    print(f"\nTotal notable items across {len(slugs)} atom(s): {total}")


if __name__ == "__main__":
    main()
