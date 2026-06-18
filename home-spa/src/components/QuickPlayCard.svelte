<script lang="ts">
  import Card from './Card.svelte'
  import { callService } from '../lib/ha'
  const items = [
    { id: 'script.music_play_discover_weekly', icon: '★', label: 'Discover Weekly', color: 'var(--green)' },
    { id: 'script.music_play_random_playlist', icon: '🔀', label: 'Random Playlist', color: 'var(--purple)' },
    { id: 'script.music_play_last_played', icon: '↺', label: 'Last Played', color: 'var(--blue)' },
  ]
  function play(id: string) { callService('script', 'turn_on', {}, { entity_id: id }) }
</script>

<Card icon="▶" title="Quick Play">
  <div class="mini">
    {#each items as it (it.id)}
      <button class="mrow" aria-label={it.id} onclick={() => play(it.id)}><span style="color:{it.color}">{it.icon}</span>{it.label}</button>
    {/each}
  </div>
</Card>

<style>
  .mini { display: flex; flex-direction: column; gap: 12px; flex: 1; justify-content: center; }
  .mrow { display: flex; align-items: center; gap: 14px; font-size: 17px; font-weight: 500; background: rgba(255,255,255,.04); border: none; color: var(--txt); padding: 16px; border-radius: 14px; cursor: pointer; text-align: left; transition: background .12s; }
  .mrow:active { background: rgba(255,255,255,.09); }
  .mrow > :global(span:first-child) { font-size: 22px; }
</style>
