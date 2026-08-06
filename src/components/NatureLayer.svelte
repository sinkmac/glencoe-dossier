<script>
  export let data = null;

  // IUCN status code → display label
  const iucnMap = {
    'EX': 'Extinct',
    'EW': 'Extinct in the Wild',
    'CR': 'Critically Endangered',
    'EN': 'Endangered',
    'VU': 'Vulnerable',
    'NT': 'Near Threatened',
    'LC': 'Least Concern',
    'DD': 'Data Deficient'
  };

  // Filter items: exclude carry_cc_bync items on commercial pages
  // (Today: render all. Gate marked here for future commercial pages.)
  function visibleItems(items) {
    const isCommercial = false; // dossier is not currently commercial
    return items.filter(item => isCommercial ? !item.carry_cc_bync : true);
  }

  function statusLabel(code) {
    return iucnMap[code] || null;
  }

  $: items = visibleItems(data?.items || []);
  $: hasItems = items.length > 0;
</script>

{#if hasItems}
  <section class="section">
    <h2>Nature Now</h2>
    <p class="section-note">Species recorded in the civil parish via GBIF.</p>

    {#if data.attribution}
      <p class="attribution">{data.attribution}</p>
    {/if}

    {#each items as species (species.id)}
      <div class="card nature-card">
        <div class="card-header">
          <span class="headline nature-name">{species.name}</span>
          {#if statusLabel(species.conservation_status)}
            <span class="status-badge">{statusLabel(species.conservation_status)}</span>
          {/if}
        </div>
        <p class="scientific-name">{species.scientific_name}</p>
        <p class="occurrence-count">
          <strong>{species.occurrence_count.toLocaleString()}</strong> record{species.occurrence_count !== 1 ? 's' : ''}
        </p>
      </div>
    {/each}
  </section>
{/if}

<style>
  .section { margin-bottom: 2rem; }
  .section h2 {
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #888;
    margin-bottom: 0.5rem;
  }
  .section-note {
    font-size: 0.8rem;
    color: #777;
    margin-bottom: 1rem;
  }
  .attribution {
    font-size: 0.7rem;
    color: #999;
    margin-bottom: 1rem;
    line-height: 1.5;
  }
  .card {
    background: #fff;
    border: 1px solid #e5e3df;
    border-radius: 8px;
    padding: 0.7rem 1rem;
    margin-bottom: 0.4rem;
  }
  .card-header {
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
    margin-bottom: 0.35rem;
  }
  .headline {
    font-weight: 500;
  }
  .nature-name {
    color: #1a1a1a;
  }
  .status-badge {
    font-size: 0.65rem;
    font-weight: 700;
    padding: 0.08rem 0.4rem;
    border-radius: 3px;
    background: #e5e3df;
    color: #666;
    white-space: nowrap;
    flex-shrink: 0;
    margin-left: auto;
  }
  .scientific-name {
    font-size: 0.8rem;
    color: #999;
    font-style: italic;
    margin: 0.2rem 0 0.35rem 0;
  }
  .occurrence-count {
    font-size: 0.8rem;
    color: #555;
    margin: 0;
  }
</style>
