<script lang="ts">
  import type { Snippet } from 'svelte'
  let { icon, title, children }: { icon?: string; title?: string; children: Snippet } = $props()
</script>

<div class="glass">
  {#if title}
    <div class="gh">{#if icon}<span class="gi">{icon}</span>{/if}<span class="gt">{title}</span></div>
  {/if}
  <div class="body">
    {@render children()}
  </div>
</div>

<style>
  .glass {
    background: linear-gradient(165deg, rgba(255,255,255,0.07), rgba(255,255,255,0.025));
    border: 1px solid var(--card-brd);
    border-radius: var(--radius);
    padding: 18px 20px;
    display: flex;
    flex-direction: column;
    min-height: 0;
    box-shadow: 0 8px 28px rgba(0,0,0,0.28), inset 0 1px 0 rgba(255,255,255,0.05);
  }
  .gh { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; flex-shrink: 0; }
  .gi { font-size: 18px; }
  .gt { font-size: 12px; letter-spacing: .12em; text-transform: uppercase; color: var(--dim); font-weight: 700; }
  /* body fills the card and centres its content so nothing strands at an edge */
  .body { flex: 1; min-height: 0; display: flex; flex-direction: column; justify-content: center; }
</style>
