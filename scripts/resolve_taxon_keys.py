#!/usr/bin/env python3
"""
resolve_taxon_keys.py — resolve correct GBIF taxonKeys for the NOTABLE_SPECIES
dict by querying actual occurrence records, and cache the result.

WHY: the taxonKey table in the original nature-layer brief was wrong (corncrake
key 404'd; chough/red_kite/otter keys resolved to the wrong species). GBIF has
multiple key spaces — species/search returns a taxonomy key that does NOT match
the speciesKey that occurrence records actually carry. The reliable method is
to query occurrences by scientificName and read the speciesKey from a real
returned record.

This is an ON-DEMAND resolver (local-run-and-commit model, same as the shapefile
and Wikidata cache). It runs when you want it refreshed, not on every build:

  python3 resolve_taxon_keys.py            # resolve all species, write cache
  python3 resolve_taxon_keys.py --species corncrake   # one species

Writes the cache to scripts/taxon-keys.json (tracked/committed). The nature
adapter (fetch_nature.py) reads this cache; it does not re-resolve at build.

Cache shape:
  { "<slug>": { "scientific_name": "...", "taxonKey": <int>, "resolved_at": "...", "status": "ok"|"not_found" } }
"""

import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ENDPOINT = "https://api.gbif.org/v1/occurrence/search"
USER_AGENT = "GoodPalantir/0.1 (heritagedata@hes.scot)"
CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "taxon-keys.json")

# slug -> scientific name. The brief's dict carried WRONG keys for several of
# these — names are the reliable join key; keys are resolved here.
NOTABLE_SPECIES = {
    "corncrake": "Crex crex",
    "red_kite": "Milvus milvus",
    "otter": "Lutra lutra",
    "red_squirrel": "Sciurus vulgaris",
    "capercaillie": "Tetrao urogallus",
    "golden_eagle": "Aquila chrysaetos",
    "white_tailed_eagle": "Haliaeetus albicilla",
    "puffin": "Fratercula arctica",
    "chough": "Pyrrhocorax pyrrhocorax",
    "red_necked_phalarope": "Phalaropus lobatus",
    "barn_owl": "Tyto alba",
    "pipistrelle_bat": "Pipistrellus pipistrellus",
}


def _get(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def resolve_species(scientific_name: str):
    """Return the real speciesKey for a species by reading a returned record."""
    params = {
        "scientificName": scientific_name,
        "hasCoordinate": "true",
        "hasGeospatialIssue": "false",
        "occurrenceStatus": "PRESENT",
        "limit": "3",
    }
    url = ENDPOINT + "?" + urllib.parse.urlencode(params)
    data = _get(url)
    keys = {r.get("speciesKey") for r in data.get("results", []) if r.get("speciesKey")}
    if not keys:
        return None, data.get("count", 0)
    # Prefer the most common key among returned records.
    from collections import Counter
    counts = Counter(r.get("speciesKey") for r in data.get("results", []) if r.get("speciesKey"))
    return counts.most_common(1)[0][0], data.get("count", 0)


def main():
    args = sys.argv[1:]
    only = None
    if "--species" in args:
        i = args.index("--species")
        only = args[i + 1]

    # Load existing cache if present
    cache = {}
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH) as f:
            cache = json.load(f)

    species = {only: NOTABLE_SPECIES[only]} if only else NOTABLE_SPECIES

    for slug, sci in species.items():
        try:
            key, count = resolve_species(sci)
            if key:
                cache[slug] = {
                    "scientific_name": sci,
                    "taxonKey": key,
                    "occurrence_count": count,
                    "resolved_at": datetime.now(timezone.utc).isoformat(),
                    "status": "ok",
                }
                print(f"  ✓ {slug}: {sci} -> taxonKey {key} (N={count:,} occurrences)")
            else:
                cache[slug] = {
                    "scientific_name": sci,
                    "taxonKey": None,
                    "occurrence_count": 0,
                    "resolved_at": datetime.now(timezone.utc).isoformat(),
                    "status": "not_found",
                }
                print(f"  ✗ {slug}: {sci} -> no records found")
        except Exception as e:
            print(f"  ✗ {slug}: {sci} -> error: {e}")
            cache[slug] = {
                "scientific_name": sci,
                "taxonKey": None,
                "occurrence_count": 0,
                "resolved_at": datetime.now(timezone.utc).isoformat(),
                "status": "error",
            }

    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2)
    print(f"\nCache written to {CACHE_PATH}")


if __name__ == "__main__":
    main()
