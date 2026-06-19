<script lang="ts">
  import { entities } from '../lib/ha'
  import { IDS } from '../lib/entities'

  let { now }: { now: Date } = $props()

  const pad = (n: number) => String(n).padStart(2, '0')
  let time = $derived(`${pad(now.getHours())}:${pad(now.getMinutes())}`)
  let date = $derived(now.toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }))

  let w = $derived($entities[IDS.weather])
  let temp = $derived(w ? Math.round(Number(w.attributes?.temperature ?? 0)) : null)
  let cond = $derived(w ? w.state : 'unknown')
  let humidity = $derived(w ? Math.round(Number(w.attributes?.humidity ?? 0)) : null)
  let wind = $derived(w ? Math.round(Number(w.attributes?.wind_speed ?? 0)) : null)

  let jakub = $derived($entities[IDS.personJakub])
  let sona = $derived($entities[IDS.personSona])
</script>

<header>
  <div class="left">
    <div class="time">{time}</div>
    <div class="date">{date}</div>
  </div>
  <div class="right">
    <div class="wx">
      <div class="wt">{temp ?? '–'}°C</div>
      <div class="wc">{cond} · wind {wind ?? '–'} · {humidity ?? '–'}%</div>
    </div>
    <div class="people">
      <span class="av" class:away={jakub?.state !== 'home'} style="background:#3d7dff">J<i></i></span>
      <span class="av" class:away={sona?.state !== 'home'} style="background:#ff5d8a">S<i></i></span>
    </div>
  </div>
</header>

<style>
  header { display: flex; align-items: flex-start; justify-content: space-between; }
  .time { font-size: 3.625rem; font-weight: 300; line-height: .9; letter-spacing: -.02em; }
  .date { font-size: 0.875rem; color: var(--dim); margin-top: 0.375rem; }
  .right { display: flex; align-items: center; gap: 1.125rem; }
  .wt { font-size: 1.875rem; font-weight: 300; text-align: right; }
  .wc { font-size: 0.75rem; color: var(--dim); text-align: right; text-transform: capitalize; }
  .people { display: flex; gap: 0.5rem; }
  .av { width: 2.625rem; height: 2.625rem; border-radius: 50%; display: grid; place-items: center; font-weight: 800; font-size: 0.9375rem; color: #fff; position: relative; }
  .av.away { opacity: .4; }
  .av i { position: absolute; bottom: -0.0625rem; right: -0.0625rem; width: 0.75rem; height: 0.75rem; border-radius: 50%; border: 0.125rem solid var(--bg); background: var(--green); }
  .av.away i { background: var(--dim); }
</style>
