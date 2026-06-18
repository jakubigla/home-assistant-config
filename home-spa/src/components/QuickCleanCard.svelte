<script lang="ts">
  import Card from './Card.svelte'
  import { entities, callService } from '../lib/ha'
  import { lightsOnCount } from '../lib/entities'
  const items = [
    { id: 'script.vacuum_clean_mudroom', icon: '🚪', label: 'Mudroom' },
    { id: 'script.vacuum_clean_kitchen', icon: '🍴', label: 'Kitchen' },
  ]
  let onCount = $derived(lightsOnCount($entities))
  function clean(id: string) { callService('script', 'turn_on', {}, { entity_id: id }) }
</script>

<Card icon="🧹" title="Quick Clean">
  <div class="mini">
    {#each items as it (it.id)}
      <button class="mrow" aria-label={it.id} onclick={() => clean(it.id)}><span>{it.icon}</span>{it.label}</button>
    {/each}
    <div class="mrow today"><span>📊</span>Today<span class="mv">{onCount} lights on</span></div>
  </div>
</Card>

<style>
  .mini { display: flex; flex-direction: column; gap: 7px; flex: 1; justify-content: center; }
  .mrow { display: flex; align-items: center; gap: 8px; font-size: 12.5px; background: rgba(255,255,255,.04); border: none; color: var(--txt); padding: 8px 9px; border-radius: 9px; cursor: pointer; text-align: left; }
  .today { background: none; border-top: 1px solid var(--card-brd); border-radius: 0; padding-top: 9px; }
  .mv { margin-left: auto; color: var(--dim); font-size: 11px; }
</style>
