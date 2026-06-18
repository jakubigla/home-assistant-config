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
  .box { background: var(--card); border: 1px solid var(--card-brd); border-radius: var(--radius); padding: 28px; max-width: 460px; }
  h2 { margin: 0 0 8px; font-size: 20px; }
  p { color: var(--dim); font-size: 13px; }
  input { width: 100%; padding: 10px 12px; border-radius: 10px; border: 1px solid var(--card-brd); background: rgba(0,0,0,.3); color: var(--txt); margin: 12px 0; }
  button { padding: 10px 18px; border-radius: 10px; border: none; background: var(--blue); color: #fff; font-weight: 700; cursor: pointer; }
  button:disabled { opacity: .4; }
</style>
