#!/usr/bin/env python3
"""
fetch_munro_v2.py — Munro Windows adapter, contract-compliant (v0.1.2)
"Which Munros have a summit window, and how good is it?"

Source: Open-Meteo hourly forecast
Cadence: 2x/day
Writes: src/data/munro-windows.json  (contract-compliant envelope + items)

Accepts optional --query-lat and --query-lon for distance-gating:
  python3 fetch_munro_v2.py --query-lat 58.1975 --query-lon -6.7451
When the nearest canon Munro is >50km from the query location, emits an
envelope-level gap object (honest absence) instead of items. Follows the
Vigil adapter's distance-gate pattern.

Contract compliance verified against ~/projects/glencoe-dossier/docs/layer-contract-v0.1.md
  - Envelope: contract, layer, face, source, cadence_hours, updated_at, disclaimer, items
  - Item: id, where (atom, lat, lon, region, precision), when (start, end, kind), what (type, status, headline), payload
  - id: layer:atom:when.start  →  "munro_windows:bidean-nam-bian:2026-07-25T08:00:00"
  - status: condition family → good | fair | poor | severe (poor/severe unused — absence is the signal)
  - headline: ≤60 chars, no "safe"
  - gap: envelope-level, emitted when the nearest canon Munro is >50km from the query location
"""

import json
import sys
import os
import math
import urllib.request
from datetime import datetime, timezone

# ── Munro canon ──────────────────────────────────────────────
# Self-contained, no config.py dependency. Expand by adding entries.
MUNROS = [
    {"name": "Bidean nam Bian", "slug": "bidean-nam-bian", "lat": 56.643, "lon": -5.029, "height_m": 1150, "region": "highland"},
    {"name": "Buachaille Etive Mòr", "slug": "buachaille-etive-mor", "lat": 56.647, "lon": -4.898, "height_m": 1022, "region": "highland"},
    {"name": "Stob Coire Sgreamhach", "slug": "stob-coire-sgreamhach", "lat": 56.633, "lon": -5.047, "height_m": 1072, "region": "highland"},
    {"name": "Beinn a' Chrùlaiste", "slug": "beinn-a-chrulaiste", "lat": 56.657, "lon": -4.912, "height_m": 857, "region": "highland"},
    {"name": "Ben Nevis", "slug": "ben-nevis", "lat": 56.797, "lon": -5.004, "height_m": 1345, "region": "highland"},
    {"name": "Ben Lawers", "slug": "ben-lawers", "lat": 56.545, "lon": -4.221, "height_m": 1214, "region": "perthshire"},
]

# ── Distance gate ────────────────────────────────────────────
PROXIMITY_LIMIT_KM = 50  # beyond this, emit gap instead of items

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def nearest_munro(lat, lon):
    nearest = None
    best_dist = float('inf')
    for m in MUNROS:
        d = haversine_km(lat, lon, m["lat"], m["lon"])
        if d < best_dist:
            best_dist = d
            nearest = m
    return nearest, best_dist

# ── Thresholds (untuned placeholders) ────────────────────────
WIND_LIMIT_KMH = 50
PRECIP_LIMIT_PCT = 30
VISIBILITY_LIMIT_M = 5000

WALKING_START = 8
WALKING_END = 18

GOOD_HOURS = 6
FAIR_HOURS = 4

OPEN_METEO_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude={lat}&longitude={lon}"
    "&hourly=temperature_2m,precipitation_probability,wind_speed_10m,visibility"
    "&forecast_days=7"
    "&timezone=Europe/London"
)

# ── Helpers ──────────────────────────────────────────────────

def hour_is_good(wind, precip, visibility):
    if wind is None or precip is None or visibility is None:
        return False
    return wind < WIND_LIMIT_KMH and precip < PRECIP_LIMIT_PCT and visibility > VISIBILITY_LIMIT_M


def longest_run(bools):
    best = current = 0
    for b in bools:
        current = current + 1 if b else 0
        best = max(best, current)
    return best


def status_for_run(hours):
    if hours >= GOOD_HOURS:
        return "good"
    if hours >= FAIR_HOURS:
        return "fair"
    return None


def window_end(start_iso, run_hours):
    from datetime import timedelta
    start = datetime.fromisoformat(start_iso)
    end = start + timedelta(hours=run_hours)
    base = end.strftime("%Y-%m-%dT%H:%M:%S")
    tz = end.strftime("%z")
    tz_colon = f"{tz[:3]}:{tz[3:]}"
    return f"{base}{tz_colon}"


def make_headline(run_hours, start_hour):
    return f"{run_hours}-hour window from {start_hour:02d}:00"


# ── Fetch ────────────────────────────────────────────────────

