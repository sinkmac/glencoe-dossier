#!/usr/bin/env python3
"""
fetch_osm.py — OSM/Overpass Nature Layer Adapter

Queries OSM/Overpass for amenities, natural features, tourism nodes, and
Gaelic names (`name:gd`) around each atom bounding box. Writes cache-compliant
osm.json per atom.

Source: https://overpass-api.de/api/interpreter (public Overpass QL endpoint,
no auth). Licence: ODbL (share-alike).

Throttling: 2-second delay between atoms. Public instance drops on sequential
heavy queries; gap objects record timeouts honestly.

Usage:
  python3 fetch_osm.py               # all atoms
  python3 fetch_osm.py --atom tiree  # single atom
"""

import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

OVERPASS = "https://overpass-api.de/api/interpreter"
USER_AGENT = "GoodPalantir/0.1 (heritagedata@hes.scot)"
THROTTLE_DELAY = 2.0

# Place atom -> (centroid lat, lon, radius_km). Matches fetch_nature.py.
ATOMS = {
    "kirriemuir": (56.6735, -3.0040, 10.0),
    "tiree": (56.5003, -6.8950, 15.0),
    "south-uist": (57.2393, -7.3250, 20.0),
    "auchmithie": (56.5623, -2.5836, 8.0),
}


def bbox(lat, lon, radius_km):
    """Compute bbox as (south, west, north, east) from centroid + radius."""
    dlat = radius_km / 111.0
    dlon = radius_km / (111.0 * math.cos(math.radians(lat)))
    return {
        "s": lat - dlat,
        "w": lon - dlon,
        "n": lat + dlat,
        "e": lon + dlon,
    }


def overpass_query(query, retry=1):
    """POST Overpass QL query, return parsed JSON or error dict."""
    from urllib import error as urlerror
    data = urllib.parse.urlencode({"data": query}).encode()
    for attempt in range(retry + 1):
        try:
            req = urllib.request.Request(
                OVERPASS, data=data, headers={"User-Agent": USER_AGENT}
            )
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())
        except urlerror.HTTPError as e:
            if e.code == 429:
                return {"gap": "429 Too Many Requests (throttled)"}
            elif e.code == 504:
                return {"gap": "504 Gateway Timeout"}
            raise
        except Exception as e:
            if attempt < retry:
                time.sleep(3)
                continue
            return {"gap": str(e)}


def amenity_query(b):
    """All amenity nodes/ways/relations in bbox."""
    return f"""[out:json][timeout:40];
(
  node["amenity"]({b['s']},{b['w']},{b['n']},{b['e']});
  way["amenity"]({b['s']},{b['w']},{b['n']},{b['e']});
  relation["amenity"]({b['s']},{b['w']},{b['n']},{b['e']});
);
out center tags;"""


def natural_query(b):
    """All natural feature nodes/ways/relations in bbox."""
    return f"""[out:json][timeout:40];
(
  node["natural"]({b['s']},{b['w']},{b['n']},{b['e']});
  way["natural"]({b['s']},{b['w']},{b['n']},{b['e']});
  relation["natural"]({b['s']},{b['w']},{b['n']},{b['e']});
);
out center tags;"""


def tourism_query(b):
    """All tourism nodes/ways/relations in bbox."""
    return f"""[out:json][timeout:40];
(
  node["tourism"]({b['s']},{b['w']},{b['n']},{b['e']});
  way["tourism"]({b['s']},{b['w']},{b['n']},{b['e']});
  relation["tourism"]({b['s']},{b['w']},{b['n']},{b['e']});
);
out center tags;"""


def gaelic_name_query(b):
    """All nodes/ways/relations carrying name:gd (Gaelic name) in bbox."""
    return f"""[out:json][timeout:40];
(
  node["name:gd"]({b['s']},{b['w']},{b['n']},{b['e']});
  way["name:gd"]({b['s']},{b['w']},{b['n']},{b['e']});
  relation["name:gd"]({b['s']},{b['w']},{b['n']},{b['e']});
);
out center tags;"""


