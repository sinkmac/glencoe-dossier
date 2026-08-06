#!/usr/bin/env python3
"""
probe_lidar.py — Scottish Remote Sensing Portal LIDAR coverage probe (Probe 3).

NOT an API for tiles. This probe reads PORTAL/API METADATA ONLY — it does not
download any tile/raster. The brief's 50MB single-file fetch ceiling is
respected: GetCapabilities (small XML) and metadata pages only.

Purpose: establish, per atom, whether LIDAR coverage exists (yes/no), which
phase/format covers it, and the access mechanism + licence.

The WMS GetCapabilities exposes each coverage as a <Layer> with an
EX_GeographicBoundingBox (EPSG:4326 lon/lat footprint). We test each atom's
point against every layer's footprint to determine per-atom coverage.

Coordinates taken verbatim from src/data/atoms.json (not retyped).
"""

import json
import re
import urllib.request

WMS_CAPS = "https://ows.remotesensing.data.gov.scot/geoserver/ows?service=wms&version=1.3.0&request=GetCapabilities"
UA = "GoodPalantir/0.1 (heritagedata@hes.scot)"

ATOMS = {
    "kirriemuir": (56.6735, -3.0040),
    "auchmithie": (56.5623, -2.5836),
    "tiree": (56.5003, -6.8950),
    "south-uist": (57.2393, -7.3250),
}


def get(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode()


def parse_layers(xml):
    """Return [(name, title, {west,east,south,north}), ...] from GetCapabilities."""
    layers = []
    # Split on <Layer ...> ... </Layer>. GeoServer nests layers; we scan top
    # boundaries by matching Layer blocks that directly contain a <Name>.
    for m in re.finditer(r"<Layer[^>]*>(.*?)</Layer>", xml, re.DOTALL):
        block = m.group(1)
        name_m = re.search(r"<Name>(.*?)</Name>", block)
        if not name_m:
            continue
        # geographic footprint
        geo = re.search(
            r"<EX_GeographicBoundingBox>\s*<westBoundLongitude>(.*?)</westBoundLongitude>"
            r"\s*<eastBoundLongitude>(.*?)</eastBoundLongitude>"
            r"\s*<southBoundLatitude>(.*?)</southBoundLatitude>"
            r"\s*<northBoundLatitude>(.*?)</northBoundLatitude>",
            block, re.DOTALL)
        title_m = re.search(r"<Title>(.*?)</Title>", block)
        if geo:
            w, e, s, n = [float(x) for x in geo.groups()]
            layers.append({
                "name": name_m.group(1),
                "title": title_m.group(1) if title_m else "",
                "w": w, "e": e, "s": s, "n": n,
            })
    return layers


def main():
    print("LIDAR coverage probe (metadata only — no tile downloads)\n")
    try:
        xml = get(WMS_CAPS)
    except Exception as e:
        print("BLOCKED: could not fetch GetCapabilities:", e)
        return
    print(f"GetCapabilities fetched: {len(xml):,} chars\n")

    layers = parse_layers(xml)
    print(f"Parsed {len(layers)} layers with geographic footprints\n")

    # Classify dataset families by layer-name patterns (some lidar datasets are
    # named by year/area, e.g. outer-hebrides-2019, not "lidar"):
    def family(name):
        n = name.split(":")[-1].lower()
        if "phase" in name.lower() or re.match(r"^lidar-[1-6]-", n) or "lidar-1-" in n:
            return "phase"
        if "hes" in n:
            return "hes"
        if "outer-hebrides" in n:
            return "outer-hebrides-2019"
        if "orkney" in n:
            return "orkney"
        if "nlp" in n or "national-lidar" in n:
            return "national-programme"
        if "aggregate" in n:
            return "aggregate"
        return "other"

    lidar_layers = [l for l in layers if family(l["name"]) in
                    ("phase", "hes", "outer-hebrides-2019", "orkney",
                     "national-programme", "aggregate")]
    print(f"({len(lidar_layers)} of the {len(layers)} layers are lidar-family)\n")

    for slug, (lat, lon) in ATOMS.items():
        hits = [l for l in lidar_layers if l["w"] <= lon <= l["e"] and l["s"] <= lat <= l["n"]]
        print(f"--- {slug} ({lat}, {lon}) ---")
        if not hits:
            print("  NO lidar layer footprint covers this point")
        else:
            for l in sorted(hits, key=lambda x: x["name"]):
                phase = l["name"].split(":")[-1]
                print(f"  {phase:<45} {l['title']}")
        print()

    out = {
        s: {"layers_covering": [dict(l) for l in
             [x for x in lidar_layers if x["w"] <= ATOMS[s][1] <= x["e"] and x["s"] <= ATOMS[s][0] <= x["n"]]]}
        for s in ATOMS
    }
    with open("probes/lidar-summary.json", "w") as f:
        json.dump(out, f, indent=2)
    print("Wrote probes/lidar-summary.json")


if __name__ == "__main__":
    main()