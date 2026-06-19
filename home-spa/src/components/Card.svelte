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
    border: 0.0625rem solid var(--card-brd);
    border-radius: var(--radius);
    padding: 1.125rem 1.25rem;
    display: flex;
    flex-direction: column;
    min-height: 0;
    box-shadow: 0 0.5rem 1.75rem rgba(0,0,0,0.28), inset 0 0.0625rem 0 rgba(255,255,255,0.05);
  }
  .gh { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.75rem; flex-shrink: 0; }
  .gi { font-size: 1.125rem; }
  .gt { font-size: 0.75rem; letter-spacing: .12em; text-transform: uppercase; color: var(--dim); font-weight: 700; }
  /* body fills the card and centres its content so nothing strands at an edge */
  .body { flex: 1; min-height: 0; display: flex; flex-direction: column; justify-content: center; }
</style>
