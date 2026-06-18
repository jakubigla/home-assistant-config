<script lang="ts">
  import type { Snippet } from 'svelte'
  let { icon, title, children }: { icon?: string; title?: string; children: Snippet } = $props()
</script>

<div class="glass">
  {#if title}
    <div class="gh">{#if icon}<span class="gi">{icon}</span>{/if}<span class="gt">{title}</span></div>
  {/if}
  {@render children()}
</div>

<style>
  .glass { background: var(--card); border: 1px solid var(--card-brd); border-radius: var(--radius); padding: 15px 16px; display: flex; flex-direction: column; min-height: 0; }
  .gh { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
  .gi { font-size: 18px; }
  .gt { font-size: 12px; letter-spacing: .12em; text-transform: uppercase; color: var(--dim); font-weight: 700; }
</style>
