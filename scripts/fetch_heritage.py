#!/usr/bin/env python3
"""
fetch_heritage.py — Canmore Heritage Layer Adapter, contract v0.1.2

Static (prebuild) adapter. Reads the HES Canmore Points shapefile, filters by
civil parish, converts British National Grid (EPSG:27700) coordinates to WGS84
(EPSG:4326), grades positional confidence from the ACCURACY field, and writes a
contract-compliant heritage.json per atom into src/data/<atom>/.

Source: http://inspire.hes.scot/AtomService/DATA/Canmore_Points.zip
  Canmore_Points.shp (inside the zip), OGL v3, ~313k records.
Update cadence: when HES publishes a new version (~monthly). No runtime
dependency, no auth, no rate limit — this is a build-time filter/conversion.

Output contract v0.1.2 (per the heritage layer brief):
  envelope: layer, atom, fetched_at, status, items, gap, attribution
  item: id (heritage:<atom>:<canmoreid>), name, broadclass[], sitetype[],
        confidence, lat, lon, trove_url, when {tense: past, label: History}

Usage:
  python3 fetch_heritage.py            # build all atoms in ATOM_TO_PARISH
  python3 fetch_heritage.py --atom kirriemuir   # single atom
"""

import json
import os
import sys
import shapefile
from datetime import datetime, timezone
from pyproj import Transformer

# ── Parish join: atom slug → PARISH string (uppercase, exact match) ─────────
# The four current place pages. Extend by adding entries; the field is already
# uppercase in the data so match exactly.
ATOM_TO_PARISH = {
    "kirriemuir":  "KIRRIEMUIR",
    "auchmithie":  "ARBROATH AND ST VIGEANS",
    "tiree":       "TIREE",
    "south-uist":  "SOUTH UIST",
}

SHAPEFILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "Canmore_Points.shp")
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "data")

# ── Coordinate transform: BNG (EPSG:27700) → WGS84 (EPSG:4326) ─────────────
# always_xy=True so the (x, y) = (easting, northing) inputs give (lon, lat).
TRANSFORMER = Transformer.from_crs("EPSG:27700", "EPSG:4326", always_xy=True)

# ── Confidence grading: ACCURACY → three-tier cellar confidence (mechanical) ──
ACCURACY_TO_CONFIDENCE = {
    "NGR given to the nearest 1m":   "HIGH",
    "NGR given to the nearest 10m":  "HIGH",
    "NGR given to the nearest 100m": "MODERATE",
    "NGR given to the nearest 1km":  "LOW",
    "General location":              "LOW",
}
DEFAULT_CONFIDENCE = "LOW"

ATTRIBUTION = (
    "Contains Historic Environment Scotland and Ordnance Survey data "
    "© Historic Environment Scotland – Scottish Charity No. SC045925 "
    "© Crown copyright and database right 2026"
)

# WGS84 bounding box sanity bounds for Scotland (catches unconverted BNG coords).
# If a converted point falls outside these, skip it — BNG-in-WGS84 coords would
# land near the South Atlantic (lon 100000→too big is caught, but keep a guard).
SCOTLAND_LAT = (54.5, 61.0)
SCOTLAND_LON = (-9.0, 0.0)


def split_field(value):
    """Split a comma-separated field, strip whitespace, drop empties."""
    if not value:
        return []
    return [part.strip() for part in str(value).split(",") if part.strip()]


def build_heritage(reader, parish, atom_slug):
    idx = {f[0]: i for i, f in enumerate(reader.fields[1:])}
    get = lambda rec, name: rec[idx[name]]

    items = []
    raw_count = 0
    for rec in reader.records():
        p = get(rec, "PARISH")
        if (p or "").strip().upper() != parish:
            continue
        raw_count += 1

        cid = get(rec, "CANMOREID")
        x = get(rec, "XCOORD")
        y = get(rec, "YCOORD")
        if x is None or y is None:
            # No coordinate — skip rather than emit a North-Sea point.
            continue
        try:
            lon, lat = TRANSFORMER.transform(float(x), float(y))
        except Exception:
            continue
        # Guard: a coordinate that fails Scottish-bounds sanity is bad data.
        if not (SCOTLAND_LAT[0] <= lat <= SCOTLAND_LAT[1] and
                SCOTLAND_LON[0] <= lon <= SCOTLAND_LON[1]):
            continue

        accuracy = get(rec, "ACCURACY") or ""
        confidence = ACCURACY_TO_CONFIDENCE.get(accuracy.strip(), DEFAULT_CONFIDENCE)

        trove_url = get(rec, "URL") or f"https://www.trove.scot/place/{cid}"

        items.append({
            "id": f"heritage:{atom_slug}:{cid}",
            "name": get(rec, "NMRSNAME") or f"Canmore {cid}",
            "broadclass": split_field(get(rec, "BROADCLASS")),
            "sitetype": split_field(get(rec, "SITETYPE")),
            "confidence": confidence,
            "lat": round(lat, 6),
            "lon": round(lon, 6),
            "trove_url": trove_url,
            "when": {"tense": "past", "label": "History"},
        })

    return items


def write_atom(slug, parish):
    """Build and write heritage.json for one atom. Returns (count, error)."""
    reader = shapefile.Reader(SHAPEFILE)
    try:
        items = build_heritage(reader, parish, slug)
    finally:
        reader.close()

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    gap = None
    if not items:
        gap = {
            "reason": "no_records",
            "pointer": "https://www.trove.scot",
        }

    envelope = {
        "layer": "heritage",
        "atom": slug,
        "fetched_at": now,
        "status": "ok" if items else "ok",
        "items": items,
        "gap": gap,
        "attribution": ATTRIBUTION,
    }

    out_dir = os.path.join(DATA_DIR, slug)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "heritage.json")
    with open(out_path, "w") as f:
        json.dump(envelope, f, indent=2, ensure_ascii=False)

    return len(items), out_path


def main():
    atoms = []
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--atom" and i + 1 < len(args):
            atoms.append(args[i + 1])
    if not atoms:
        atoms = list(ATOM_TO_PARISH.keys())

    total = 0
    for slug in atoms:
        if slug not in ATOM_TO_PARISH:
            sys.stderr.write(f"✗ unknown atom {slug!r} (not in ATOM_TO_PARISH)\n")
            sys.exit(1)
        parish = ATOM_TO_PARISH[slug]
        try:
            count, out_path = write_atom(slug, parish)
            total += count
            gap = "(gap: no records)" if count == 0 else ""
            print(f"  ✓ {slug}: {count} heritage records → {out_path} {gap}")
        except Exception as e:
            sys.stderr.write(f"  ✗ {slug}: {e}\n")
            sys.exit(1)

    print(f"  Total: {total} heritage records across {len(atoms)} atom(s)")


if __name__ == "__main__":
    main()