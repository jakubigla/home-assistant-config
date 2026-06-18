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
  .media { display: flex; flex-direction: column; gap: 22px; align-items: center; flex: 1; justify-content: center; text-align: center; }
  .art { width: 110px; height: 110px; border-radius: 20px; background: linear-gradient(135deg, var(--purple), var(--blue)); flex-shrink: 0; box-shadow: 0 10px 30px rgba(90,169,255,.25); }
  .mt { font-size: 22px; font-weight: 700; }
  .ms { font-size: 14px; color: var(--dim); margin-top: 4px; }
  .ctrl { display: flex; gap: 28px; margin-top: 8px; align-items: center; }
  .ctrl button { background: none; border: none; color: var(--dim); font-size: 26px; cursor: pointer; }
  .ctrl .p { color: var(--txt); font-size: 34px; }
</style>
