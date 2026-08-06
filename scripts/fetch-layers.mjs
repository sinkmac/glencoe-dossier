// Prebuild script: fetches live layer data from adapter endpoints
// and writes contract-compliant JSON to src/data/ for the static build.
// Supports multiple locations (Glencoe, Callanish).
// Runs automatically before `npm run build` via the "prebuild" script.

import { execSync } from 'node:child_process';
import { writeFileSync, readFileSync, mkdirSync, existsSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const DATA_DIR = resolve(__dirname, '..', 'src', 'data');

/** Locations to fetch data for */
const LOCATIONS = {
  glencoe: { lat: 56.680, lon: -5.110, label: 'Glencoe' },
  callanish: { lat: 58.1975, lon: -6.7451, label: 'Callanish' }
};

/** Build endpoint URLs for a given location */
function endpoints(lat, lon) {
  return {
    biteforecast: `https://biteforecast.scot/api/layer/forecast?lat=${lat}&lon=${lon}`,
    vigil: `https://standing-stones-vigil.netlify.app/api/layer/vigil?lat=${lat}&lon=${lon}`
  };
}

/**
 * Transform the new /api/layer/vigil response into the dossier's internal
 * vigil contract shape that the renderer consumes.
 *
 * The standing-stones endpoint returns items shaped
 *   { id, name, location, alignment, register, when:{tense,label} }
 * with NO `what` object. The Glencoe renderer (src/routes/+page.svelte) builds
 * sections from item.what.type and renders item.what.headline/status + a
 * countdown when.kind — so the raw response must be mapped here, at the fetch
 * layer, rather than passed through. Doing it here (not in the renderer) keeps
 * the renderer unchanged and keeps the adaptation at the data boundary.
 */
function transformVigil(data) {
  const now = new Date();
  const mapped = {
    contract: '0.1',
    layer: 'vigil_alignments',
    face: 'culture',
    source: 'standing-stones-canon',
    cadence_hours: 24,
    updated_at: now.toISOString(),
    disclaimer: 'Alignment data based on published archaeoastronomy research. Dates are astronomical, not meteorological.',
    items: (data.items || []).map(it => {
      const slug = (it.id || '').replace(/^vigil:/, '');
      const typeLabel = (it.alignment?.type || '').replace(/_/g, ' ');
      const start = it.alignment?.next_date ? `${it.alignment.next_date}T12:00:00Z` : now.toISOString();
      const end = new Date(new Date(start).getTime() + 24 * 60 * 60 * 1000).toISOString();
      return {
        id: it.id,
        where: {
          atom: slug,
          lat: it.location?.lat,
          lon: it.location?.lon,
          region: (it.location?.region || '').toLowerCase().replace(/\s+/g, '-'),
          precision: 'exact'
        },
        when: { start, end, kind: 'countdown' },
        what: {
          type: 'culture/alignment',
          status: 'upcoming',
          headline: `${typeLabel} at ${it.name}`
        },
        payload: {
          alignmentType: it.alignment?.type,
          nextDate: it.alignment?.next_date,
          daysUntil: it.alignment?.days_until,
          event: it.alignment?.event,
          windowDescription: it.alignment?.window_description,
          register: it.register,
          distanceKm: it.location?.distance_km
        }
      };
    })
  };
  // Map the gap object (new shape: reason/pointer) to the renderer's shape.
  if (data.gap) {
    mapped.gap = {
      reason: data.gap.reason || 'no_sites_in_radius',
      pointer: data.gap.pointer || 'https://standing-stones-vigil.netlify.app'
    };
  } else {
    mapped.gap = null;
  }
  return mapped;
}

/** Fetch a single endpoint and write to file */
async function fetchLayer(key, url, filePath) {
  const response = await fetch(url, {
    headers: { 'Accept': 'application/json' },
    signal: AbortSignal.timeout(15000)
  });
  if (!response.ok) {
    throw new Error(`${key} returned ${response.status}: ${response.statusText}`);
  }
  const data = await response.json();
  // Vigil endpoint returns the new layer shape; map to the dossier contract.
  const out = key === 'vigil' ? transformVigil(data) : data;
  writeFileSync(filePath, JSON.stringify(out, null, 2));
  const itemCount = out.items?.length || 0;
  const hasGap = out.gap ? ` gap:${out.gap.reason || out.gap.nearest_name || out.gap.nearest_atom}` : '';
  console.log(`  ✓ ${key}: ${itemCount} items${hasGap}`);
}

/** Run the Munro Python adapter for a given location */
function runMunro(lat, lon, outDir) {
  const scriptPath = resolve(__dirname, 'fetch_munro_v2.py');
  const munroOut = resolve(outDir, 'munro-windows.json');
  const cmd = `python3 "${scriptPath}" --query-lat ${lat} --query-lon ${lon}`;
  const output = execSync(cmd, { timeout: 30000, encoding: 'utf-8' });
  // Script writes to the default path; copy to location-specific path
  const defaultPath = resolve(DATA_DIR, 'munro-windows.json');
  const data = JSON.parse(readFileSync(defaultPath, 'utf-8'));
  writeFileSync(munroOut, JSON.stringify(data, null, 2));
  const itemCount = data.items?.length || 0;
  const hasGap = data.gap ? ` gap:${data.gap.nearest_name || data.gap.nearest_atom}` : '';
  console.log(`  ✓ munro: ${itemCount} items${hasGap}`);
  return output.trim();
}

/**
 * Run the Heritage Python adapter (Canmore Points shapefile, static source).
 *
 * Local-run-and-commit model: the adapter runs on a machine that has the
 * 35MB shapefile + pyshp/pyproj, and the resulting heritage.json is COMMITTED.
 * On a deploy builder (Netlify) those prerequisites are NOT present — that is
 * the expected state, not a failure, because the committed JSON is the
 * authoritative artifact and the shapefile should never be shipped to a build
 * box. So:
 *   - shapefile missing (-or- python deps missing)  → graceful skip, return 0
 *   - shapefile + deps present, but the run errors  → real failure, return 1
 */
function runHeritage() {
  const scriptPath = resolve(__dirname, 'fetch_heritage.py');
  const shapefilePath = resolve(__dirname, 'data', 'Canmore_Points.shp');

  // Prereq 1: shapefile present locally? If not, skip (committed JSON serves).
  if (!existsSync(shapefilePath)) {
    console.log('  ~ heritage: Canmore_Points.shp not present — using committed heritage.json (local-run model)');
    return 0;
  }

  // Prereq 2: python has pyshp + pyproj? Probe before running so a missing dep
  // is a clean skip, not an error-catch false failure.
  let depsOk = true;
  try {
    execSync('python3 -c "import shapefile, pyproj"', { stdio: 'pipe' });
  } catch {
    depsOk = false;
  }
  if (!depsOk) {
    console.log('  ~ heritage: pyshp/pyproj not installed for python3 — using committed heritage.json (local-run model)');
    return 0;
  }

  // Prereqs all present — actually run the adapter.
  try {
    const output = execSync(`python3 "${scriptPath}"`, { timeout: 120000, encoding: 'utf-8' });
    console.log(output.trim().split('\n').map(l => `  ${l}`).join('\n'));
    return 0;
  } catch (e) {
    console.error(`  ✗ heritage adapter failed: ${e.message}`);
    return 1;
  }
}

/**
 * Run the Wikidata join adapter (public SPARQL endpoint, build-time cache).
 * Unlike heritage, this queries a live public endpoint — no local prereqs —
 * so it always runs. Results are written to src/data/<atom>/wikidata.json and
 * committed; absence of a match is the default, not a failure.
 */
function runWikidata() {
  const scriptPath = resolve(__dirname, 'fetch_wikidata.py');
  try {
    const output = execSync(`python3 "${scriptPath}"`, { timeout: 180000, encoding: 'utf-8' });
    console.log(output.trim().split('\n').map(l => `  ${l}`).join('\n'));
    return 0;
  } catch (e) {
    console.error(`  ✗ wikidata adapter failed: ${e.message}`);
    return 1;
  }
}

/**
 * Run the GBIF Nature adapter (live public GBIF occurrence endpoint).
 * Reads the COMMITTED taxon-keys.json cache (resolved on demand by
 * resolve_taxon_keys.py) — it never re-resolves taxonKeys at build. Writes
 * src/data/<atom>/nature.json. Same model as runWikidata: live endpoint, no
 * local prereqs, unconditional.
 */
function runNature() {
  const scriptPath = resolve(__dirname, 'fetch_nature.py');
  try {
    const output = execSync(`python3 "${scriptPath}"`, { timeout: 180000, encoding: 'utf-8' });
    console.log(output.trim().split('\n').map(l => `  ${l}`).join('\n'));
    return 0;
  } catch (e) {
    console.error(`  ✗ nature adapter failed: ${e.message}`);
    return 1;
  }
}

/**
 * OSM/Overpass layer (live public endpoint, committed cache-only at build).
 * Reads from committed src/data/<atom>/osm.json files (refreshed on demand by
 * fetch_osm.py / fetch_osm_all.py). Does not fetch at build time to avoid
 * throttling against the public Overpass instance.
 */
function runOSM() {
  // OSM cache is committed; no fetch at build time.
  // To refresh: python3 scripts/fetch_osm_all.py, then commit osm.json files.
  console.log('  (cache-only — no live fetch at build time)');
  return 0;
}

/** Fetch all layers for a single location */
async function fetchLocation(slug, { lat, lon, label }) {
  console.log(`\n--- ${label} ---`);
  const outDir = resolve(DATA_DIR, slug);
  mkdirSync(outDir, { recursive: true });

  // Fetch JS endpoints
  const eps = endpoints(lat, lon);
  const results = await Promise.allSettled([
    fetchLayer('biteforecast', eps.biteforecast, resolve(outDir, 'biteforecast-midge.json')),
    fetchLayer('vigil', eps.vigil, resolve(outDir, 'vigil-alignments.json'))
  ]);

  let failures = 0;
  for (const r of results) {
    if (r.status === 'rejected') {
      console.error(`  ✗ ${r.reason}`);
      failures++;
    }
  }

  // Run Munro adapter
  try {
    runMunro(lat, lon, outDir);
  } catch (e) {
    console.error(`  ✗ munro adapter failed: ${e.message}`);
    failures++;
  }

  return failures;
}

async function main() {
  mkdirSync(DATA_DIR, { recursive: true });
  let totalFailures = 0;

  // --skip-wikidata: skip the live Wikidata SPARQL refresh and use the cached
  // wikidata.json (already committed). Speeds up local iteration — the full
  // Wikidata pass runs ~70+ queries. Cache is the build-time contract anyway.
  const skipWikidata = process.argv.includes('--skip-wikidata');

  for (const [slug, config] of Object.entries(LOCATIONS)) {
    totalFailures += await fetchLocation(slug, config);
  }

  // Heritage layer (static Canmore shapefile) — independent of the live locations
  console.log('\n--- Heritage (Canmore Points) ---');
  totalFailures += runHeritage();

  // Wikidata join layer (live public SPARQL, build-time cache) — independent
  if (skipWikidata) {
    console.log('\n--- Wikidata join (SKIPPED — using cached wikidata.json) ---');
  } else {
    console.log('\n--- Wikidata join ---');
    totalFailures += runWikidata();
  }

  // GBIF Nature layer (live public endpoint, committed taxon-keys cache) — independent
  console.log('\n--- Nature (GBIF notable species) ---');
  totalFailures += runNature();

  // OSM/Overpass layer (committed cache-only, no live fetch at build)
  console.log('\n--- OSM (OpenStreetMap amenities & Gaelic names) ---');
  totalFailures += runOSM();

  if (totalFailures > 0) {
    console.error(`\n${totalFailures} layer(s) failed. Build will use stale data if it exists.`);
  } else {
    console.log('\nAll locations fetched successfully.');
  }
}

main().catch(e => {
  console.error('Fatal:', e);
  process.exit(1);
});