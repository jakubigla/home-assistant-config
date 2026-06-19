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
  .db { position: relative; border-radius: var(--radius); overflow: hidden; border: 0.0625rem solid var(--card-brd); display: grid; place-items: center; background: #10141d; box-shadow: 0 0.5rem 1.75rem rgba(0,0,0,0.28); }
  .db.offline { background: linear-gradient(165deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02)); }
  .db img { width: 100%; height: 100%; object-fit: cover; }
  .live { position: absolute; top: 0.875rem; left: 1rem; font-size: 0.6875rem; background: var(--red); color: #fff; padding: 0.1875rem 0.5625rem; border-radius: 0.375rem; font-weight: 800; z-index: 1; }
  .ph { display: flex; flex-direction: column; align-items: center; gap: 0.375rem; color: var(--dim); }
  .phicon { font-size: 3.5rem; opacity: .55; }
  .phlabel { font-size: 1.125rem; font-weight: 700; color: var(--txt); }
  .phsub { font-size: 0.8125rem; }
</style>
