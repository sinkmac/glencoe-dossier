<script>
  import midgeData from '../../data/callanish/biteforecast-midge.json';
  import munroData from '../../data/callanish/munro-windows.json';
  import vigilData from '../../data/callanish/vigil-alignments.json';
  import atoms from '../../data/atoms.json';

  function family(type) {
    return type.split('/')[0];
  }

  function statusLabel(fam, val) {
    const labels = {
      condition: { good: 'Good', fair: 'Fair', poor: 'Poor', severe: 'Severe' },
      culture: { upcoming: 'Upcoming', live: 'Live', met: 'Past' },
      cause: { open: 'Open', urgent: 'Urgent', met: 'Resolved' },
      mood: { good: 'Good', fair: 'Fair', poor: 'Poor', severe: 'Severe' }
    };
    return labels[fam]?.[val] ?? val;
  }

  function fmt(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    return d.toLocaleString('en-GB', {
      weekday: 'short', day: 'numeric', month: 'short',
      hour: '2-digit', minute: '2-digit',
      timeZone: 'Europe/London'
    });
  }

  function atomName(slug) {
    return atoms[slug]?.name ?? slug;
  }

  function expired(item) {
    if (!item.when?.end) return false;
    return new Date(item.when.end) < new Date();
  }

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

  // Aggregate condition items
  const conditionItems = sections
    .flatMap(s => s.groups['condition'] || [])
    .sort((a, b) => new Date(a.when.start) - new Date(b.when.start));

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

  const disclaimers = layers
    .filter(l => l.disclaimer && l.source)
    .map(l => ({ source: l.source, text: l.disclaimer }));
</script>

<svelte:head>
  <title>Callanish — dossier</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
</svelte:head>

<div class="page">
  <header class="banner">
    <h1>Callanish</h1>
    <p class="subtitle">Dossier &middot; { new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }) }</p>
  </header>

  {#if conditionItems.length === 0 && conditionGaps.length === 0 && cultureItems.length === 0 && cultureGaps.length === 0}
    <p class="empty">No information available for this location.</p>
  {/if}

  <!-- Conditions -->
  {#if conditionItems.length > 0 || conditionGaps.length > 0}
    <section class="section">
      <h2>Conditions Now</h2>
      {#each conditionItems as item}
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
          <p class="gap-message">No vigil site near Callanish. Nearest: <strong>{gap.nearest_name || atomName(gap.nearest_atom)}</strong>, about {Math.round(gap.distance_km * 0.621)} miles south.</p>
          {#if gap.next_event}
            <p class="gap-event">Next alignment: {fmt(gap.next_event)}</p>
          {/if}
        </div>
      {/each}
    </section>
  {/if}

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

  .page { max-width: 640px; margin: 2rem auto; padding: 0 1rem; }
  .banner { margin-bottom: 1.5rem; }
  .banner h1 { font-size: 1.5rem; font-weight: 600; letter-spacing: -0.01em; }
  .subtitle { color: #666; font-size: 0.85rem; margin-top: 0.1rem; }
  .section { margin-bottom: 1.5rem; }
  .section h2 { font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; color: #888; margin-bottom: 0.75rem; }
  .card { background: #fff; border: 1px solid #e5e3df; border-radius: 8px; padding: 0.85rem 1rem; margin-bottom: 0.5rem; }
  .card-header { display: flex; align-items: baseline; gap: 0.5rem; }
  .headline { font-weight: 500; }
  .status-badge { display: inline-block; font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; padding: 0.1rem 0.4rem; border-radius: 3px; white-space: nowrap; flex-shrink: 0; }
  .status-good { background: #e2f0e0; color: #2a6b2a; }
  .status-fair { background: #f0edc0; color: #7a6a20; }
  .status-poor { background: #f5d0c0; color: #a04020; }
  .status-severe { background: #e8c0c0; color: #8b2020; }
  .status-upcoming { background: #dce8f5; color: #2a5070; }
  .status-live { background: #e2f0e0; color: #2a6b2a; }
  .status-met { background: #e5e3df; color: #666; }
  .meta { font-size: 0.8rem; color: #888; margin-top: 0.3rem; }
  .countdown-signal { font-size: 0.75rem; color: #2a5070; font-weight: 500; }
  .gap-card { background: #f4f2ef; border-style: dashed; }
  .gap-message { color: #555; font-size: 0.9rem; }
  .gap-event { margin-top: 0.2rem; font-size: 0.8rem; color: #777; }
  .empty { color: #888; font-style: italic; }
  .disclaimers { margin-top: 2rem; padding-top: 1rem; }
  .disclaimers hr { border: none; border-top: 1px solid #e5e3df; margin-bottom: 0.75rem; }
  .disclaimer { font-size: 0.75rem; color: #999; margin-bottom: 0.25rem; }
</style>