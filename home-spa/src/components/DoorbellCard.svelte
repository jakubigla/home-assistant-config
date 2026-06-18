<script lang="ts">
  import { cameraProxyUrl } from '../lib/ha'
  import { IDS } from '../lib/entities'
  let tick = $state(0)
  // refresh the still image every 1.5s (cheap on weak GPU vs live stream);
  // cleared on unmount so a hidden/boundary-failed card doesn't leak the timer
  $effect(() => {
    const id = setInterval(() => (tick += 1), 1500)
    return () => clearInterval(id)
  })
  let src = $derived(`${cameraProxyUrl(IDS.doorbell)}?t=${tick}`)
</script>

<div class="db">
  <span class="live">● LIVE</span>
  <img alt="Doorbell" {src} />
</div>

<style>
  .db { position: relative; border-radius: var(--radius); overflow: hidden; background: #10141d; border: 1px solid var(--card-brd); display: grid; place-items: center; }
  .db img { width: 100%; height: 100%; object-fit: cover; }
  .live { position: absolute; top: 10px; left: 12px; font-size: 9px; background: var(--red); color: #fff; padding: 2px 7px; border-radius: 5px; font-weight: 800; z-index: 1; }
</style>
