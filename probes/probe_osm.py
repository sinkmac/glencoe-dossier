#!/usr/bin/env python3
"""
probe_osm.py — OSM/Overpass source probe (Probe 2).

Purpose: inventory which OSM tag families are populated near each of the four
atoms, count records per family, check for name:gd (Gaelic) coverage, and
capture raw samples for a hand spot-check of overlap with Canmore.

No auth. Uses the public Overpass instance (overpass-api.de). Respects
etiquette: a proper User-Agent, sequential requests, short timeout, small
output.

Coordinates taken verbatim from src/data/atoms.json (not retyped). Bbox
radii match the repo's existing per-atom radii (fetch_nature.py):
  kirriemuir 10km, tiree 15km, south-uist 20km, auchmithie 8km.
"""

import json
import math
import sys
import time
import urllib.parse
import urllib.request

OVERPASS = "https://overpass-api.de/api/interpreter"
USER_AGENT = "GoodPalantir/0.1 (heritagedata@hes.scot)"

ATOMS = {
    "kirriemuir": {"lat": 56.6735, "lon": -3.0040, "radius_km": 10.0},
    "auchmithie": {"lat": 56.5623, "lon": -2.5836, "radius_km": 8.0},
    "tiree": {"lat": 56.5003, "lon": -6.8950, "radius_km": 15.0},
    "south-uist": {"lat": 57.2393, "lon": -7.3250, "radius_km": 20.0},
}

# Tag families of interest (per the brief).
FAMILIES = ["historic", "natural", "tourism", "amenity", "man_made"]


def bbox(lat, lon, radius_km):
    dlat = radius_km / 111.0
    dlon = radius_km / (111.0 * math.cos(math.radians(lat)))
    return {
        "s": lat - dlat, "w": lon - dlon,
        "n": lat + dlat, "e": lon + dlon,
    }


def overpass(query, retries=2):
    """POST an Overpass QL query, retrying once on transient failure."""
    data = urllib.parse.urlencode({"data": query}).encode()
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(OVERPASS, data=data,
                                         headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            if attempt < retries:
                time.sleep(3)
                continue
            return {"error": str(e)}


def tag_family_query(b, family):
    """All nodes/ways/relations in bbox with the given tag key."""
    return f"""[out:json][timeout:40];
(
  node["{family}"]({b['s']},{b['w']},{b['n']},{b['e']});
  way["{family}"]({b['s']},{b['w']},{b['n']},{b['e']});
  relation["{family}"]({b['s']},{b['w']},{b['n']},{b['e']});
);
out center tags;"""


def name_gd_query(b):
    return f"""[out:json][timeout:40];
(
  node["name:gd"]({b['s']},{b['w']},{b['n']},{b['e']});
  way["name:gd"]({b['s']},{b['w']},{b['n']},{b['e']});
  relation["name:gd"]({b['s']},{b['w']},{b['n']},{b['e']});
);
out center tags;"""


def count_elements(result):
    if "elements" not in result:
        return -1, result.get("error", "no elements key")
    return len(result["elements"]), None


def main():
    print("OSM/Overpass probe\n")
    summary = {}
    for slug, cfg in ATOMS.items():
        b = bbox(cfg["lat"], cfg["lon"], cfg["radius_km"])
        print(f"--- {slug} (bbox s={b['s']:.3f} w={b['w']:.3f} n={b['n']:.3f} e={b['e']:.3f}) ---")
        fam_counts = {}
        for fam in FAMILIES:
            res = overpass(tag_family_query(b, fam))
            n, err = count_elements(res)
            fam_counts[fam] = n
            print(f"  {fam}: {n if n >= 0 else 'ERR ' + str(err)}")
            time.sleep(1.5)  # etiquette: pace requests
        # name:gd coverage
        res = overpass(name_gd_query(b))
        gd_n, gd_err = count_elements(res)
        print(f"  name:gd: {gd_n if gd_n >= 0 else 'ERR ' + str(gd_err)}")
        time.sleep(1.5)
        summary[slug] = {"bbox": b, "families": fam_counts, "name_gd": gd_n}

    # Raw samples: dump a few elements from kirriemuir historic + name:gd for
    # the hand spot-check (overlap with Canmore). Re-query, keep first 3.
    print("\n--- Raw sample (kirriemuir, historic) ---")
    b = bbox(ATOMS["kirriemuir"]["lat"], ATOMS["kirriemuir"]["lon"], ATOMS["kirriemuir"]["radius_km"])
    res = overpass(tag_family_query(b, "historic"))
    for el in (res.get("elements") or [])[:3]:
        print(json.dumps(el, ensure_ascii=False))
    time.sleep(1.5)
    print("\n--- Raw sample (kirriemuir, name:gd) ---")
    res = overpass(name_gd_query(b))
    for el in (res.get("elements") or [])[:3]:
        print(json.dumps(el, ensure_ascii=False))

    with open("probes/osm-summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print("\nWrote probes/osm-summary.json")


if __name__ == "__main__":
    main()
