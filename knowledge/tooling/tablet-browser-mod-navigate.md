---
summary: Kitchen tablet stuck on HA splash = stale Fully WebView cache (clearCache fixes, keeps login); wake before navigate.
before_action:
  - About to call browser_mod.navigate (or popup) targeting the kitchen wall tablet
  - About to press the Fully Kiosk clear-browser-cache or load-start-url button
  - About to prune browser_mod browsers or devices
  - About to debug why the kitchen wall tablet is not loading Home Assistant
on_symptom:
  - "kitchen tablet shows only the Home Assistant logo / boot splash, never the dashboard"
  - "tablet stuck loading Home Assistant after a core update"
  - "tablet clock / screensaver view unstyled: raw markdown table, small clock, left-aligned"
  - "card_mod styles missing on the tablet but fine on a laptop"
  - "tablet ignores a frontend or lovelace resource change after HA restart"
  - "browser_mod.navigate returns 200 but the tablet does not move"
  - "doorbell popup never appears on the kitchen tablet"
  - "sensor.browser_mod_<id>_browser_path unavailable while screen is off"
  - "many unavailable light.browser_mod_*_screen / sensor.browser_mod_* entities"
  - "sensor.browser_mod_<tablet id>_* unavailable for days while Fully Kiosk entities look healthy"
---

# Tablet + browser_mod gotchas

Tablet = Galaxy Tab A 2018 (SM-T595, Android 10, Fully Kiosk 1.61), 192.168.1.115, HA user
`Centrala`, start URL `http://192.168.1.183:8123/`. browser_mod id (stable since 2026-08-11,
survived the 2026-09-16 cache clear): `browser_mod_c6830995_0bc293d0`.

- **Splash-only screen = stale WebView cache, not HA.** Fully's WebView serves a dead HA app shell
  from its own cache and makes **zero** network requests — HA sees nothing, the WebView is not hung
  (a different-origin page, e.g. observer `http://192.168.1.183:4357/`, renders fine). Fix:
  `button.galaxy_tab_a_2018_10_5_clear_browser_cache` then `..._load_start_url`. Cache clear keeps
  HA login and the browser_mod id (2026-09-16: earlier "id rotates on cache clear" was wrong — the
  2026-08-11 rotation came from something else). Can be triggered remotely, no re-login needed.
- **Prove it before clearing:** `logger.set_level {"aiohttp.access": "info"}`, force
  `load_start_url`, read `GET /api/hassio/core/logs` (`Range: entries=:-2000:`) for
  `192.168.1.115` lines — none = cache theory confirmed; revert with `"warning"`. `/api/error_log`
  is gone in 2026.9. `ss -tni | grep 192.168.1.115` on the box shows the frozen connection.
- **How long has it been dead:** `.storage/auth` → refresh token with `last_used_ip`
  192.168.1.115; `last_used_at` is the last time the tablet frontend authenticated (2026-09-16 it
  was 8 days stale while Fully entities looked healthy — Fully health ≠ page health).
- **Fully REST from the box beats HA entities for diagnosis:** host + password in
  `.storage/core.config_entries` (domain `fully_kiosk`); `?cmd=deviceInfo&type=json`,
  `getScreenshot` (HA `camera_proxy` returns 503), `loadUrl&url=`, `stopScreensaver`,
  `clearCache`, `loadStartUrl`, `listSettings`. Screensaver playlist is `/wall-tablet/clock`
  (same origin — shares the broken cache), so screenshots while `isInScreensaver` show that view.
- **Fully drops the browser_mod websocket while the screen is off** — all
  `sensor.browser_mod_<id>_*` go `unavailable`. Order matters: `switch.turn_on
  switch.kitchen_dashboard_screen` → `wait_template` on `…_browser_path != unavailable` (≤15 s) →
  `browser_mod.navigate`.
- **`button.…_load_start_url` loads HA root `/`**, which redirects to the user's default dashboard
  (`/wall-tablet/home`). Use it to force a lovelace config re-fetch; use `browser_mod.navigate` for
  in-app moves. `browser_mod.navigate` to an id absent from `.storage/browser_mod.storage` is a
  silent 200 no-op.
- **Prune stale browsers with WS `{"type":"browser_mod/unregister","browserID":"browser_mod_…"}`**
  — removes the store entry and its device. Pick by `last_seen` in `browser_mod.storage`. Other
  ids seen 2026-09-16 are phones/laptops (`meta` is always `default`; identify by the
  `_browser_useragent` sensor, tablet UA contains `SM-T595`).
- **Tablet caches index.html itself.** After an HA core update or any `frontend:` /
  `lovelace.resources` change + restart, the tablet keeps booting the OLD index (zero requests to
  HA) until a Fully cache clear — a new `extra_module_url` simply never loads. Clear cache +
  `load_start_url` right after such restarts (2026-09-16: needed twice in one evening).
- **card_mod on a fresh tablet load is a race HA does not guard.** Lovelace resources are not
  awaited before views render; the slow tablet painted `/wall-tablet/clock` before card-mod
  arrived and every `card_mod:` block was silently ignored (default fonts, visible `a | b`
  table header) while SPA navigation to the same view was styled. Fix in place: card-mod loads
  via `frontend.extra_module_url` (packages/frontend/config.yaml, `?v=` cache-buster must track
  the HACS version), NOT as a lovelace resource. Fully screensaver = fresh load every time.
- **DOM probe on the tablet without adb:** `browser_mod.javascript` (`browser_id` + `code`) with
  code that POSTs its findings to `/api/services/persistent_notification/create` using
  `JSON.parse(localStorage.hassTokens).access_token`; read back with WS
  `persistent_notification/get` (not in `/api/states`). Wait ≥35 s after a fresh load or the
  browser is not registered yet and the call is a silent no-op. Dismiss the notification after.
- **Fully is unlicensed** (`isLicensed: false`, red "Please Get a License" overlay) — cosmetic, not
  a loading fault.
