<script lang="ts">
  import { entities } from '../lib/ha'
  import { readyToArm, doorStatus, IDS } from '../lib/entities'

  let map = $derived($entities)
  let arm = $derived(readyToArm(map))
  let doors = $derived(doorStatus(map))
  let openDoors = $derived(doors.filter(d => d.open))
  let closedDoors = $derived(doors.filter(d => !d.open))
  let scene = $derived(map[IDS.scene]?.state ?? '–')
</script>

<div class="row">
  <div class="pill" class:ok={arm.ready} class:warn={!arm.ready}>
    <span class="dot" class:red={!arm.ready}></span>
    {arm.ready ? 'Ready to Arm' : 'Not Ready'} · {arm.occupiedZones} zones
  </div>
  {#each openDoors as d (d.id)}
    <div class="pill warn"><span class="dot red"></span>{d.label} open</div>
  {/each}
  {#if closedDoors.length}
    <div class="pill"><span class="dot"></span>{closedDoors.map(d => d.label).join(' · ')} closed</div>
  {/if}
  <div class="pill"><span style="color:var(--purple)">🎬</span>Scene: {scene}</div>
</div>

<style>
  .row { display: flex; gap: 0.5625rem; flex-wrap: wrap; }
  .pill { background: var(--card); border: 0.0625rem solid var(--card-brd); border-radius: 62.4375rem; padding: 0.5rem 0.875rem; font-size: 0.7812rem; display: flex; align-items: center; gap: 0.4375rem; font-weight: 500; }
  .pill.ok { border-color: rgba(61,220,143,.3); }
  .pill.warn { border-color: rgba(255,93,108,.4); background: rgba(255,93,108,.07); }
  .dot { width: 0.5rem; height: 0.5rem; border-radius: 50%; background: var(--green); }
  .dot.red { background: var(--red); box-shadow: 0 0 0.4375rem var(--red); }
</style>
