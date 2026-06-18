<script lang="ts">
  import { entities } from '../lib/ha'
  import { IDS } from '../lib/entities'
  let tick = $state(0)
  // refresh the still image every 1.5s (cheap on weak GPU vs live stream);
  // cleared on unmount so a hidden/boundary-failed card doesn't leak the timer
  $effect(() => {
    const id = setInterval(() => (tick += 1), 1500)
    return () => clearInterval(id)
  })
  // HA's camera_proxy needs a signed URL — the camera entity exposes one in its
  // entity_picture attribute (token rotates with state). Building the path by
  // hand returns 403, so always read it from the live entity. Camera down /
  // no picture → show a placeholder instead of a broken image.
  let cam = $derived($entities[IDS.doorbell])
  let picture = $derived(cam?.attributes?.entity_picture as string | undefined)
  let live = $derived(cam?.state !== 'unavailable' && !!picture)
  let src = $derived(picture ? `${picture}&t=${tick}` : '')
</script>

<div class="db" class:offline={!live}>
  {#if live}
    <span class="live">● LIVE</span>
    <img alt="Doorbell" {src} />
  {:else}
    <div class="ph">
      <div class="phicon">📹</div>
      <div class="phlabel">Doorbell</div>
      <div class="phsub">Camera offline</div>
    </div>
  {/if}
</div>

<style>
  .db { position: relative; border-radius: var(--radius); overflow: hidden; border: 1px solid var(--card-brd); display: grid; place-items: center; background: #10141d; box-shadow: 0 8px 28px rgba(0,0,0,0.28); }
  .db.offline { background: linear-gradient(165deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02)); }
  .db img { width: 100%; height: 100%; object-fit: cover; }
  .live { position: absolute; top: 14px; left: 16px; font-size: 11px; background: var(--red); color: #fff; padding: 3px 9px; border-radius: 6px; font-weight: 800; z-index: 1; }
  .ph { display: flex; flex-direction: column; align-items: center; gap: 6px; color: var(--dim); }
  .phicon { font-size: 56px; opacity: .55; }
  .phlabel { font-size: 18px; font-weight: 700; color: var(--txt); }
  .phsub { font-size: 13px; }
</style>
