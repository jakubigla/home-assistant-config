# Verification Loop

How to prove a dashboard change actually landed and renders right. Load after pushing a dashboard change.

## Table of contents

- [Why verification is non-trivial](#why-verification-is-non-trivial)
- [The verification loop](#the-verification-loop)
- [Commands reference](#commands-reference)
- [Failure modes](#failure-modes)
- [Entity resolution recipe](#entity-resolution-recipe)
- [Reload vs refresh — what triggers what](#reload-vs-refresh--what-triggers-what)

## Why verification is non-trivial

There are three separate caches between a commit and a pixel:

1. **Git remote → HA filesystem.** HA auto-pulls from the current branch every ~5–10 s. Edits are not live until pushed *and* pulled.
2. **HA filesystem → HA runtime state.** Template integrations re-read on `template.reload`. Lovelace dashboards are read on-demand — usually re-read immediately.
3. **HA runtime → browser.** The frontend caches the lovelace config. A browser reload does not necessarily re-fetch; the frontend uses a WebSocket subscription with its own staleness rules.

Any of these can make a freshly-pushed change look like it didn't land.

## The Playwright step is NOT optional

Every dashboard change must end with a Playwright visual check before claiming done. Pre-commit, HA reload HTTP 200, template API sanity, and WebSocket config queries are insufficient — they're all blind to browser cache, card-render errors, and layout collapse. We've shipped "green" non-visual runs that showed a stub on the tablet. If Playwright MCP is broken, surface it to the user and ask to restart the MCP or do a manual browser check — don't silently skip.

## The verification loop

After `git push`:

```
 1. Wait 5–10 seconds for HA to pull.
 2. Query the expected entity or config to confirm the backend has the new file.
 3. Navigate the dashboard in Playwright.
 4. Force-refetch the lovelace config via WebSocket (bypasses frontend cache).
 5. Navigate away and back (clears visual-render cache).
 6. Screenshot. Inspect carefully — compare every row to the spec.
```

### Backend confirmation — step 2

**For a new template sensor**, query its state:

```bash
curl -s -H "Authorization: Bearer $API_ACCESS_TOKEN" \
  http://homeassistant.local:8123/api/states/binary_sensor.<name> \
  | python3 -m json.tool
```

Expected: JSON with `state` that matches the template's expected output. If it returns `{"message": "Entity not found."}`, HA hasn't picked up the file yet — wait and retry, or check the HA error log.

**For a dashboard config change**, fetch the lovelace config through the Playwright-attached hass object:

```javascript
async () => {
  const hass = document.querySelector('home-assistant')?.hass;
  const resp = await hass.connection.sendMessagePromise({
    type: 'lovelace/config',
    url_path: 'wall-tablet',   // or 'mobile-phone'
    force: true,               // <-- bypasses frontend cache
  });
  const view = (resp.views || []).find(v => v.path === 'climate');
  return JSON.stringify({
    section_count: view?.sections?.length,
    first_section_span: view?.sections?.[0]?.column_span,
    card_types: view?.sections?.[0]?.cards?.map(c => c.type),
  });
}
```

If the returned shape matches the new YAML, the backend is ready. The browser view may still be stale — proceed to step 5.

### Force a re-render — step 5

After confirming the backend, navigate away and back:

```javascript
await mcp__playwright__browser_navigate({ url: 'http://homeassistant.local:8123/wall-tablet/home' });
await mcp__playwright__browser_navigate({ url: 'http://homeassistant.local:8123/wall-tablet/climate' });
```

This forces the Lovelace view component to re-mount with the fresh config. Plain `window.location.reload()` often doesn't — the lovelace config subscription picks up the old cached version on remount.

### Screenshot inspection — step 6

**Always save to `.playwright-mcp/` (gitignored), never to the repo root.** Reuse filenames across iterations — `appliances.png`, not `appliances-v1.png`, `appliances-v2.png`, … — so stale screenshots don't accumulate.

```javascript
await mcp__playwright__browser_take_screenshot({
  fullPage: true,
  filename: '.playwright-mcp/<page>.png',
  type: 'png',
});
```

Then inspect every row against the spec. Specifically check:

- Row widths: does the content fill the expected area? No unexpected dead space?
- Card types: is each element the expected component (thermostat vs. chip vs. sparkline)?
- Icons: present and visible? Not muted when they shouldn't be?
- Text truncation: any titles clipped by adjacent elements?
- Numeric formatting: decimal places, °C suffix, correct precision?
- Conditional rows: only the expected variant visible, the other hidden?

Don't trust a pass until every row looks right.

## Commands reference

| Command | When to run | What it does |
|---|---|---|
| `curl .../api/states/<entity>` | After push, to confirm HA picked up a new template | Returns current state + attributes; 404 means not yet pulled/parsed |
| `curl -X POST .../api/services/template/reload -d '{}'` | Template entity missing after expected pull delay | Forces template integration to re-read files |
| `curl -X POST .../api/services/lovelace/reload_resources -d '{}'` | After adding/updating a HACS JS resource | Reloads custom card resources (does NOT reload dashboard YAML) |
| `hass.connection.sendMessagePromise({type: 'lovelace/config', url_path: 'X', force: true})` | To verify dashboard YAML is parsed correctly | Returns the active dashboard config from backend, bypassing frontend cache |
| `browser_navigate(home) → browser_navigate(target)` | To force a stale browser view to re-render | Re-mounts the Lovelace view component |
| `browser_console_messages({ level: 'error' })` | After any push, to catch template/card errors | Reveals Jinja render errors, missing custom cards, etc. |

## Failure modes

| Symptom | Cause | Fix |
|---|---|---|
| `Entity not found` after push | HA hasn't pulled yet | Wait 10 s, retry |
| Template shows `unavailable` forever | Jinja threw or YAML invalid | Read HA error log; check indentation |
| Old layout still shows after push | Browser cached config | Step 5 of the loop (navigate-away-and-back) |
| Old layout still shows even after navigate | Backend still serving old YAML | Step 2/4 — check `lovelace/config` with `force: true` |
| Card renders as `custom:X` text placeholder | HACS resource not loaded | `lovelace/reload_resources` + hard refresh |
| Template works in dev tools, fails in card | `state_attr` returned None; `default` filter didn't catch it | Add `, true` second arg: `\| default('x', true)` |
| Graph title clipped on one card but not its sibling | `history-graph` y-axis label width varies per data range | Switch to `type: sensor` one-per-entity (see cards.md) |
| `phone:` dashboard key rejected on HA start | Lovelace URL path requires hyphen | Rename to `mobile-phone:` |

## Entity resolution recipe

Before editing any dashboard card, resolve the real entity_id. Friendly names and room names are NOT reliable.

**Fastest (MCP):**

```
mcp__HomeAssistant__GetLiveContext
```

Returns all entities grouped by domain. Search the output text for your target area or domain.

**Filtered via API:**

```bash
curl -s -H "Authorization: Bearer $API_ACCESS_TOKEN" \
  http://homeassistant.local:8123/api/states \
  | python3 -c "
import json, sys
for e in json.load(sys.stdin):
    if e['entity_id'].startswith(('climate.', 'humidifier.')):
        print(e['entity_id'], '::', e['attributes'].get('friendly_name',''), '::', e['state'])
"
```

**Full entity detail (what attributes to template on):**

```bash
curl -s -H "Authorization: Bearer $API_ACCESS_TOKEN" \
  http://homeassistant.local:8123/api/states/climate.<name> | python3 -m json.tool
```

Look for `hvac_modes`, `preset_modes`, `current_temperature`, `fan_modes`, etc. before writing chip templates.

## Reload vs refresh — what triggers what

HA has several "reload" mechanisms that each handle different things:

| Action | Reloads |
|---|---|
| **`homeassistant.reload_core_config`** | `configuration.yaml` core blocks only — rarely what you want |
| **`homeassistant.reload_all`** | All reloadable integrations — heavy, usually unnecessary |
| **`template.reload`** | Template sensors/binary_sensors — use after editing a file in `templates/` |
| **`lovelace.reload_resources`** | HACS `/local/` JS resources — only when you install/update a custom card |
| **`input_boolean.reload`**, `input_select.reload`, etc. | That specific input domain |
| **Frontend refresh (⋮ → Refresh)** | Lovelace view re-fetches config — equivalent to `navigate-away-and-back` |
| **HA restart** | Everything — last resort |

Template and lovelace reloads are independent: adding a binary_sensor + referencing it in a dashboard requires both a `template.reload` *and* a dashboard re-fetch (or just wait for HA to auto-reload on next pull).
