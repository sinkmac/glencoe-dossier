#!/usr/bin/env python3
"""
fetch_wikidata.py — Wikidata join-layer adapter for the heritage dossier.

Reads each atom's heritage.json (CANMOREID per item), batch-queries Wikidata
via the Canmore ID property P718, and writes a wikidata.json join map per atom.

This is a JOIN layer, not a primary source. Enrichment is ADDITIVE and absence
is the default: an item with no P718 match is simply not present in the map —
the heritage item renders exactly as it does today (no image, no summary, no
broken placeholder). Only matched items gain a `wikidata` entry.

Corrected facts (verified against the live SPARQL endpoint — see
verify_wikidata.py and commit history):
  - Canmore ID property is P718, NOT P3634.
  - P18 returns a full Special:FilePath URL usable directly; no md5 thumbnail
    converter (the original get_commons_image_url produced HTTP 400).
  - Place QIDs: kirriemuir Q1011603, tiree Q511617, south-uist Q841059,
    auchmithie Q4819456. (The original brief's QIDs were wrong.)

Coverage ~28% (17/60 Kirriemuir CANMOREIDs). The adapter must therefore not
emit gaps for the ~72% without a match — a bare item is a valid state.

Source: https://query.wikidata.org/sparql (public, no auth, CC0). Queries are
batched (VALUES over sampled ID chunks) to stay well inside the 60s/min limit.
Results are CACHED to src/data/<atom>/wikidata.json at build time — never
queried at runtime.

Usage:
  python3 fetch_wikidata.py                 # all atoms
  python3 fetch_wikidata.py --atom kirriemuir
"""

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "GoodPalantir/0.1 (heritagedata@hes.scot)"

CANMORE_PROPERTY = "P718"          # verified: "Canmore ID"
BATCH_SIZE = 50                     # CANMOREIDs per SPARQL query

# Place atom → Wikidata QID (verified). Used for the notable-people query.
ATOM_QID = {
    "kirriemuir": "Q1011603",
    "tiree": "Q511617",
    "south-uist": "Q841059",
    "auchmithie": "Q4819456",
}

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "data")

ATTRIBUTION = "Data from Wikidata. Wikidata is licensed CC0 — no attribution required, credited as good practice."


def wikidata_query(sparql, tries=4):
    """Run a SPARQL query against Wikidata. Returns list of result dicts."""
    url = ENDPOINT + "?query=" + urllib.parse.quote(sparql)
    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    })
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read())
            return [
                {k: v["value"] for k, v in row.items()}
                for row in data["results"]["bindings"]
            ]
        except urllib.error.HTTPError as e:
            last = e.code
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"query failed after {tries} tries, last HTTP {last}")


def load_heritage_ids(slug):
    """Return the CANMOREIDs in this atom's heritage.json."""
    path = os.path.join(DATA_DIR, slug, "heritage.json")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        env = json.load(f)
    ids = []
    for it in env.get("items", []):
        # heritage ids look like "heritage:kirriemuir:32313"
        cid = it["id"].split(":")[-1]
        ids.append(cid)
    return ids


def _https(url):
    """Normalise a Wikimedia URL to https.

    Wikidata P18 returns http://commons.wikimedia.org/... — on an HTTPS page the
    browser blocks those as mixed content, so every thumbnail silently fails to
    load. Special:FilePath is served over https; force it.
    """
    if url and url.startswith("http://"):
        return "https://" + url[len("http://"):]
    return url


def fetch_canmore_join(chunk):
    """Return {canmore_id: {qid, name, image, coord, article}} for one ID chunk."""
    vals = " ".join(f'"{c}"' for c in chunk)
    sparql = f"""
    SELECT ?item ?itemLabel ?canmore ?image ?coord ?article WHERE {{
      VALUES ?canmore {{ {vals} }}
      ?item wdt:{CANMORE_PROPERTY} ?canmore .
      OPTIONAL {{ ?item wdt:P18 ?image . }}
      OPTIONAL {{ ?item wdt:P625 ?coord . }}
      OPTIONAL {{
        ?article schema:about ?item ;
                 schema:inLanguage "en" ;
                 schema:isPartOf <https://en.wikipedia.org/> .
      }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
    }}
    """
    out = {}
    for row in wikidata_query(sparql):
        cid = row["canmore"]
        entry = {
            "qid": row["item"].split("/")[-1],
            "name": row.get("itemLabel"),
            "image": _https(row.get("image")),  # force https (mixed-content guard)
            "coord": row.get("coord"),           # WKT "Point(lon lat)"
            "article": row.get("article"),
        }
        entry = {k: v for k, v in entry.items() if v is not None}
        # Keep the most complete entry if a Canmore ID appears more than once.
        if cid not in out or len(entry) > len(out[cid]):
            out[cid] = entry
    return out


