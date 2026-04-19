---
name: ha-dashboards
description: Build, redesign, or polish Home Assistant Lovelace dashboards in this repo (`dashboards/**/*.yaml`). Use when the user asks to "add/create/redesign/polish a tab/view/page/dashboard", fix a layout that looks narrow or wrong, swap card types, add seasonal/conditional rows, or work with Mushroom/Bubble/weather/thermostat cards. Covers the non-obvious grid/column/visibility mechanics that cause silent layout failures, plus the push→HA pull→Playwright verify loop and entity-resolution traps specific to this HA config.
---

# Home Assistant Dashboards

Procedural knowledge for Lovelace YAML work in this repo. Read this before touching any file under `dashboards/`.

## When to use what

- **Non-trivial redesigns** (new tab, rebuild a view, swap layout paradigm) — run `superpowers:brainstorming` first. Collaborate on a spec before writing code.
- **Tweaks** (add a card, change an icon, fix a label) — go direct. No brainstorming.
- **Area/room documentation** after edits — use the `/ha-area-docs` skill.

## Workflow

1. **Resolve entities before coding.** Friendly names lie. `climate.living_room` in this repo is actually the Midea AC, friendly name "AirCon_53E4", not the thermostat. Query `mcp__HomeAssistant__GetLiveContext` or `/api/states` and filter by the domain/area you care about. Never infer an entity_id from the room name alone.
2. **Edit YAML.** See [references/cards.md](references/cards.md) for card selection and [references/layout.md](references/layout.md) for sections/grid mechanics.
3. **Lint.** `uv run pre-commit run --all-files`. Note: `.yamllint` ignores `dashboards/`, but the pre-commit chain still runs other checks.
4. **Commit on a feature branch.** Never push to `main`. A PR already exists for work-in-progress redesign branches — check with `gh pr list --head <branch>` before opening a new one.
5. **Push.** HA auto-pulls from the current branch within ~5–10s. Local file edits are not live until pushed.
6. **Verify live via Playwright.** See [references/verify.md](references/verify.md). Screenshots alone can fool you with stale frontend caches — always force-refetch the lovelace config through the WebSocket bridge and re-navigate before screenshotting.

## The #1 gotcha: section width

`type: sections` with `max_columns: 1` caps the single section at ~500 px wide. On a landscape tablet, this leaves most of the viewport as dead space. Symptom: "content looks narrow and there's huge whitespace on the sides".

**The correct idiom for a single-column, full-width dashboard:**

```yaml
type: sections
max_columns: 3
sections:
  - column_span: 3
    cards:
      - type: horizontal-stack
        grid_options:
          columns: full      # <-- CRITICAL: without this, the stack takes ~1/4 row
        cards: [...]
```

Three levers must line up:

1. `max_columns: 3` (or more) on the view — lets the grid be wide.
2. `column_span: 3` on the section — makes the section span the full grid width.
3. `grid_options: { columns: full }` on **every** card inside the section — without this, each card defaults to ~3/12 cells and rows fragment across columns.

Skipping any one produces a broken layout. See [references/layout.md](references/layout.md) for the full decision tree and alternative patterns (multi-section natural flow, panel view, etc.).

## The #2 gotcha: card type for trends

`type: history-graph` with **multiple** entities renders each entity as a separate stacked sparkline panel. Two rooms × two entities = four fat graph panels with frequent title clipping.

For at-a-glance trend rows, prefer `type: sensor` with `graph: line`:

```yaml
- type: sensor
  entity: sensor.living_room_hygro_temperature
  graph: line
  hours_to_show: 24
  name: Living Room Temp
```

Compact: big current number + small inline sparkline. Put four across in a `horizontal-stack`. Covered fully in [references/cards.md](references/cards.md).

## The #3 gotcha: weather card

`custom:mushroom-template-card` + weather templates renders as a thin text strip — fine on a phone chip row, terrible as a climate-tab hero. For hero-grade weather, use the built-in:

```yaml
- type: weather-forecast
  grid_options:
    columns: full
  entity: weather.forecast_home
  show_current: true
  show_forecast: true
  forecast_type: daily
```

Big icon, current conditions, 5-day strip. `weather.forecast_home` is the canonical entity in this repo.

## The #4 gotcha: mutually-exclusive `visibility` on Mushroom template-card pairs

A pair of `custom:mushroom-template-card`s with complementary `visibility:` templates (running-hero + idle-hero) inside a `vertical-stack` silently disappears from the DOM — **both** cards, even when one's condition is true. Verified 2026-04-19 on Mushroom 5.1.1 / HA 2026.4.3. Non-visual checks (WebSocket config, template API, reload 200) all pass — only Playwright DOM inspection catches it.

**Don't:**

```yaml
# ❌ Broken — both disappear
- type: vertical-stack
  cards:
    - type: custom:mushroom-template-card
      primary: "{{ time_left }}m left"
      visibility: [{ condition: template,
        value_template: "{{ states('sensor.x') not in ('stop', 'unknown', 'unavailable') }}" }]
    - type: custom:mushroom-template-card
      primary: "Idle"
      visibility: [{ condition: template,
        value_template: "{{ states('sensor.x') in ('stop', 'unknown', 'unavailable') }}" }]
```

**Do:** one always-visible card that branches content via Jinja:

