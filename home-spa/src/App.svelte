<script lang="ts">
  import './styles/tokens.css'
  import { onMount } from 'svelte'
  import { connect, connectionState, getToken, setToken } from './lib/ha'
  import Header from './components/Header.svelte'
  import StatusPills from './components/StatusPills.svelte'
  import LightsCard from './components/LightsCard.svelte'
  import ClimateCard from './components/ClimateCard.svelte'
  import MediaCard from './components/MediaCard.svelte'
  import DoorbellCard from './components/DoorbellCard.svelte'
  import CurtainsCard from './components/CurtainsCard.svelte'
  import AppliancesCard from './components/AppliancesCard.svelte'
  import QuickPlayCard from './components/QuickPlayCard.svelte'
  import QuickCleanCard from './components/QuickCleanCard.svelte'
  import Dock from './components/Dock.svelte'
  import TokenPrompt from './components/TokenPrompt.svelte'
  import ConnectionOverlay from './components/ConnectionOverlay.svelte'

  let needsToken = $state(getToken() === null)
  let now = $state(new Date())

  onMount(() => {
    const clock = setInterval(() => (now = new Date()), 30_000)
    if (!needsToken) connect().catch(() => (needsToken = true))
    return () => clearInterval(clock)
  })

  function onToken(token: string) {
    setToken(token)
    needsToken = false
    connect().catch(() => (needsToken = true))
  }

  const cards = [LightsCard, ClimateCard, MediaCard, DoorbellCard, CurtainsCard, AppliancesCard, QuickPlayCard, QuickCleanCard]
</script>

{#if needsToken}
  <TokenPrompt onsubmit={onToken} />
{:else}
  <ConnectionOverlay state={$connectionState} />
  <main>
    <Header {now} />
    <StatusPills />
    <div class="stage">
      {#each cards as Card (Card)}
        <svelte:boundary>
          <Card />
          {#snippet failed()}<div class="cardfail">unavailable</div>{/snippet}
        </svelte:boundary>
      {/each}
    </div>
    <Dock />
  </main>
{/if}

<style>
  main { height: 100vh; padding: 26px 30px; display: flex; flex-direction: column; gap: 18px; }
  .stage { flex: 1; display: grid; grid-template-columns: repeat(4, 1fr); grid-template-rows: 1fr 1fr; gap: 13px; min-height: 0; }
  .stage > :global(*) { min-height: 0; }
  .cardfail { background: var(--card); border: 1px solid var(--card-brd); border-radius: var(--radius); display: grid; place-items: center; color: var(--dim); font-size: 12px; }
</style>
