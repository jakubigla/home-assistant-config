<script lang="ts">
  const items = [
    { icon: '🌡️', label: 'Climate', href: '/wall-tablet/climate' },
    { icon: '🎬', label: 'Media', href: '/wall-tablet/media' },
    { icon: '🏡', label: 'Outdoor', href: '/wall-tablet/outdoor' },
    { icon: '🛡️', label: 'Security', href: '/wall-tablet/security' },
    { icon: '⚙️', label: 'Settings', href: '/wall-tablet/settings' },
  ]
</script>

<nav class="dock">
  {#each items as it (it.href)}
    <a class="dbtn" href={it.href} target="_top"><span class="di">{it.icon}</span>{it.label}</a>
  {/each}
</nav>

<style>
  .dock { display: flex; gap: 0.625rem; justify-content: center; }
  .dbtn { flex: 1; max-width: 9.375rem; height: 3rem; border-radius: 0.875rem; background: var(--card); border: 0.0625rem solid var(--card-brd); display: flex; align-items: center; justify-content: center; gap: 0.5rem; font-size: 0.8125rem; font-weight: 600; color: var(--txt); text-decoration: none; }
  .di { font-size: 1.125rem; }
</style>
