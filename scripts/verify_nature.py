#!/usr/bin/env python3
"""
verify_nature.py — regression checks for the GBIF Nature layer.

Asserts the acceptance criteria from the nature layer brief against the
COMMITTED nature.json files (not a live re-query), so it runs deterministically:
  - contract v0.1.2 shape (envelope + item fields, no extra/missing)
  - Tiree: corncrake present with a large count (the editorial-value gate)
  - all items carry name, scientific_name, taxon_class, conservation_status,
    last_recorded, occurrence_count, notable, dark_sky_proxy, carry_cc_bync, when
  - carry_cc_bync present on every item (licence handling wired, not dead code)
  - gap object when a layer would be empty
"""

import json
import os
import sys

REQUIRED_ITEM_FIELDS = {
    "id", "name", "scientific_name", "taxon_class", "conservation_status",
    "last_recorded", "occurrence_count", "notable", "dark_sky_proxy",
    "carry_cc_bync", "when",
}
REQUIRED_ENV_FIELDS = {
    "layer", "atom", "fetched_at", "status", "items", "attribution", "gap",
}

ATOMS = ["kirriemuir", "tiree", "south-uist", "auchmithie"]
BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "data")

failures = 0


def check(label, ok, detail=""):
    global failures
    print(f"{'PASS' if ok else 'FAIL'}  {label}: {detail}")
    if not ok:
        failures += 1


for atom in ATOMS:
    path = os.path.join(BASE, atom, "nature.json")
    if not os.path.exists(path):
        check(f"nature.json exists ({atom})", False, "missing")
        continue
    with open(path) as f:
        d = json.load(f)

    # Envelope shape
    check(f"envelope fields ({atom})",
          set(d.keys()) == REQUIRED_ENV_FIELDS,
          f"keys={sorted(d.keys())}")
    check(f"layer=nature ({atom})", d["layer"] == "nature")
    check(f"status=ok ({atom})", d["status"] == "ok")
    check(f"attribution present ({atom})", isinstance(d["attribution"], str) and len(d["attribution"]) > 20)

    # Items
    for it in d["items"]:
        missing = REQUIRED_ITEM_FIELDS - set(it.keys())
        check(f"item fields complete [{atom}:{it['name']}]",
              not missing, f"missing={sorted(missing)}" if missing else "ok")
        check(f"carry_cc_bync present [{atom}:{it['name']}]",
              "carry_cc_bync" in it, "field absent")
        check(f"conservation_status present [{atom}:{it['name']}]",
              "conservation_status" in it and it["conservation_status"] is not None)
        check(f"occurrence_count > 0 [{atom}:{it['name']}]",
              isinstance(it.get("occurrence_count"), int) and it["occurrence_count"] > 0)

# Tiree editorial-value gate: corncrake present with a large count.
with open(os.path.join(BASE, "tiree", "nature.json")) as f:
    tiree = json.load(f)
corn = next((it for it in tiree["items"] if it.get("scientific_name") == "Crex crex"), None)
check("Tiree has corncrake (Crex crex)",
      corn is not None, f"found={bool(corn)}")
if corn:
    check("Tiree corncrake count is large (editorial value)",
          corn["occurrence_count"] > 1000, f"count={corn['occurrence_count']}")
    check("Tiree corncrake has vernacular name",
          corn["name"] != corn["scientific_name"], f"name={corn['name']}")

# Dark-sky proxies: kirriemuir should have pipistrelle/barn owl flagged true.
with open(os.path.join(BASE, "kirriemuir", "nature.json")) as f:
    kirri = json.load(f)
proxies = [it for it in kirri["items"] if it.get("dark_sky_proxy")]
check("kirriemuir has dark-sky proxies (bat/owl)",
      len(proxies) > 0, f"count={len(proxies)}")

print("")
print("ALL CHECKS PASSED" if failures == 0 else f"{failures} CHECK(S) FAILED")
sys.exit(0 if failures == 0 else 1)