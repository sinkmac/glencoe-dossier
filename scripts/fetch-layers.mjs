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
  writeFileSync(filePath, JSON.stringify(data, null, 2));
  const itemCount = data.items?.length || 0;
  const hasGap = data.gap ? ` gap:${data.gap.nearest_name || data.gap.nearest_atom}` : '';
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

  for (const [slug, config] of Object.entries(LOCATIONS)) {
    totalFailures += await fetchLocation(slug, config);
  }

  // Heritage layer (static Canmore shapefile) — independent of the live locations
  console.log('\n--- Heritage (Canmore Points) ---');
  totalFailures += runHeritage();

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