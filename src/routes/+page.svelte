<script>
  import midgeData from '../data/glencoe/biteforecast-midge.json';
  import munroData from '../data/glencoe/munro-windows.json';
  import vigilData from '../data/glencoe/vigil-alignments.json';
  import atoms from '../data/atoms.json';

  /** Extract family from type like 'condition/midge-risk' → 'condition' */
  function family(type) {
    return type.split('/')[0];
  }

  /** Status label scoped by family */
  function statusLabel(fam, val) {
    const labels = {
      condition: { good: 'Good', fair: 'Fair', poor: 'Poor', severe: 'Severe' },
      culture: { upcoming: 'Upcoming', live: 'Live', met: 'Past' },
      cause: { open: 'Open', urgent: 'Urgent', met: 'Resolved' },
      mood: { good: 'Good', fair: 'Fair', poor: 'Poor', severe: 'Severe' }
    };
    return labels[fam]?.[val] ?? val;
  }

  /** Format ISO date to readable */
  function fmt(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    return d.toLocaleString('en-GB', {
      weekday: 'short', day: 'numeric', month: 'short',
      hour: '2-digit', minute: '2-digit',
      timeZone: 'Europe/London'
    });
  }

  /** Resolve atom slug to display name */
  function atomName(slug) {
    return atoms[slug]?.name ?? slug;
  }

  /** Check if item is expired */
  function expired(item) {
    if (!item.when?.end) return false;
    return new Date(item.when.end) < new Date();
  }

  /** Build sections from static data */
  const layers = [midgeData, munroData, vigilData];

  const sections = layers.map(layer => {
    const live = (layer.items || []).filter(i => !expired(i));
    const groups = {};
    for (const item of live) {
      const f = family(item.what.type);
      if (!groups[f]) groups[f] = [];
      groups[f].push(item);
    }
    return { layer, groups, gap: layer.gap ?? null };
  });

  // Aggregate condition items — split munro (summit-window) from midge so each
  // can render its own shape. Munro items now carry a `name` field (from the
  // fetch_munro_v2.py MUNROS config); midge items do not and render as before.
  const allCondition = sections
    .flatMap(s => s.groups['condition'] || [])
    .sort((a, b) => new Date(a.when.start) - new Date(b.when.start));

  const midgeItems = allCondition.filter(i => i.what?.type !== 'condition/summit-window');
  const munroItems = allCondition.filter(i => i.what?.type === 'condition/summit-window');

  // Group munro items by date + status + window (headline encodes window
  // length, e.g. "11-hour window from 08:00"). Same day + same status + same
  // window group into one card; a different window length on the same day is
  // the useful differentiator and stays separate (per the brief).
  function groupMunros(items) {
    const groups = {};
    for (const it of items) {
      const date = (it.when?.start || '').slice(0, 10);
      const key = `${date}|${it.what?.status}|${it.what?.headline}`;
      if (!groups[key]) {
        groups[key] = { date, status: it.what?.status, headline: it.what?.headline, items: [] };
      }
      groups[key].items.push(it);
    }
    return Object.values(groups).map(g => ({ ...g, count: g.items.length }));
  }
  const munroGroups = groupMunros(munroItems);
  let expandedMunroGroups = $state(new Set()); // group keys shown expanded (name list)
  function toggleMunroGroup(key) {
    const next = new Set(expandedMunroGroups);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    expandedMunroGroups = next;
  }

  // Condition gaps: layers with face "conditions" that have no items + have a gap
  const conditionGaps = sections
    .filter(s => s.layer.face === 'conditions' && s.gap && Object.keys(s.groups).length === 0)
    .map(s => ({ layer: s.layer, gap: s.gap }));

  // Culture items
  const cultureItems = sections
    .flatMap(s => s.groups['culture'] || []);

  // Culture gaps: layers with face "culture" that have no items + have a gap
  const cultureGaps = sections
    .filter(s => s.layer.face === 'culture' && s.gap && Object.keys(s.groups).length === 0)
    .map(s => ({ layer: s.layer, gap: s.gap }));

  // Disclaimers from envelopes
  const disclaimers = layers
    .filter(l => l.disclaimer && l.source)
    .map(l => ({ source: l.source, text: l.disclaimer }));

  // ── Munro: best-upcoming-day headline (Problem 3) ─────────────────
  // Deterministic from munroData only (midge unaffected).
  // Best day = future date (strictly after today) with the highest count of
  // GOOD-status items; ties go to the earlier date. Omitted if no future GOOD
  // items exist — no "no good days" message, no editorial language.
  function todayKey() {
    const n = new Date();
    const m = String(n.getMonth() + 1).padStart(2, '0');
    const d = String(n.getDate()).padStart(2, '0');
    return `${n.getFullYear()}-${m}-${d}`;
  }
  function bestDayHeadline() {
    const today = todayKey();
    const counts = {};
    for (const it of (munroData.items || [])) {
      if (it.what?.status !== 'good') continue;
      const dk = (it.when?.start || '').slice(0, 10);
      if (!dk || dk <= today) continue; // future only, strictly after today
      counts[dk] = (counts[dk] || 0) + 1;
    }
    let bestKey = null;
    let bestCount = 0;
    for (const [dk, c] of Object.entries(counts)) {
      if (c > bestCount || (c === bestCount && (bestKey === null || dk < bestKey))) {
        bestKey = dk;
        bestCount = c;
      }
    }
    if (!bestKey) return null;
    const d = new Date(bestKey + 'T00:00:00');
    const label = d.toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'short' });
    return { label, count: bestCount };
  }
  const bestDay = bestDayHeadline();
