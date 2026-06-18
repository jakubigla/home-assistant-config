<script lang="ts">
  import Card from './Card.svelte'
  import { entities, callService } from '../lib/ha'
  import { IDS, coverPosition } from '../lib/entities'
  let map = $derived($entities)
  const rows = [
    { id: IDS.coverGroundFloor, label: 'Ground Floor' },
    { id: IDS.coverBedroom, label: 'Bedroom' },
  ]
  function setPos(id: string, e: Event) {
    const position = Number((e.target as HTMLInputElement).value)
    callService('cover', 'set_cover_position', { position }, { entity_id: id })
  }
</script>

<Card icon="🪟" title="Curtains">
  <div class="body">
    {#each rows as r (r.id)}
      {@const pos = coverPosition(map, r.id)}
      <div class="cvr">
        <span class="nm">{r.label}</span>
        <input type="range" min="0" max="100" value={pos} aria-label={r.id} onchange={(e) => setPos(r.id, e)} />
        <span class="pct">{pos}%</span>
      </div>
    {/each}
  </div>
</Card>

<style>
  .body { flex: 1; display: flex; flex-direction: column; justify-content: center; gap: 28px; }
  .cvr { display: flex; align-items: center; gap: 16px; }
  .nm { font-size: 17px; font-weight: 500; width: 130px; }
  input[type=range] { flex: 1; height: 8px; accent-color: var(--blue); }
  .pct { font-size: 16px; font-weight: 600; color: var(--dim); width: 48px; text-align: right; }
</style>
