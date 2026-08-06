#!/usr/bin/env python3
"""
probe_geonames.py — GeoNames source probe (Probe 1).

Purpose: establish whether GeoNames can serve the language layer (Gaelic
alternate names) and inventory its fields near each of the four atoms.

STATUS: BLOCKED at the auth wall. GeoNames requires a registered username
on every call, and the free tier must be explicitly enabled after
registration. No username is available in this environment (no env var,
no .env, no .netrc, no config token). The brief's prerequisite says: "If
this blocks the probe, report it and stop — do not sign up for an account
or work around it." So this probe records the block and does not proceed.

This script exists so the block is reproducible and verifiable, not to
work around it.
"""

import json
import urllib.error
import urllib.parse
import urllib.request

# Four atoms, coordinates taken verbatim from src/data/atoms.json (not retyped).
ATOMS = {
    "kirriemuir": (56.6735, -3.0040),
    "auchmithie": (56.5623, -2.5836),
    "tiree": (56.5003, -6.8950),
    "south-uist": (57.2393, -7.3250),
}

# findNearbyPlaceName endpoint from the brief's list of interest.
ENDPOINT = "http://api.geonames.org/findNearbyPlaceNameJSON"


def main():
    print("GeoNames probe — auth wall check (no username available)\n")
    for slug, (lat, lon) in ATOMS.items():
        params = {"lat": str(lat), "lng": str(lon), "radius": "10", "maxRows": "5"}
        url = ENDPOINT + "?" + urllib.parse.urlencode(params)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "GoodPalantir/0.1 (heritagedata@hes.scot)"})
            with urllib.request.urlopen(req, timeout=15) as r:
                body = r.read().decode()
                print(f"  {slug}: HTTP {r.status} (unexpected — auth should be required)")
                print(f"    {body[:200]}")
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            print(f"  {slug}: HTTP {e.code} — {body[:200]}")
        except Exception as e:
            print(f"  {slug}: {e}")

    print("\nResult: BLOCKED. GeoNames requires a registered username on every call")
    print("(free tier must be enabled after registration). No username available.")
    print("Per the brief, this probe reports the blocker and stops.")


if __name__ == "__main__":
    main()