</script>

<svelte:head>
  <title>Glencoe — dossier</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
</svelte:head>

<div class="page">
  <header class="banner">
    <h1>Glencoe</h1>
    <p class="subtitle">Dossier &middot; { new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }) }</p>
  </header>

  {#if midgeItems.length === 0 && munroGroups.length === 0 && conditionGaps.length === 0 && cultureItems.length === 0 && cultureGaps.length === 0}
    <p class="empty">No information available for this location.</p>
  {/if}

  <!-- Conditions -->
  {#if midgeItems.length > 0 || munroGroups.length > 0 || conditionGaps.length > 0}
    <section class="section">
      <h2>Conditions Now</h2>
      {#if bestDay}
        <p class="best-day">Best day this week: {bestDay.label} — {bestDay.count} Munros with GOOD windows</p>
      {/if}
      {#each midgeItems as item}
        <div class="card condition-{item.what.status}">
          <div class="card-header">
            <span class="status-badge status-{item.what.status}">{statusLabel('condition', item.what.status)}</span>
            <span class="headline">{item.what.headline}</span>
          </div>
          <p class="meta">
            {#if item.when.kind === 'window'}
              {fmt(item.when.start)} &ndash; {fmt(item.when.end)}
            {:else}
              {fmt(item.when.start)}
            {/if}
          </p>
        </div>
      {/each}
      {#each munroGroups as group}
        <div class="card condition-{group.status}">
          <div class="card-header">
            <span class="status-badge status-{group.status}">{statusLabel('condition', group.status)}</span>
            {#if group.count === 1}
              <span class="headline"><strong>{group.items[0].name}</strong> — {group.headline}</span>
            {:else}
              <span class="headline"><strong>{group.count} Munros</strong> — {group.headline}</span>
            {/if}
          </div>
          <p class="meta">
            {fmt(group.items[0].when.start)} &ndash; {fmt(group.items[0].when.end)}
          </p>
          {#if group.count > 1}
            <button class="show-more" onclick={() => toggleMunroGroup(group.date + '|' + group.status + '|' + group.headline)}>
              {expandedMunroGroups.has(group.date + '|' + group.status + '|' + group.headline)
                ? 'Hide Munros −'
                : `▾ ${group.items.map(i => i.name).join(', ')}`}
            </button>
            {#if expandedMunroGroups.has(group.date + '|' + group.status + '|' + group.headline)}
              <div class="munro-list">
                {#each group.items as item}
                  <p class="munro-name">{item.name}</p>
                {/each}
              </div>
            {/if}
          {/if}
        </div>
      {/each}
      {#each conditionGaps as { layer, gap }}
        <div class="card gap-card">
          <p class="gap-message">No local data for this area. Nearest: <strong>{gap.nearest_name || atomName(gap.nearest_atom)}</strong>, about {Math.round(gap.distance_km * 0.621)} miles away.</p>
        </div>
      {/each}
    </section>
  {/if}

  <!-- Culture -->
  {#if cultureItems.length > 0 || cultureGaps.length > 0}
    <section class="section">
      <h2>Vigil &amp; Heritage</h2>
      {#each cultureItems as item}
        <div class="card">
          <div class="card-header">
            <span class="status-badge status-{item.what.status}">{statusLabel('culture', item.what.status)}</span>
            <span class="headline">{item.what.headline}</span>
          </div>
          <p class="meta">
            {#if item.when.kind === 'countdown'}
              {fmt(item.when.start)} &middot; <span class="countdown-signal">Countdown</span>
            {:else}
              {fmt(item.when.start)}
            {/if}
          </p>
        </div>
      {/each}
      {#each cultureGaps as { layer, gap }}
        <div class="card gap-card">
          <p class="gap-message">No vigil site near Glencoe. Nearest: <strong>{gap.nearest_name || atomName(gap.nearest_atom)}</strong>, about {Math.round(gap.distance_km * 0.621)} miles south.</p>
          {#if gap.next_event}
            <p class="gap-event">Next alignment: {fmt(gap.next_event)}</p>
          {/if}
        </div>
      {/each}
    </section>
  {/if}

  <!-- Disclaimers -->
  <footer class="disclaimers">
    <hr />
    {#each disclaimers as d}
      <p class="disclaimer">{d.source}: {d.text}</p>
    {/each}
  </footer>
</div>

<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    font-size: 15px;
    line-height: 1.5;
    color: #1a1a1a;
    background: #faf9f7;
    -webkit-font-smoothing: antialiased;
  }

  .page {
    max-width: 640px;
    margin: 2rem auto;
    padding: 0 1rem;
  }

  .banner {
    margin-bottom: 1.5rem;
  }

  .banner h1 {
    font-size: 1.5rem;
    font-weight: 600;
    letter-spacing: -0.01em;
  }

  .subtitle {
    color: #666;
    font-size: 0.85rem;
    margin-top: 0.1rem;
  }

  .section {
    margin-bottom: 1.5rem;
  }

  .section h2 {
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #888;
    margin-bottom: 0.75rem;
  }

  .best-day {
    font-size: 0.9rem;
    font-weight: 600;
    color: #2a6b2a;
    margin-bottom: 0.75rem;
  }

  .card {
    background: #fff;
    border: 1px solid #e5e3df;
    border-radius: 8px;
    padding: 0.85rem 1rem;
    margin-bottom: 0.5rem;
  }

  .card-header {
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
  }

  .headline {
    font-weight: 500;
  }

  .status-badge {
    display: inline-block;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 0.1rem 0.4rem;
    border-radius: 3px;
    white-space: nowrap;
    flex-shrink: 0;
  }

  .status-good { background: #e2f0e0; color: #2a6b2a; }
  .status-fair { background: #f0edc0; color: #7a6a20; }
  .status-poor { background: #f5d0c0; color: #a04020; }
  .status-severe { background: #e8c0c0; color: #8b2020; }
  .status-upcoming { background: #dce8f5; color: #2a5070; }
  .status-live { background: #e2f0e0; color: #2a6b2a; }
  .status-met { background: #e5e3df; color: #666; }

  .meta {
    font-size: 0.8rem;
    color: #888;
    margin-top: 0.3rem;
  }

  .show-more {
    display: inline-block;
    margin-top: 0.35rem;
    font-size: 0.8rem;
    color: #2a5070;
    background: none;
    border: none;
    cursor: pointer;
    padding: 0.15rem 0;
    text-align: left;
  }
  .show-more:hover { text-decoration: underline; }
  .munro-list { margin-top: 0.4rem; padding-left: 0.25rem; border-top: 1px solid #eef0ec; padding-top: 0.4rem; }
  .munro-name { font-size: 0.8rem; color: #333; margin-bottom: 0.15rem; }

  .countdown-signal {
    font-size: 0.75rem;
    color: #2a5070;
    font-weight: 500;
  }

  .gap-card {
    background: #f4f2ef;
    border-style: dashed;
  }

  .gap-message {
    color: #555;
    font-size: 0.9rem;
  }

  .gap-event {
    margin-top: 0.2rem;
    font-size: 0.8rem;
    color: #777;
  }

  .empty {
    color: #888;
    font-style: italic;
  }

  .disclaimers {
    margin-top: 2rem;
    padding-top: 1rem;
  }

  .disclaimers hr {
    border: none;
    border-top: 1px solid #e5e3df;
    margin-bottom: 0.75rem;
  }

  .disclaimer {
    font-size: 0.75rem;
    color: #999;
    margin-bottom: 0.25rem;
  }
</style>