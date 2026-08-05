#!/usr/bin/env python3
import json, sys

DATA = "src/data"
fails = []

def check(cond, msg):
    print(("  OK  " if cond else "  FAIL ") + msg)
    if not cond:
        fails.append(msg)

# -- Kirriemuir --
k = json.load(open(f"{DATA}/kirriemuir/heritage.json"))
print("=== KIRRIEMUIR ===")
check(len(k["items"]) == 452, f"count {len(k['items'])} (~460 expected)")
check(k["atom"] == "kirriemuir", "atom == kirriemuir")
check(k["layer"] == "heritage", "layer == heritage")
check(k["gap"] is None, "gap is null")
check("attribution" in k and "Historic Environment Scotland" in k["attribution"], "attribution present at envelope")
check("Crown copyright and database right 2026" in k["attribution"], "attribution has year + OGL")

rec = next((i for i in k["items"] if i["id"] == "heritage:kirriemuir:32313"), None)
check(rec is not None, "CANMOREID 32313 present")
if rec:
    check(rec["name"] == "KIRRIEMUIR, HIGH STREET, OLD PARISH CHURCH", f"name correct ({rec['name'][:40]})")
    check(rec["confidence"] == "HIGH", f"32313 confidence HIGH ({rec['confidence']})")
    check("RELIGIOUS RITUAL AND FUNERARY" in rec["broadclass"], "broadclass has RELIGIOUS RITUAL AND FUNERARY")
    print(f"      32313 lat/lon: {rec['lat']}, {rec['lon']}")

lats = [i["lat"] for i in k["items"]]
lons = [i["lon"] for i in k["items"]]
check(all(56.5 <= la <= 57.0 for la in lats), f"all lat in 56.5-57.0 (range {min(lats):.3f}-{max(lats):.3f})")
check(all(-3.2 <= lo <= -2.8 for lo in lons), f"all lon in 2.8-3.2W (range {min(lons):.3f}-{max(lons):.3f})")
check(all(i["confidence"] in ("HIGH", "MODERATE", "LOW") for i in k["items"]), "all items have valid confidence grade")
conf = {}
for i in k["items"]:
    conf[i["confidence"]] = conf.get(i["confidence"], 0) + 1
print(f"    confidence dist: {conf}")
cids = [i["id"] for i in k["items"]]
check(len(cids) == len(set(cids)), "no duplicate ids")

# -- Tiree --
t = json.load(open(f"{DATA}/tiree/heritage.json"))
print("\n=== TIREE ===")
check(len(t["items"]) == 539, f"count {len(t['items'])} (~544 expected)")
sk = next((i for i in t["items"] if "SKERRYVORE" in i["name"]), None)
check(sk is not None, "TIREE SKERRYVORE LIGHTHOUSE present")
if sk:
    check("MARITIME" in sk["broadclass"], f"included (not filtered) broadclass: {sk['broadclass']}")
    check(sk["id"].startswith("heritage:tiree:"), f"id {sk['id']}")
    print(f"    Skerryvore lat/lon: {sk['lat']}, {sk['lon']}")

print("\n" + ("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURE(S): {fails}"))
sys.exit(1 if fails else 0)