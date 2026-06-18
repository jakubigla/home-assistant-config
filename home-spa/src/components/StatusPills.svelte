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
  .row { display: flex; gap: 9px; flex-wrap: wrap; }
  .pill { background: var(--card); border: 1px solid var(--card-brd); border-radius: 999px; padding: 8px 14px; font-size: 12.5px; display: flex; align-items: center; gap: 7px; font-weight: 500; }
  .pill.ok { border-color: rgba(61,220,143,.3); }
  .pill.warn { border-color: rgba(255,93,108,.4); background: rgba(255,93,108,.07); }
  .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--green); }
  .dot.red { background: var(--red); box-shadow: 0 0 7px var(--red); }
</style>
