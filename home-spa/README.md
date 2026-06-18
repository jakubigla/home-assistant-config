# Home SPA

Bespoke Svelte dashboard replacing the wall-tablet Home view. Built to `www/home-spa/` and served by Home Assistant at `/local/home-spa/`.

Ambient-stage design: dark radial-gradient background, glass cards, state-driven colour (lit lights glow amber, open doors flag red). Sized for the wall tablet (Samsung SM-T595, 1920×1200, 16:10 landscape) with zero scroll; kept light for the tablet's 2018 hardware (no live video — the doorbell is a polled still image).

## Build

```sh
cd home-spa && npm install && npm run build   # outputs to ../www/home-spa
```

or `just spa-build`. **Commit the regenerated `www/home-spa/`** — Home Assistant git-pulls it; there is no build step on the HA side. The build output is excluded from the trailing-whitespace / end-of-file pre-commit hooks so the committed bundle stays byte-exact with Vite's output.

Dev server: `just spa-dev` (or `cd home-spa && npm run dev`).

## Tests & checks

```sh
cd home-spa && npm test                                # vitest
cd home-spa && npx svelte-check --tsconfig ./tsconfig.json
```

## Token

First load on a device prompts for a Home Assistant long-lived access token (Profile → Security → Long-lived access tokens). It is stored in `localStorage` under the key `ha_spa_token`. **Never commit a token.** The wall tablet is a trusted device; a later iteration may move to the OAuth2/IndieAuth flow.

## Panel

Registered in `configuration.yaml` under `lovelace.dashboards.home-spa`, a `mode: yaml` dashboard whose single `type: panel` view embeds the SPA in a full-bleed `iframe` card (`dashboards/home-spa.yaml`). It appears in the sidebar as "Home SPA". (HA's old `panel_iframe` was removed in 2024.6; the iframe-card dashboard is the supported equivalent on current HA.)

## Architecture

- `src/lib/ha.ts` — the only HA-coupling point: WebSocket connection, token auth, live entity-state store, `callService`, camera proxy URL.
- `src/lib/entities.ts` — entity-id constants (`IDS`, `LIGHT_IDS`) and derived-state helpers.
- `src/components/*.svelte` — presentational cards (props in, service-call events out); each stage card is wrapped in a `<svelte:boundary>` so one failing card cannot blank the page.
- `src/App.svelte` — assembles Header → StatusPills → 4×2 card stage → Dock; handles token prompt and reconnect overlay.

## Scope

Pilot: the **Home** view only. The Dock deep-links to the existing tablet views (`/wall-tablet/climate`, etc.) until those are ported. Content is refined live on the tablet.
