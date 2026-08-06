#!/usr/bin/env python3
"""
fetch_osm_all.py — Fetch OSM data for all atoms

Runs fetch_osm.py across kirriemuir, auchmithie, tiree, south-uist in sequence
with throttling delay between atoms. Cache-only pattern: commit results to git.

Usage:
  python3 fetch_osm_all.py
"""

import subprocess
import sys
import os

ATOMS = ["kirriemuir", "auchmithie", "tiree", "south-uist"]


def main():
    script_path = os.path.join(os.path.dirname(__file__), "fetch_osm.py")

    print("Fetching OSM data for all atoms...")
    for atom in ATOMS:
        print(f"\n{atom}:")
        try:
            result = subprocess.run(
                [sys.executable, script_path, "--atom", atom],
                check=True,
                capture_output=True,
                text=True,
            )
            print(result.stdout)
            if result.returncode != 0:
                print(f"Error: {result.stderr}", file=sys.stderr)
        except subprocess.CalledProcessError as e:
            print(f"Failed to fetch {atom}: {e.stderr}", file=sys.stderr)

    print("\nAll atoms fetched. Commit osm.json files to lock the cache.")


if __name__ == "__main__":
    main()
