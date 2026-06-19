<script lang="ts">
  import Card from './Card.svelte'
  import { entities, callService } from '../lib/ha'
  import { IDS } from '../lib/entities'
  let m = $derived($entities[IDS.mediaTv])
  let title = $derived(m?.attributes?.media_title ?? (m?.state === 'playing' ? 'Playing' : 'Idle'))
  let app = $derived(m?.attributes?.app_name ?? 'Living Room TV')
  function ctl(svc: string) {
    callService('media_player', svc, {}, { entity_id: IDS.mediaTv })
  }
</script>

<Card icon="🎵" title="Living Room TV">
  <div class="media">
    <div class="art"></div>
    <div class="info">
      <div class="mt">{title}</div>
      <div class="ms">{app}</div>
      <div class="ctrl">
        <button aria-label="prev" onclick={() => ctl('media_previous_track')}>⏮</button>
        <button aria-label="play-pause" class="p" onclick={() => ctl('media_play_pause')}>⏯</button>
        <button aria-label="next" onclick={() => ctl('media_next_track')}>⏭</button>
      </div>
    </div>
  </div>
</Card>

<style>
  .media { display: flex; flex-direction: column; gap: 1.375rem; align-items: center; flex: 1; justify-content: center; text-align: center; }
  .art { width: 6.875rem; height: 6.875rem; border-radius: 1.25rem; background: linear-gradient(135deg, var(--purple), var(--blue)); flex-shrink: 0; box-shadow: 0 0.625rem 1.875rem rgba(90,169,255,.25); }
  .mt { font-size: 1.375rem; font-weight: 700; }
  .ms { font-size: 0.875rem; color: var(--dim); margin-top: 0.25rem; }
  .ctrl { display: flex; gap: 1.75rem; margin-top: 0.5rem; align-items: center; }
  .ctrl button { background: none; border: none; color: var(--dim); font-size: 1.625rem; cursor: pointer; }
  .ctrl .p { color: var(--txt); font-size: 2.125rem; }
</style>
