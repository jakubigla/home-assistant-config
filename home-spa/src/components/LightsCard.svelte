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
  .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; flex: 1; align-content: stretch; }
  .lc { border: none; border-radius: 16px; display: grid; place-items: center; font-size: 34px; background: rgba(255,255,255,.05); color: var(--txt); cursor: pointer; transition: transform .12s; }
  .lc:active { transform: scale(.94); }
  .lc.on { background: radial-gradient(circle at 50% 30%, rgba(255,181,71,.45), rgba(255,181,71,.05)); color: #ffd9a0; box-shadow: 0 0 24px rgba(255,181,71,.22); }
  .lc.off { color: var(--red); background: rgba(255,93,108,.08); font-size: 28px; }
</style>