def fetch_munro(munro):
    url = OPEN_METEO_URL.format(lat=munro["lat"], lon=munro["lon"])
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def process_munro(munro):
    """Return list of contract-compliant items for this Munro, or None if fetch failed."""
    raw = fetch_munro(munro)
    if raw is None:
        return None

    hourly = raw.get("hourly", {})
    times = hourly.get("time", [])
    wind = hourly.get("wind_speed_10m", [])
    precip = hourly.get("precipitation_probability", [])
    visibility = hourly.get("visibility", [])

    days = {}
    for i, t in enumerate(times):
        try:
            date_str, time_str = t.split("T")
            hour = int(time_str.split(":")[0])
        except (ValueError, IndexError):
            continue
        if not (WALKING_START <= hour <= WALKING_END):
            continue
        good = hour_is_good(
            wind[i] if i < len(wind) else None,
            precip[i] if i < len(precip) else None,
            visibility[i] if i < len(visibility) else None,
        )
        days.setdefault(date_str, []).append((hour, good))

    items = []
    for date_str in sorted(days.keys()):
        good_flags = [g for _, g in days[date_str]]
        run_hours = longest_run(good_flags)
        status = status_for_run(run_hours)
        if status is None:
            continue

        start_iso = f"{date_str}T{WALKING_START:02d}:00:00+01:00"
        end_iso = window_end(f"{date_str}T{WALKING_START:02d}:00:00+01:00", run_hours)

        items.append({
            "id": f"munro_windows:{munro['slug']}:{date_str}",
            "where": {
                "atom": munro["slug"],
                "lat": munro["lat"],
                "lon": munro["lon"],
                "region": munro["region"],
                "precision": "exact"
            },
            "when": {
                "start": start_iso,
                "end": end_iso,
                "kind": "window"
            },
            "what": {
                "type": "condition/summit-window",
                "status": status,
                "headline": make_headline(run_hours, WALKING_START)
            },
            "payload": {
                "window_hours": run_hours,
                "wind_limit_kmh": WIND_LIMIT_KMH,
                "precip_limit_pct": PRECIP_LIMIT_PCT,
                "visibility_limit_m": VISIBILITY_LIMIT_M
            }
        })

    return items


# ── Main ─────────────────────────────────────────────────────

def main():
    # Parse command-line args for query location
    query_lat = None
    query_lon = None
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--query-lat" and i < len(sys.argv):
            query_lat = float(sys.argv[i + 1])
        elif arg == "--query-lon" and i < len(sys.argv):
            query_lon = float(sys.argv[i + 1])

    now = datetime.now(timezone.utc)

    # Distance-gate: if query location provided, check proximity
    gap = None
    if query_lat is not None and query_lon is not None:
        nearest, dist = nearest_munro(query_lat, query_lon)
        if dist > PROXIMITY_LIMIT_KM:
            gap = {
                "nearest_atom": nearest["slug"],
                "nearest_name": nearest["name"],
                "distance_km": round(dist),
                "next_event": None
            }
            print(f"  ⚠ Nearest Munro is {nearest['name']} ({dist:.0f}km) — beyond {PROXIMITY_LIMIT_KM}km limit, emitting gap")

    # Fetch data for all Munros (only if no gap — if gap, skip fetch entirely)
    all_items = []
    failures = 0

    if gap is None:
        results = [process_munro(m) for m in MUNROS]
        for i, r in enumerate(results):
            if r is None:
                failures += 1
            else:
                all_items.extend(r)

    # Build envelope
    envelope = {
        "contract": "0.1",
        "layer": "munro_windows",
        "face": "conditions",
        "source": "open-meteo",
        "cadence_hours": 12,
        "updated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "disclaimer": "Forecast guidance only. Not a substitute for MWIS, SAIS, or your own judgement.",
        "items": all_items
    }

    if gap is not None:
        envelope["gap"] = gap

    # Also emit gap if ALL Munros failed (backward-compatible with no query-location mode)
    if gap is None and failures == len(MUNROS):
        envelope["gap"] = {
            "reason": "all_fetches_failed",
            "detail": "Open-Meteo unreachable for all Munro locations",
            "checked_at": now.strftime("%Y-%m-%dT%H:%M:%SZ")
        }

    # Write to src/data
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "data")
    os.makedirs(data_dir, exist_ok=True)
    out_path = os.path.join(data_dir, "munro-windows.json")

    with open(out_path, "w") as f:
        json.dump(envelope, f, indent=2)

    if gap:
        print(f"✓ munro: gap emitted ({gap['nearest_name']}, {gap['distance_km']}km) → {out_path}")
    else:
        print(f"✓ munro: {len(all_items)} items across {len(MUNROS) - failures}/{len(MUNROS)} summits → {out_path}")
        if failures > 0:
            print(f"  {failures} summit(s) failed — partial failure, not a coverage gap")

    # Validate contract compliance
    assert "contract" in envelope, "Missing contract version"
    assert "layer" in envelope, "Missing layer name"
    assert "face" in envelope, "Missing face declaration"
    assert "items" in envelope, "Missing items array"
    for item in all_items:
        assert "id" in item, f"Item missing id: {item}"
        assert "where" in item, f"Item missing where: {item['id']}"
        assert "when" in item, f"Item missing when: {item['id']}"
        assert "what" in item, f"Item missing what: {item['id']}"
        assert item["what"]["type"].startswith("condition/"), f"Wrong type: {item['what']['type']}"
        assert item["what"]["status"] in ("good", "fair", "poor", "severe"), f"Bad status: {item['what']['status']}"
        assert len(item["what"]["headline"]) <= 60, f"Headline too long: {item['what']['headline']}"
        assert "safe" not in item["what"]["headline"].lower(), f"'safe' in headline: {item['what']['headline']}"
        assert item["when"]["kind"] == "window", f"Wrong kind: {item['when']['kind']}"
        assert "atom" in item["where"], f"Missing atom: {item['id']}"
    print("  ✓ Contract compliance self-check passed")


if __name__ == "__main__":
    main()