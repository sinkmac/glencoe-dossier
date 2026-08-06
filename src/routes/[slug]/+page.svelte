<script>
  let { data } = $props();

  const { slug, atom, layers, wikidata } = data;

  // ── Layer separation ──────────────────────────────────────────────
  const heritageLayer = layers.find((l) => l.family === 'heritage');
  const heritage = heritageLayer?.data ?? null;

  const conditionLayers = layers.filter((l) => l.family === 'condition');
  const cultureLayers = layers.filter((l) => l.family === 'culture');

  // ── Wikidata enrichment (join layer) ──────────────────────────────
  // Additive only: an item with no P718 match has no entry, so it renders
  // exactly as it does today. wikidata.items is keyed by CANMOREID; the
  // heritage item id is "heritage:<atom>:<canmoreid>".
  const wdMap = wikidata?.items ?? {};
  const people = wikidata?.people ?? [];
  const hasWdAttribution = !!(wikidata && wikidata.attribution);

  function wdMatch(item) {
    const cid = item.id.split(':').pop();
    return wdMap[cid] || null;
  }
  // Defensive: force https on image URLs (Wikidata P18 can be http://, which
  // the browser blocks as mixed content on an HTTPS page).
  function wdImage(match) {
    const img = match && match.image;
    if (!img) return null;
    return img.startsWith('http://') ? 'https://' + img.slice(7) : img;
  }

  // ── Heritage: group by broadclass, cap per group, confidence count ─
  // Items carry (id, name, broadclass[], sitetype[], confidence, lat, lon,
  // trove_url, when{tense,label}). No `what` object — grouped by category.
  function buildGroups(items) {
    const groups = {};
    for (const item of items) {
      const key = (item.broadclass && item.broadclass[0]) || 'UNCLASSIFIED';
      if (!groups[key]) groups[key] = [];
      groups[key].push(item);
    }
    return Object.entries(groups)
      .sort((a, b) => b[1].length - a[1].length || a[0].localeCompare(b[0]))
      .map(([name, list]) => ({
        name,
        items: list.sort((a, b) => a.name.localeCompare(b.name)),
        count: list.length
      }));
  }

  const heritageGroups = heritage ? buildGroups(heritage.items || []) : [];
  const HERITAGE_SHOW = 8; // default cap per group ("briefing, not a dashboard")
  let expanded = $state(new Set()); // broadclass keys shown in full

  const totalHeritage = heritage?.items?.length ?? 0;
  const confidenceDist = {};
  for (const it of heritage?.items ?? []) {
    confidenceDist[it.confidence] = (confidenceDist[it.confidence] || 0) + 1;
  }
  const hasAttribution = !!(heritage && heritage.attribution);

  const confClass = {
    HIGH: 'conf-high',
    MODERATE: 'conf-moderate',
    LOW: 'conf-low'
  };

  function visibleItems(group) {
    return expanded.has(group.name) ? group.items : group.items.slice(0, HERITAGE_SHOW);
  }
  function toggleGroup(name) {
    const next = new Set(expanded);
    if (next.has(name)) next.delete(name);
    else next.add(name);
    expanded = next;
  }
</script>

<svelte:head>
  <title>{atom?.name ?? slug} — dossier</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
</svelte:head>

