<script lang="ts">
  import Card from './Card.svelte'
  import { entities, callService } from '../lib/ha'
  import { LIGHT_IDS, isLightOn, lightsOnCount } from '../lib/entities'

  let map = $derived($entities)
  let onCount = $derived(lightsOnCount(map))

  function toggle(id: string) {
    callService('light', 'toggle', {}, { entity_id: id })
  }
  function allOff() {
    callService('light', 'turn_off', {}, { entity_id: 'all' })
  }
</script>

<Card icon="💡" title={`Lights · ${onCount} on`}>
  <div class="grid">
    {#each LIGHT_IDS as l (l.id)}
      <button class="lc" class:on={isLightOn(map, l.id)} aria-label={l.id} onclick={() => toggle(l.id)}>{l.icon}</button>
    {/each}
    <button class="lc off" aria-label="all-off" onclick={allOff}>⏻</button>
  </div>
</Card>

<style>
  .grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 7px; flex: 1; }
  .lc { border: none; border-radius: 11px; display: grid; place-items: center; font-size: 18px; background: rgba(255,255,255,.05); color: var(--txt); cursor: pointer; }
  .lc.on { background: radial-gradient(circle at 50% 30%, rgba(255,181,71,.4), rgba(255,181,71,.04)); color: #ffd9a0; }
  .lc.off { color: var(--red); background: rgba(255,93,108,.08); font-size: 15px; }
</style>
