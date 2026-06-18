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
  .media { display: flex; gap: 12px; align-items: center; flex: 1; }
  .art { width: 48px; height: 48px; border-radius: 11px; background: linear-gradient(135deg, var(--purple), var(--blue)); flex-shrink: 0; }
  .mt { font-size: 14px; font-weight: 700; }
  .ms { font-size: 11px; color: var(--dim); }
  .ctrl { display: flex; gap: 14px; margin-top: 7px; }
  .ctrl button { background: none; border: none; color: var(--dim); font-size: 16px; cursor: pointer; }
  .ctrl .p { color: var(--txt); }
</style>