def extract_node(elem):
    """Extract (id, name, name_gd, type, tag, lat, lon) from OSM element."""
    tags = elem.get("tags", {})
    lat = elem.get("lat")
    lon = elem.get("lon")
    if lat is None or lon is None:
        # Ways/relations may have center coords; use those
        center = elem.get("center")
        if center:
            lat, lon = center.get("lat"), center.get("lon")
    if lat is None or lon is None:
        return None

    node_id = f"node/{elem['id']}"
    name = tags.get("name", "")
    name_gd = tags.get("name:gd", "")

    # Determine primary tag type (priority: amenity > tourism > natural)
    tag = None
    node_type = None
    if "amenity" in tags:
        node_type = "amenity"
        tag = tags["amenity"]
    elif "tourism" in tags:
        node_type = "tourism"
        tag = tags["tourism"]
    elif "natural" in tags:
        node_type = "natural"
        tag = tags["natural"]

    return {
        "id": node_id,
        "name": name,
        "name_gd": name_gd,
        "type": node_type,
        "tag": tag,
        "lat": lat,
        "lon": lon,
    }


def fetch_atom(atom, lat, lon, radius_km):
    """Fetch all OSM data for a single atom, return osm.json envelope."""
    print(f"  {atom}...", end="", flush=True)

    b = bbox(lat, lon, radius_km)
    fetched_at = datetime.now(timezone.utc).isoformat()
    amenities = []
    gaelic_names = []
    counts = {
        "amenity": 0,
        "natural": 0,
        "tourism": 0,
        "name_gd": 0,
    }
    gaps = []

    # Query 1: Amenities
    res = overpass_query(amenity_query(b))
    if "gap" in res:
        gaps.append(f"amenity: {res['gap']}")
    elif "elements" in res:
        for elem in res["elements"]:
            extracted = extract_node(elem)
            if extracted:
                amenities.append(extracted)
        counts["amenity"] = len(amenities)

    # Query 2: Natural features
    res = overpass_query(natural_query(b))
    if "gap" in res:
        gaps.append(f"natural: {res['gap']}")

    # Query 3: Tourism
    res = overpass_query(tourism_query(b))
    if "gap" in res:
        gaps.append(f"tourism: {res['gap']}")

    # Query 4: Gaelic names (all tags, deduplicate)
    res = overpass_query(gaelic_name_query(b))
    if "gap" in res:
        gaps.append(f"name:gd: {res['gap']}")
    elif "elements" in res:
        seen_ids = set()
        for elem in res["elements"]:
            elem_id = f"node/{elem['id']}"
            if elem_id in seen_ids:
                continue
            seen_ids.add(elem_id)
            tags = elem.get("tags", {})
            if tags.get("name:gd"):
                lat = elem.get("lat")
                lon = elem.get("lon")
                if lat is None or lon is None:
                    center = elem.get("center")
                    if center:
                        lat, lon = center.get("lat"), center.get("lon")
                if lat is not None and lon is not None:
                    gaelic_names.append(
                        {
                            "id": elem_id,
                            "name": tags.get("name", ""),
                            "name_gd": tags["name:gd"],
                        }
                    )
        counts["name_gd"] = len(gaelic_names)

    # Throttle delay before next atom
    time.sleep(THROTTLE_DELAY)

    gap_obj = None
    if gaps:
        gap_obj = " | ".join(gaps)

    print(" ✓")

    return {
        "layer": "osm",
        "atom": atom,
        "fetched": fetched_at,
        "amenities": amenities,
        "gaelic_names": gaelic_names,
        "counts": counts,
        "attribution": "© OpenStreetMap contributors, ODbL",
        "gap": gap_obj,
    }


def main():
    atoms_to_fetch = sys.argv[1:] if len(sys.argv) > 1 else list(ATOMS.keys())
    if len(sys.argv) > 2 and sys.argv[1] == "--atom":
        atoms_to_fetch = [sys.argv[2]]

    data_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "src", "data"
    )

    for atom in atoms_to_fetch:
        if atom not in ATOMS:
            print(f"~ {atom}: unknown atom (skipped)")
            continue

        lat, lon, radius_km = ATOMS[atom]
        result = fetch_atom(atom, lat, lon, radius_km)

        atom_dir = os.path.join(data_dir, atom)
        os.makedirs(atom_dir, exist_ok=True)

        output_path = os.path.join(atom_dir, "osm.json")
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)
        print(f"    → {output_path}")


if __name__ == "__main__":
    main()