```yaml
- type: custom:mushroom-template-card
  primary: >-
    {% set ms = states('sensor.x') %}
    {% if ms not in ('stop', 'unknown', 'unavailable') %}{{ time_left }}m left
    {% else %}Idle{% endif %}
  secondary: >-
    {% set ms = states('sensor.x') %}
    {% if ms not in ('stop', 'unknown', 'unavailable') %}{{ job_state | title }}
    {% else %}Last: {{ last_run }}{% endif %}
  icon_color: >-
    {% if states('sensor.x') not in ('stop', 'unknown', 'unavailable') %}blue
    {% else %}teal{% endif %}
```

`visibility:` on a **single** Mushroom card (shown only when a condition is met — error card, warning chip) still works. `visibility:` on a `horizontal-stack` or `vertical-stack` wrapper also works. The breakage is specifically two sibling Mushroom template-cards with complementary conditions.

## Conditional / seasonal layouts

Swap rows by season, time of day, occupancy, etc. via a template `binary_sensor` + per-card `visibility:` blocks.

**Template sensor location:** `packages/bootstrap/templates/binary_sensors/<name>.yaml`. Auto-included via `!include_dir_list`. Flat structure — no `template:` wrapper:

```yaml
---
binary_sensor:
  - name: cooling_season         # snake_case, no unique_id (convention)
    state: >
      {{ now().month in [5, 6, 7, 8, 9] }}
    icon: >
      {% if is_state('binary_sensor.cooling_season', 'on') %}
        mdi:snowflake
      {% else %}
        mdi:radiator
      {% endif %}
```

**Tip:** Make the icon template read the sensor's own state (`is_state('binary_sensor.<name>', 'on')`) instead of re-evaluating the `state:` expression. DRY, and future boundary changes become one-line edits. Matches `outdoor_is_dark.yaml` / `raining.yaml` peers in the same folder.

**Visibility usage in cards:**

```yaml
- type: horizontal-stack
  grid_options:
    columns: full
  visibility:
    - condition: state
      entity: binary_sensor.cooling_season
      state: "off"       # winter variant; use "on" for summer variant
  cards: [...]
```

Two mutually-exclusive `horizontal-stack` blocks sharing an entity — only one renders at a time. This is the idiomatic Lovelace pattern; `type: conditional` adds an extra wrapper that often interferes with section-view layout.

## Jinja traps in card templates

- **`| default('x')` does NOT catch `None`.** `state_attr('entity', 'hvac_action')` returns Python `None` when the entity is unavailable — not undefined. Use `| default('x', true)` (second arg = catch all falsy):

  ```jinja
  {{ state_attr('climate.main_heating', 'hvac_action') | default('idle', true) | capitalize }}
  ```

- **Guard numeric attrs.** `| float(0) | round(N)` handles both `None` and non-numeric strings. Skip the guard and the card crashes when the entity is briefly unavailable after restart.

- **88-char line limit (yamllint warning).** Ternary expressions like `{{ 'a' if cond else 'b' }}` commonly overflow. Use an `{% if %}/{% else %}/{% endif %}` block, which also matches peer style in `templates/binary_sensors/`.

## Mushroom chip conventions (from `home.yaml`)

For `custom:mushroom-template-card` chips:

- **`primary` is the big text, `secondary` is the subtitle.** On a climate page where the value matters (e.g., `23.8°C · 29%`), put the data in `primary` and the room name in `secondary`. On a home/overview page where room identity matters first, invert.
- **`layout: horizontal`** for a chip-shaped row item; `vertical` for a tall tile (bigger icon, text stacked).
- **`icon_color:` dynamic**: template returns one of the Mushroom color tokens (`blue`, `amber`, `orange`, `disabled`, ...). Use `disabled` (muted grey) instead of `none` when signalling "off".
- **`tap_action: { action: more-info, entity: <other> }`** overrides the default more-info target. Use when the card's main `entity:` is a sensor but you want the tap to open the related device (e.g., chip shows room temperature, tap opens humidifier).

Reference patterns already in this repo:

- Weather strip on a phone row: `dashboards/tablet/home.yaml:89-108`
- Per-room climate chip with dual card_mod: `dashboards/tablet/home.yaml:440-486`
- Door/alarm/outdoor chips: `dashboards/tablet/outdoor.yaml:18-42`, `181-226`

## Dashboard URL paths

Lovelace dashboard keys must contain a hyphen (HA constraint). This repo's slugs:

- `/wall-tablet/<tab>` — tablet dashboard (`dashboards/tablet/*.yaml`)
- `/mobile-phone/<tab>` — phone dashboard (`dashboards/phone/*.yaml`)

The `phone:` key fails to load ("Url path needs to contain a hyphen"). The repo uses `mobile-phone:` historically.

## What NOT to put on a dashboard

- **Secrets or tokens** — even in card_mod. Use `!secret` references.
- **Curtain controls on a Climate page** — curtains are not climate. Separate concerns.
- **Standalone humidifier controls as primary cards** — humidifiers here spend most of their life `unavailable`. Show humidity as a chip, open more-info on tap for control.

## References

- [references/layout.md](references/layout.md) — `type: sections` grid mechanics, column_span, grid_options, panel view alternatives
- [references/cards.md](references/cards.md) — card-type decision matrix with copy-paste snippets
- [references/verify.md](references/verify.md) — Playwright + HA refresh loop, force-refetch recipe, common failure modes