<div class="page">
  <header class="banner">
    <h1>{atom?.name ?? slug}</h1>
    <p class="subtitle">Dossier &middot; { new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }) }</p>
  </header>

  {#if layers.length === 0}
    <p class="empty">No information available for this place.</p>
  {/if}

  <!-- Heritage -->
  {#if heritage && totalHeritage > 0}
    <section class="section">
      <h2>Heritage <span class="count-badge">{totalHeritage}</span></h2>
      <p class="section-note">
        Historic Environment Scotland records for the civil parish.
        {#if confidenceDist.HIGH}<span class="mini-stat"><strong>{confidenceDist.HIGH}</strong> high-confidence</span>{/if}
        {#if confidenceDist.MODERATE}<span class="mini-stat"><strong>{confidenceDist.MODERATE}</strong> moderate</span>{/if}
        {#if confidenceDist.LOW}<span class="mini-stat"><strong>{confidenceDist.LOW}</strong> low</span>{/if}
        {#if heritage.gap}
          <span class="gap-flag">no records found</span>
        {/if}
      </p>

      {#if hasAttribution}
        <p class="attribution">{heritage.attribution}</p>
      {/if}

      {#each heritageGroups as group}
        <div class="heritage-group">
          <h3 class="group-title">{group.name} <span class="group-count">{group.count}</span></h3>
          {#each visibleItems(group) as item (item.id)}
            {@const wd = wdMatch(item)}
            <div class="card herit-card">
              <div class="card-header">
                <span class="conf-badge {confClass[item.confidence] || 'conf-low'}">{item.confidence}</span>
                <a class="headline herit-name" href="{item.trove_url}">{item.name}</a>
              </div>
              {#if item.sitetype && item.sitetype.length}
                <p class="sitetype">{item.sitetype.join(' · ')}</p>
              {/if}
              {#if wd}
                <div class="herit-enrich">
                  {#if wd.image}
                    <img class="herit-thumb" src="{wdImage(wd)}" alt="" loading="lazy" />
                  {/if}
                  <div class="herit-enrich-links">
                    {#if wd.article}
                      <a href="{wd.article}" rel="noopener" class="enrich-link">Wikipedia →</a>
                    {/if}
                    <a href="https://www.wikidata.org/wiki/{wd.qid}" rel="noopener" class="enrich-link">Wikidata →</a>
                  </div>
                </div>
              {/if}
            </div>
          {/each}
          {#if group.count > HERITAGE_SHOW}
            <button class="show-more" onclick={() => toggleGroup(group.name)}>
              {expanded.has(group.name) ? 'Show fewer −' : `Show all ${group.count} in ${group.name} →`}
            </button>
          {/if}
        </div>
      {/each}
    </section>
  {/if}

  <!-- Notable people (Wikidata, additive — empty for places without records) -->
  {#if people.length > 0}
    <section class="section">
      <h2>Notable People <span class="count-badge">{people.length}</span></h2>
      <p class="section-note">People recorded as born here, via Wikidata.</p>
      {#each people as p}
        <div class="card">
          <div class="card-header">
            {#if p.article}
              <a class="headline herit-name" href="{p.article}" rel="noopener">{p.name}</a>
            {:else}
              <span class="headline">{p.name}</span>
            {/if}
            {#if p.dob}
              <span class="person-dob">b. {p.dob.slice(0, 4)}</span>
            {/if}
          </div>
          {#if p.occupations && p.occupations.length}
            <p class="sitetype">{p.occupations.join(' · ')}</p>
          {/if}
        </div>
      {/each}
      {#if hasWdAttribution}
        <p class="attribution">{wikidata.attribution}</p>
      {/if}
    </section>
  {/if}

  <!-- Conditions (condition-family envelopes when present) -->
  {#if conditionLayers.length}
    <section class="section">
      <h2>Conditions Now</h2>
      {#each conditionLayers as layer}
        {#each (layer.data.items || []) as item (item.id)}
          <div class="card">
            <div class="card-header">
              <span class="headline">{item.what?.headline}</span>
            </div>
          </div>
        {/each}
      {/each}
    </section>
  {/if}

  <!-- Culture (e.g. vigil alignments) -->
  {#if cultureLayers.length}
    <section class="section">
      <h2>Vigil &amp; Alignments</h2>
      {#each cultureLayers as layer}
        {#each (layer.data.items || []) as item (item.id)}
          <div class="card">
            <div class="card-header">
              <span class="headline">{item.what?.headline}</span>
            </div>
          </div>
        {/each}
      {/each}
    </section>
  {/if}

  <footer class="disclaimers">
    <hr />
    {#each layers.filter((l) => l.data.disclaimer && l.data.source) as layer}
      <p class="disclaimer">{layer.data.source}: {layer.data.disclaimer}</p>
    {/each}
    <p class="back-link"><a href="/">← All dossiers</a></p>
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
  .page { max-width: 680px; margin: 2rem auto; padding: 0 1rem; }
  .banner { margin-bottom: 1.5rem; }
  .banner h1 { font-size: 1.5rem; font-weight: 600; letter-spacing: -0.01em; }
  .subtitle { color: #666; font-size: 0.85rem; margin-top: 0.1rem; }
  .section { margin-bottom: 2rem; }
  .section h2 { font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; color: #888; margin-bottom: 0.5rem; }
  .count-badge { font-size: 0.7rem; background: #e5e3df; color: #444; padding: 0.1rem 0.4rem; border-radius: 8px; }
  .section-note { font-size: 0.8rem; color: #777; margin-bottom: 1rem; }
  .mini-stat { margin-right: 0.75rem; }
  .mini-stat strong { color: #444; }
  .gap-flag { color: #a04020; }
  .heritage-group { margin-bottom: 1.25rem; }
  .group-title { font-size: 0.85rem; font-weight: 600; color: #333; margin-bottom: 0.4rem; text-transform: uppercase; letter-spacing: 0.03em; }
  .group-count { color: #999; font-weight: 500; font-size: 0.75rem; }
  .card { background: #fff; border: 1px solid #e5e3df; border-radius: 8px; padding: 0.7rem 1rem; margin-bottom: 0.4rem; }
  .card-header { display: flex; align-items: baseline; gap: 0.5rem; }
  .headline { font-weight: 500; }
  .herit-name { color: #1a1a1a; text-decoration: none; }
  .herit-name:hover { text-decoration: underline; }
  .sitetype { font-size: 0.75rem; color: #888; margin-top: 0.25rem; }
  .herit-enrich { display: flex; align-items: center; gap: 0.75rem; margin-top: 0.5rem; }
  .herit-thumb { width: 4.5rem; height: 3.4rem; object-fit: cover; border-radius: 4px; border: 1px solid #e5e3df; flex-shrink: 0; background: #f4f2ef; }
  .herit-enrich-links { display: flex; flex-direction: column; gap: 0.1rem; }
  .enrich-link { font-size: 0.78rem; color: #2a5070; text-decoration: none; }
  .enrich-link:hover { text-decoration: underline; }
  .person-dob { font-size: 0.78rem; color: #999; margin-left: auto; white-space: nowrap; }
  .conf-badge { display: inline-block; font-size: 0.65rem; font-weight: 700; padding: 0.08rem 0.4rem; border-radius: 3px; white-space: nowrap; flex-shrink: 0; }
  .conf-high { background: #e2f0e0; color: #2a6b2a; }
  .conf-moderate { background: #f0edc0; color: #7a6a20; }
  .conf-low { background: #e5e3df; color: #666; }
  .show-more { display: inline-block; margin-top: 0.25rem; font-size: 0.8rem; color: #2a5070; background: none; border: none; cursor: pointer; padding: 0.15rem 0; }
  .show-more:hover { text-decoration: underline; }
  .attribution { font-size: 0.7rem; color: #999; margin-top: 1rem; line-height: 1.5; }
  .empty { color: #888; font-style: italic; }
  .disclaimers { margin-top: 2rem; padding-top: 1rem; }
  .disclaimers hr { border: none; border-top: 1px solid #e5e3df; margin-bottom: 0.75rem; }
  .disclaimer { font-size: 0.75rem; color: #999; margin-bottom: 0.25rem; }
  .back-link { margin-top: 1rem; }
  .back-link a { color: #2a5070; font-size: 0.85rem; text-decoration: none; }
  .back-link a:hover { text-decoration: underline; }
</style>