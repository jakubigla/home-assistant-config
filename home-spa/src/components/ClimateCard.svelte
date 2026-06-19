<script lang="ts">
  import Card from './Card.svelte'
  import { entities } from '../lib/ha'
  import { climate } from '../lib/entities'
  let map = $derived($entities)
  let lr = $derived(climate(map, 'living_room'))
  let br = $derived(climate(map, 'bedroom'))
</script>

<Card icon="🌡️" title="Climate">
  <div class="r">
    <div><div class="n">Living Room</div><div class="h">{lr.humidity}% · <span class:on={lr.humidifierOn}>Humid {lr.humidifierOn ? 'ON' : 'OFF'}</span></div></div>
    <div class="v">{lr.temp.toFixed(1)}°</div>
  </div>
  <div class="r">
    <div><div class="n">Bedroom</div><div class="h">{br.humidity}% · <span class:on={br.humidifierOn}>Humid {br.humidifierOn ? 'ON' : 'OFF'}</span></div></div>
    <div class="v">{br.temp.toFixed(1)}°</div>
  </div>
</Card>

<style>
  .r { display: flex; align-items: center; justify-content: space-between; padding: 1.125rem 0; }
  .r + .r { border-top: 0.0625rem solid var(--card-brd); }
  .n { font-size: 1.125rem; font-weight: 700; }
  .h { font-size: 0.8125rem; color: var(--dim); margin-top: 0.25rem; }
  .h .on { color: var(--cyan); font-weight: 600; }
  .v { font-size: 2.875rem; font-weight: 300; letter-spacing: -.02em; }
</style>
