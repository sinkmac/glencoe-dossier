// Generic dossier route: renders whatever layers exist for an atom.
// Reads src/data/<slug>/ at build time (prerendered static site).
import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { join } from 'node:path';

// Prerender runs from the project root, so resolve src/data against cwd —
// __dirname here points into .svelte-kit/build output, not the source tree.
const DATA_DIR = join(process.cwd(), 'src', 'data');

// Layer filename → family key the renderer knows how to display.
const LAYER_FILES = {
  'heritage.json': 'heritage',
  'biteforecast-midge.json': 'condition',
  'munro-windows.json': 'condition',
  'vigil-alignments.json': 'culture'
};

// Atoms that ship a heritage layer (the four place pages). These are the
// prerendered slugs. Extend as more parishes/atoms are added.
const HERITAGE_ATOMS = ['kirriemuir', 'auchmithie', 'tiree', 'south-uist'];

export const prerender = true;

export const entries = () => {
  return HERITAGE_ATOMS.map((slug) => ({ slug }));
};

export async function load({ params }) {
  const { slug } = params;
  const dir = join(DATA_DIR, slug);

  const atoms = JSON.parse(readFileSync(join(DATA_DIR, 'atoms.json'), 'utf-8'));

  const layers = [];
  if (existsSync(dir)) {
    for (const file of readdirSync(dir)) {
      const family = LAYER_FILES[file];
      if (!family) continue;
      const raw = readFileSync(join(dir, file), 'utf-8');
      const data = JSON.parse(raw);
      layers.push({ family, file, data });
    }
  }

  return { slug, atom: atoms[slug] ?? null, layers };
}