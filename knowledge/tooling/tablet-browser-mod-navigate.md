---
summary: Tablet browser_mod id rotates on cache clear; socket drops while screen is off — wake first, then navigate.
before_action:
  - About to call browser_mod.navigate (or popup) targeting the kitchen wall tablet
  - About to press the Fully Kiosk clear-browser-cache or load-start-url button
  - About to prune browser_mod browsers or devices
on_symptom:
  - "browser_mod.navigate returns 200 but the tablet does not move"
  - "doorbell popup never appears on the kitchen tablet"
  - "sensor.browser_mod_<id>_browser_path unavailable while tablet screen is off"
  - "many unavailable light.browser_mod_*_screen / sensor.browser_mod_* entities"
---

# Tablet + browser_mod gotchas

- **The tablet's browser_mod id lives in the tablet's browser storage.** Fully Kiosk "Clear browser
  cache" (`button.galaxy_tab_a_2018_10_5_clear_browser_cache`, last 2026-08-11) rotates it; the old
  id stays in the device/entity registry but not in `.storage/browser_mod.storage`, and
  `browser_mod.navigate` to it is a silent 200 no-op. Current id (2026-09-07):
  `browser_mod_c6830995_0bc293d0` (UA `Android 10; SM-T595`). Verify via
  `sensor.browser_mod_<id>_browser_useragent` while the screen is on.
- **Fully drops the browser_mod websocket while the screen is off** — all `sensor.browser_mod_<id>_*`
  go `unavailable`. Order matters: `switch.turn_on switch.kitchen_dashboard_screen` → `wait_template`
  on `…_browser_path != unavailable` (≤15 s) → `browser_mod.navigate`.
- **`button.…_load_start_url` loads HA root `/`**, which redirects to the user's default dashboard
  (currently `/wall-tablet/home`). Use it to force a lovelace config re-fetch on the tablet; use
  `browser_mod.navigate` for in-app moves.
- **Prune stale browsers with WS `{"type":"browser_mod/unregister","browserID":"browser_mod_…"}`**
  — removes the store entry and its device. Pick by `last_seen` in `browser_mod.storage` (0 or
  weeks old); 17 pruned 2026-09-07, 6 kept.
