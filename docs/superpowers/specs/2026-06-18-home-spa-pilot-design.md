# Home View SPA Pilot — Design

**Date:** 2026-06-18
**Status:** Approved (design), pending implementation plan
**Scope:** Pilot — Home view only. Proves the stack for a later full reskin of the tablet dashboard.

## Goal

Replace the wall-tablet **Home** view with a bespoke, Claude-designed single-page app, hosted inside Home Assistant. It must:

- Render a refreshing "ambient stage" aesthetic (locked direction B v2) — calm hero + information-dense glass cards.
- Fit the wall tablet's screen exactly (**1920×1200, 16:10 landscape**) with **zero scroll**.
- Be light enough for the tablet's weak 2018 hardware (Snapdragon 450, 3 GB RAM): minimal blur/filters, few DOM nodes, no heavy live video.
- Be glanceable on wake — the tablet powers on via motion sensor on arrival, so the first ~2 seconds must convey home state instantly.

This pilot deliberately covers **one** view to prove the end-to-end stack (auth, live state, service calls, deploy, design system) before porting the remaining nine tablet views.

## Target Device

- Samsung Galaxy Tab A 2018 (SM-T595): 10.5", **1920×1200 px, 16:10**, Snapdragon 450, 3 GB RAM, Android.
- Usable fullscreen area ≈ 1920×1120 after Android status bar. Design to 16:10, treat the design as edge-to-edge.
- Wakes on motion (not always-on) → prioritize fast first-paint and glance-readability over idle ambiance.

## Approach

A static Svelte SPA, built to `dist/`, hosted from Home Assistant's `config/www/` and surfaced as a sidebar panel. It talks to HA over the WebSocket API using a long-lived access token stored in the browser.

### Tech stack
- **Svelte + Vite** — tiny reactive bundle, ideal for live entity state on weak hardware.
- **`home-assistant-js-websocket`** — official HA WS client for auth, state subscription, and service calls.
- TypeScript.

### Hosting & deploy
- Source SPA lives in the repo at `home-spa/` (Vite project; own `package.json`).
- Build output goes to `config/www/home-spa/` (served by HA at `/local/home-spa/`).
- Built `dist/` is committed so HA's git-pull serves it without a build step on the HA side. (Build runs locally / in CI before commit.)
- Panel registered in `configuration.yaml`. Use `panel_custom` with an iframe wrapper, or `panel_iframe` pointing at `/local/home-spa/index.html`, giving a fullscreen sidebar entry. The dashboard-key hyphen rule does **not** apply to panels, but use a hyphenated key anyway for consistency.

### Authentication
- **Long-lived access token**, generated in the HA user profile.
- Stored in `localStorage`. On first load, if no token present, prompt the user to paste one.
- Token is **never committed** to the repo. The wall tablet is a trusted device, so this is acceptable for the pilot. (A later iteration may move to the OAuth2/IndieAuth flow for multi-user cleanliness.)

### Camera (doorbell)
- `camera.doorbell_rtsp` rendered as a **polled still image** (~1–2 s refresh) via HA's camera proxy URL, not a live HLS stream — far lighter on the 2018 GPU. Live stream is a possible later upgrade.

## Architecture & Components

Design for isolation: a single HA-coupling module, a derived-state module, and dumb presentational cards that take state as props and emit service-call events.

