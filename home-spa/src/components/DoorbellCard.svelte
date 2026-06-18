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

<div class="db">
  {#if live}
    <span class="live">● LIVE</span>
    <img alt="Doorbell" {src} />
  {:else}
    <span class="ph">📹 Doorbell offline</span>
  {/if}
</div>

<style>
  .db { position: relative; border-radius: var(--radius); overflow: hidden; background: #10141d; border: 1px solid var(--card-brd); display: grid; place-items: center; }
  .db img { width: 100%; height: 100%; object-fit: cover; }
  .live { position: absolute; top: 10px; left: 12px; font-size: 9px; background: var(--red); color: #fff; padding: 2px 7px; border-radius: 5px; font-weight: 800; z-index: 1; }
  .ph { color: var(--dim); font-size: 13px; }
</style>
