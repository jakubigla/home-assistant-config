<script lang="ts">
  import Card from './Card.svelte'
  import { entities } from '../lib/ha'
  import { applianceState } from '../lib/entities'
  let a = $derived(applianceState($entities))
  let rows = $derived([
    { id: 'washer', icon: '🌀', name: 'Washer', on: a.washer, label: a.washer ? 'running' : 'idle' },
    { id: 'dryer', icon: '🔥', name: 'Dryer', on: a.dryer, label: a.dryer ? 'running' : 'idle' },
    { id: 'gfVac', icon: '🤖', name: 'GF Vac', on: a.gfVac, label: a.gfVac ? 'cleaning' : 'idle' },
    { id: 'firstVac', icon: '🤖', name: '1F Vac', on: a.firstVac, label: a.firstVac ? 'cleaning' : 'idle' },
  ])
</script>

<Card icon="🏠" title="Appliances">
  <div class="mini">
    {#each rows as r (r.id)}
      <div class="mrow"><span>{r.icon}</span>{r.name}<span class="mv" class:on={r.on}>{r.label}</span></div>
    {/each}
  </div>
</Card>

<style>
  .mini { display: flex; flex-direction: column; gap: 0.875rem; flex: 1; justify-content: center; }
  .mrow { display: flex; align-items: center; gap: 0.875rem; font-size: 1.0625rem; font-weight: 500; }
  .mrow > :global(span:first-child) { font-size: 1.5rem; }
  .mv { margin-left: auto; color: var(--dim); font-size: 0.875rem; }
  .mv.on { color: var(--blue); font-weight: 600; }
</style>
