<script lang="ts">
  let { onsubmit }: { onsubmit: (token: string) => void } = $props()
  let value = $state('')
</script>

<div class="overlay">
  <div class="box">
    <h2>Connect to Home Assistant</h2>
    <p>Paste a long-lived access token (Profile → Security → Long-lived access tokens).</p>
    <input bind:value placeholder="Long-lived token" />
    <button disabled={!value.trim()} onclick={() => onsubmit(value.trim())}>Connect</button>
  </div>
</div>

<style>
  .overlay { position: fixed; inset: 0; display: grid; place-items: center; background: var(--bg); z-index: 10; }
  .box { background: var(--card); border: 0.0625rem solid var(--card-brd); border-radius: var(--radius); padding: 1.75rem; max-width: 28.75rem; }
  h2 { margin: 0 0 0.5rem; font-size: 1.25rem; }
  p { color: var(--dim); font-size: 0.8125rem; }
  input { width: 100%; padding: 0.625rem 0.75rem; border-radius: 0.625rem; border: 0.0625rem solid var(--card-brd); background: rgba(0,0,0,.3); color: var(--txt); margin: 0.75rem 0; }
  button { padding: 0.625rem 1.125rem; border-radius: 0.625rem; border: none; background: var(--blue); color: #fff; font-weight: 700; cursor: pointer; }
  button:disabled { opacity: .4; }
</style>
