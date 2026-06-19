<script lang="ts">
  let { state }: { state: 'connecting' | 'connected' | 'disconnected' } = $props()
</script>

{#if state !== 'connected'}
  <div class="ov">{state === 'connecting' ? 'Connecting…' : 'Reconnecting…'}</div>
{/if}

<style>
  .ov { position: fixed; top: 0.75rem; left: 50%; transform: translateX(-50%); background: rgba(0,0,0,.6); padding: 0.375rem 1rem; border-radius: 62.4375rem; font-size: 0.75rem; color: var(--dim); z-index: 20; }
</style>
