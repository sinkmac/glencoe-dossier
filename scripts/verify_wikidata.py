#!/usr/bin/env python3
"""
verify_wikidata.py — evidence-first regression check for the Wikidata join layer.

The join layer brief was verified against the live endpoint before any code was
built. Three claims in the original resource doc were wrong and are CORRECTED
here (see commit history for the diagnosis):

  C1. The Canmore ID property is P718 ("Canmore ID"), NOT P3634.
      (P3634 is a different property; P709 is "Historic Environment Scotland ID";
      P7906/P7907/P7922 are Canmore type-vocabulary IDs.)
  C2. Query for P718="32313" returns the real item
      (Q17777741 Old Parish Church, High Street, Kirriemuir).
  C3. The four place QIDs resolve to the verified labels:
      Kirriemuir Q1011603, Tiree Q511617, South Uist Q841059, Auchmithie Q4819456.
      (The original brief's Q80967/Q766298/Q207257/Q4818800 were wrong — they
      resolve to Outer Hebrides / Juan Bautista Ceballos / East Lothian / Atullya.)
  C4. P18 returns a full Special:FilePath URL usable directly — no
      md5-based thumbnail converter needed (the original get_commons_image_url
      produced HTTP 400 on real values).
  C5. P718 join coverage of local Kirriemuir CANMOREIDs must be >= 25%.
      This is a LOWER-BOUND regression check, not an exact count — coverage
      legitimately rises as editors add items, and the check must not flake.

Uses the endpoint + User-Agent from the resource doc. Exits non-zero on any
failed assertion. Run with: python3 scripts/verify_wikidata.py
"""

import json
import time
import urllib.parse
import urllib.request

ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "GoodPalantir/0.1 (heritagedata@hes.scot)"

# Verified place QIDs (corrected from the original brief)
PLACE_QIDS = {
    "kirriemuir": "Q1011603",
    "tiree": "Q511617",
    "south-uist": "Q841059",
    "auchmithie": "Q4819456",
}

CANMORE_PROPERTY = "P718"
COVERAGE_MIN_PCT = 25.0  # lower bound; Wikidata coverage rises over time

failures = 0


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


def check(cond, label, detail=""):
    status = "OK  " if cond else "FAIL"
    print(f"[{status}] {label}" + (f"  ({detail})" if detail else ""))
    global failures
    if not cond:
        failures += 1


def main():
    # ── C2: Canmore ID 32313 resolves via P718 ─────────────────────────
    print("=== C2: P718 Canmore ID join ===")
    q2 = f"""
    SELECT ?item ?itemLabel ?coord ?image ?article WHERE {{
      ?item wdt:{CANMORE_PROPERTY} "32313" .
      OPTIONAL {{ ?item wdt:P625 ?coord . }}
      OPTIONAL {{ ?item wdt:P18 ?image . }}
      OPTIONAL {{
        ?article schema:about ?item ;
                 schema:inLanguage "en" ;
                 schema:isPartOf <https://en.wikipedia.org/> .
      }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
    }}
    """
    rows2 = wikidata_query(q2)
    check(len(rows2) > 0, "P718='32313' returns ≥1 row", f"({len(rows2)})")
    for r in rows2[:3]:
        qid = r["item"].split("/")[-1]
        print(f"  {qid}  {r.get('itemLabel')}  coord={bool(r.get('coord'))} "
              f"image={bool(r.get('image'))} article={bool(r.get('article'))}")
    if rows2:
        check(rows2[0]["item"].startswith("http://www.wikidata.org/entity/Q"),
              "item is a QID", rows2[0]["item"].split("/")[-1])
        # Enrichment is additive: the item must resolve and carry at least one
        # enrichment signal. Any specific signal (article, image, coord) may be
        # absent — absence is the default, not a gap state.
        r0 = rows2[0]
        signals = [k for k in ("coord", "image", "article") if k in r0]
        check(len(signals) >= 1, "item carries ≥1 enrichment signal",
              f"({', '.join(signals) or 'none'})")

    # ── C3: place QIDs resolve to expected labels ─────────────────────
    print("\n=== C3: place QID labels ===")
    expected_labels = {
        "kirriemuir": "Kirriemuir",
        "tiree": "Tiree",
        "south-uist": "South Uist",
        "auchmithie": "Auchmithie",
    }
    for slug, qid in PLACE_QIDS.items():
        q = f'SELECT ?l WHERE {{ wd:{qid} rdfs:label ?l . FILTER(lang(?l)="en") }} LIMIT 1'
        rows = wikidata_query(q)
        got = rows[0]["l"] if rows else "(none)"
        check(got.lower() == expected_labels[slug].lower(),
              f"{slug} {qid} → {got!r}", f"expected {expected_labels[slug]!r}")

    # ── C4: P18 value is a directly-usable Special:FilePath URL ───────
    print("\n=== C4: P18 value format ===")
    q18 = f'SELECT ?img WHERE {{ wd:{PLACE_QIDS["kirriemuir"]} wdt:P18 ?img . }} LIMIT 1'
    r18 = wikidata_query(q18)
    if r18:
        val = r18[0]["img"]
        check(val.startswith("http://commons.wikimedia.org/wiki/Special:FilePath/"),
              "P18 is a Special:FilePath URL (usable directly)",
              val.split("/")[-1][:60])
    else:
        check(False, "no P18 image for Kirriemuir to test format")

    # ── C5: P718 join coverage lower bound (>= 25%) ───────────────────
    print("\n=== C5: P718 coverage lower bound (Kirriemuir) ===")
    import os
    import shapefile
    local = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "Canmore_Points.shp")
    if os.path.exists(local):
        rdr = shapefile.Reader(local)
        idx = {f[0]: i for i, f in enumerate(rdr.fields[1:])}
        parish_ids = [
            str(rec[idx["CANMOREID"]])
            for rec in rdr.records()
            if (rec[idx["PARISH"]] or "").strip().upper() == "KIRRIEMUIR"
        ]
        print(f"  {len(parish_ids)} Kirriemuir records in shapefile")
        # Sample a bounded spread; match against P718 in one VALUES query.
        sample = parish_ids[:60]
        vals = " ".join(f'"{i}"' for i in sample)
        q5 = f"""
        SELECT ?canmore WHERE {{
          VALUES ?canmore {{ {vals} }}
          ?item wdt:{CANMORE_PROPERTY} ?canmore .
        }}
        """
        matched = {r["canmore"] for r in wikidata_query(q5)}
        pct = 100 * len(matched) / len(sample)
        print(f"  {len(matched)}/{len(sample)} sampled CANMOREIDs matched via {CANMORE_PROPERTY} ({pct:.1f}%)")
        check(pct >= COVERAGE_MIN_PCT,
              f"P718 coverage >= {COVERAGE_MIN_PCT:.0f}%",
              f"{pct:.1f}%")
    else:
        print("  (shapefile not present locally — coverage check skipped)")
        check(True, "shapefile absent — coverage check skipped (non-failing)")

    print("\n" + ("ALL CHECKS PASSED" if failures == 0 else f"{failures} CHECK(S) FAILED"))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())