- **`lib/ha.ts`** — the only point coupled to Home Assistant. Owns: WS connection + auth (token from `localStorage`), the subscribed entity-state store, and a `callService(domain, service, data)` wrapper. Handles reconnect with backoff.
- **`lib/entities.ts`** — maps entity ids to friendly config and computes derived values (lights-on count, perimeter door summary, cooling/heating season, "ready to arm" rollup). Keeps entity ids in one place.
- **Presentational components** (each one purpose, props in / events out, mockable in isolation):
  - `Header` — clock, date, weather (temp/wind/humidity), two person avatars with presence dots.
  - `StatusPills` — alarm-ready rollup, open-door warnings, perimeter-closed summary, occupancy, active scene.
  - `LightsCard` — 8-light grid + all-off; ON glows amber; tap toggles, hold opens brightness/color control.
  - `ClimateCard` — living room + bedroom temp/humidity/humidifier; tap opens climate control.
  - `MediaCard` — living-room TV now-playing + transport (prev / play-pause / next, volume).
  - `DoorbellCard` — polled still image with LIVE badge; tap opens larger view.
  - `CurtainsCard` — ground-floor + bedroom cover position bars.
  - `AppliancesCard` — washer / dryer / two vacuums live state.
  - `QuickPlayCard` — three music scripts (Discover Weekly, Random, Last Played).
  - `QuickCleanCard` — two vacuum scripts (Mudroom, Kitchen) + "today" lights summary.
  - `Dock` — five buttons deep-linking to the existing HA tablet views (`/wall-tablet/climate`, `/media`, `/outdoor`, `/security`, `/settings`) until those views are ported to the SPA.

### Layout
- Edge-to-edge flex column: Header → StatusPills → Stage (4×2 grid of cards) → Dock.
- Sized to 16:10 so the eight cards + header + dock fill the viewport with no scroll.

## Entity Inventory (Home view surface)

People `person.jakub`, `person.sona`; alarm `alarm_control_panel.main`, `binary_sensor.home_ready_to_arm` (attrs `open_doors_count`, `occupied_zones_count`); doors `binary_sensor.terrace_left_door`, `terrace_main_door`, `balcony_door`, `garage_door`; weather `weather.forecast_home`; scene `input_select.living_room_scene`; camera `camera.doorbell_rtsp`; lights `light.toilet`, `living_room_corner_lamp`, `kitchen`, `bedroom`, `bathroom_main`, `ensuite_bathroom`, `hall_bulbs`, `stairway` (+ all-off via `light.turn_off` target `all`); media `media_player.living_room_tv`; music scripts `script.music_play_discover_weekly`, `music_play_random_playlist`, `music_play_last_played`; vacuum scripts `script.vacuum_clean_mudroom`, `vacuum_clean_kitchen`; climate `sensor.living_room_hygro_temperature`/`_humidity` + `input_boolean.living_room_humidification_active` + `climate.living_room`, bedroom equivalents + `climate.bedroom`; covers `cover.ground_floor`, `cover.bedroom`; appliances `binary_sensor.washer_power`, `tumble_dryer_power`, `vacuum.dreamebot_l10_ultra`, `vacuum.x40_master`.

Entity ids must be verified against the live HA instance during implementation (MCP / hass-cli / API), not assumed from the YAML.

## Error Handling

- **WS disconnect** → reconnect with backoff; show a non-blocking "reconnecting" overlay; cards keep last-known state.
- **Missing entity** → the owning card degrades to an "unknown" state and never throws (a crashing card must not take down the page — cf. the mass-player-card lesson).
- **Bad / expired token** → clear it and re-prompt.

## Testing

- Component-level tests with mock `hass` state (each card renders and emits correct service calls).
- Manual on-device verification after deploy: push → HA git-pull → load on the tablet → Playwright visual check.

## Out of Scope (pilot)

- The other nine tablet views (reachable via the Dock's deep-links for now).
- Multi-user OAuth login flow.
- Add-on packaging / ingress.
- Live (HLS) camera streaming.
- **Final content of the Home screen** — the card set is a strong starting point; content is refined live on the real tablet once the stack runs, because usefulness-vs-noise is clearer on the actual wall with real state.

## Risks

- **Weak hardware** — keep effects cheap, DOM small; verify frame rate on-device, not just on desktop.
- **Token in localStorage** — acceptable for a trusted wall tablet; revisit for multi-user.
- **Committed `dist/`** — keep the build reproducible; document the build step so source and output don't drift.