def fetch_notable_people(qid, limit=20):
    """Notable people born in a place (P19) — additive, may be empty."""
    sparql = f"""
    SELECT ?person ?personLabel ?dob ?occupationLabel ?article WHERE {{
      ?person wdt:P19 wd:{qid} .
      OPTIONAL {{ ?person wdt:P569 ?dob . }}
      OPTIONAL {{ ?person wdt:P106 ?occupation . }}
      OPTIONAL {{
        ?article schema:about ?person ;
                 schema:inLanguage "en" ;
                 schema:isPartOf <https://en.wikipedia.org/> .
      }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
    }}
    ORDER BY ?dob
    LIMIT {limit}
    """
    people = []
    by_qid = {}
    for row in wikidata_query(sparql):
        qid = row["person"].split("/")[-1]
        entry = by_qid.setdefault(qid, {
            "qid": qid,
            "name": row.get("personLabel"),
            "dob": row.get("dob"),
            "occupations": [],
            "article": row.get("article"),
        })
        occ = row.get("occupationLabel")
        if occ and occ not in entry["occupations"]:
            entry["occupations"].append(occ)
        if row.get("article") and not entry["article"]:
            entry["article"] = row["article"]
    # Contract shape: flat fields, occupations merged (P106 is multi-valued).
    for entry in by_qid.values():
        people.append({
            "qid": entry["qid"],
            "name": entry["name"],
            "dob": entry["dob"],
            "occupations": entry["occupations"],
            "article": entry["article"],
        })
    return people


def build_atom(slug):
    """Build and write wikidata.json for one atom. Returns (matched, total, people, path)."""
    ids = load_heritage_ids(slug)
    total = len(ids)

    join = {}
    for i in range(0, len(ids), BATCH_SIZE):
        chunk = ids[i:i + BATCH_SIZE]
        join.update(fetch_canmore_join(chunk))
        time.sleep(0.5)  # polite spacing between batched queries

    people = []
    qid = ATOM_QID.get(slug)
    if qid:
        try:
            people = fetch_notable_people(qid)
        except Exception as e:
            sys.stderr.write(f"  ⚠ {slug}: people query failed ({e}); continuing with join only\n")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    envelope = {
        "layer": "wikidata",
        "atom": slug,
        "source": "wikidata",
        "fetched_at": now,
        "status": "ok",
        "items": join,          # {canmore_id: {qid, name, image, coord, article}}
        "people": people,       # notable people born here (additive, may be [])
        "attribution": ATTRIBUTION,
    }

    out_dir = os.path.join(DATA_DIR, slug)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "wikidata.json")
    with open(out_path, "w") as f:
        json.dump(envelope, f, indent=2, ensure_ascii=False)

    return len(join), total, len(people), out_path


def main():
    atoms = []
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--atom" and i + 1 < len(args):
            atoms.append(args[i + 1])
    if not atoms:
        atoms = list(ATOM_QID.keys())

    grand = {"matched": 0, "total": 0}
    for slug in atoms:
        if slug not in ATOM_QID:
            sys.stderr.write(f"✗ unknown atom {slug!r} (not in ATOM_QID)\n")
            sys.exit(1)
        try:
            matched, total, npeople, out_path = build_atom(slug)
            grand["matched"] += matched
            grand["total"] += total
            pct = 100 * matched / total if total else 0
            print(f"  ✓ {slug}: {matched}/{total} CANMOREIDs joined "
                  f"({pct:.1f}%), {npeople} notable people → {out_path}")
        except Exception as e:
            sys.stderr.write(f"  ✗ {slug}: {e}\n")
            sys.exit(1)

    pct = 100 * grand["matched"] / grand["total"] if grand["total"] else 0
    print(f"  Total: {grand['matched']}/{grand['total']} joined ({pct:.1f}%). "
          f"Unmatched items remain unchanged (absence is the default).")


if __name__ == "__main__":
    main()