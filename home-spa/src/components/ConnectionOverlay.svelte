<script lang="ts">
  let { state }: { state: 'connecting' | 'connected' | 'disconnected' } = $props()
</script>

{#if state !== 'connected'}
  <div class="ov">{state === 'connecting' ? 'Connecting…' : 'Reconnecting…'}</div>
{/if}

<style>
  .ov { position: fixed; top: 12px; left: 50%; transform: translateX(-50%); background: rgba(0,0,0,.6); padding: 6px 16px; border-radius: 999px; font-size: 12px; color: var(--dim); z-index: 20; }
</style>
