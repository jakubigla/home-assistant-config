# Garage View — Design Spec

Date: 2026-05-25
Branch: `chore/may-fixes`

## Goal

Add a dedicated **Garage** view to both the tablet and phone dashboards. Surface the
BMW CarData vehicle card (i4 M50) and consolidate garage-door control + status, EV
charging detail, garage room sensors, and trip/range stats in one place. The main
tablet Home view is full, so the vehicle card gets its own tab rather than being
squeezed in.

## Resolved facts (verified against live HA)

### BMW CarData
- Custom card: `custom:bmw-cardata-vehicle-card`. Auto-registered by the integration —
  **no HACS frontend resource install needed**.
- Required config: `device_id: 95997f834d22c4835e55ba4bc7524717` (vehicle = **i4 M50**, an EV).
- The card already renders: vehicle image, battery/range bar, lock/door/window/alarm
  indicators, inline map, and quick-info button tiles. **Do not duplicate these** in
  surrounding cards.
- Defaults used: `show_image`, `show_range`, `show_indicators`, `show_map`, `show_buttons`
  all `true`. `soc_source` left at default (`soc`).

### Garage door
- Control entity: `cover.garage_door` — `device_class: garage`, `supported_features: 11`
  (open / close / stop). **This is the control path** (per user decision; the raw
  `switch.garage_door` Satel pulse is intentionally NOT exposed here).
- Status zone: `binary_sensor.garage_door` (`on` = open, `off` = closed).
- Transit state: `input_select.garage_door_state` — options `idle` / `opening` / `closing`.
- Motion: `binary_sensor.garage_motion` (friendly "Garage Sensor").

### EV charging / vehicle entities (all `sensor.i4_m50_*`)
- `battery_hv_state_of_charge` — current HV SoC (%), currently `80`.
- `battery_ev_target_state_of_charge` — target SoC (%), `80`.
- `charging_ev_predicted_state_of_charge` — predicted SoC (%).
- `battery_ev_charging_current_limit` — charge current limit (A), `32`.
- `charging_ev_charging_state` — e.g. `NOCHARGING`.
- `charging_ev_charging_method` — e.g. `NOCHARGING`.
- `charging_port_plug_lock_state` — e.g. `CHARGING_CABLE_NOT_LOCKED`.
- `range_ev_estimate_during_charging` — range (km), `261`.
- `vehicle_mileage` — odometer (km), `22239`.
- `trip_battery_charge_level_at_end_of_trip` — last-trip end SoC (%).

These string states can be `unknown` / `INVALID` / `NOCHARGING`; templates must guard
and present them cleanly.

## Architecture

Two new view files, included from the two dashboard entrypoints. No shared partials —
the views diverge enough (3-col vs 1-col) that duplication is cheaper than abstraction.

### File changes
- **New** `dashboards/tablet/garage.yaml`
- **New** `dashboards/phone/garage.yaml`
- **Edit** `dashboards/tablet.yaml` — insert `- !include tablet/garage.yaml` immediately
  after the `outdoor` include (before `security`).
- **Edit** `dashboards/phone.yaml` — add `- !include phone/garage.yaml` to the top-level
  views list (after `energy`, before the room subviews).

### Tablet view (`dashboards/tablet/garage.yaml`)

- Header: `title: Garage`, `path: garage`, `icon: mdi:garage`.
- `type: sections`, `max_columns: 3`. Single section, `column_span: 3`.
- Every card gets `grid_options: { columns: full }` (the repo's full-width idiom).

Rows top→bottom:

1. **Vehicle hero** — `custom:bmw-cardata-vehicle-card` with the device_id above.
2. **Garage door** — `horizontal-stack`:
   - `custom:mushroom-cover-card` for `cover.garage_door`, `show_buttons_control: true`,
     `layout: horizontal`, name "Garage Door".
   - `custom:mushroom-template-card` status: single card, content branches on transit.
     - icon/color: green `mdi:garage` when closed, red `mdi:garage-open` when open;
       amber `mdi:garage-alert` while `input_select.garage_door_state` is
       `opening`/`closing`.
     - primary: `Opening…` / `Closing…` during transit, else `Open` / `Closed`.
     - secondary: last-changed time of `binary_sensor.garage_door`.
   - `custom:mushroom-template-card` for `binary_sensor.garage_motion`
     (motion vs clear, blue/disabled).
3. **EV charging** — `horizontal-stack` of `mushroom-template-card` tiles:
   - Charging state (humanize `NOCHARGING`/`CHARGING`/… → title-case, dash for invalid).
   - SoC: primary `{{ hv_soc }}%`, secondary `Target {{ target }}%`.
   - Charge current limit `{{ n }} A`.
   - Predicted SoC `{{ n }}%`.
   - Plug lock state (humanize underscore-caps).
4. **Trip / range** — `horizontal-stack` of tiles:
   - Mileage `{{ n }} km` (thousands-formatted).
   - Range estimate `{{ n }} km`.
   - Last-trip end charge `{{ n }}%`.

### Phone view (`dashboards/phone/garage.yaml`)

- Header: `title: Garage`, `path: garage`, `icon: mdi:garage`. **Top-level tab**, NOT a
  subview (`subview` omitted) — it's a primary page, unlike the room subviews.
- `type: sections`, `max_columns: 1`.
- Rows (stacked, single column):
  1. `custom:bmw-cardata-vehicle-card` (same device_id).
  2. `custom:mushroom-cover-card` for `cover.garage_door` + the same garage status
     template card.
  3. Condensed charging chips (`mushroom-chips-card`): SoC/target, charging state,
     range.
  4. Mileage + last-trip chips.

## Template / Jinja rules (from ha-dashboards skill)

- Guard every numeric attr: `| float(0) | round(0)`; never assume a value is present
  (entities go `unavailable` briefly after restart).
- Treat string states `unknown`, `unavailable`, `INVALID`, `NOCHARGING`, `None`, `''`
  as "no data" → render a dash `—`, not the raw token.
- Humanize SCREAMING_SNAKE states: `.replace('_',' ') | title`.
- One always-visible card that branches content via `{% if %}` for the garage transit
  state — NOT a pair of mutually-exclusive Mushroom cards with complementary
  `visibility:` (documented breakage on Mushroom 5.1.1).
- Keep template lines ≤ 88 chars; prefer `{% if %}/{% else %}/{% endif %}` over long
  ternaries.

## Verification

1. `uv run pre-commit run --all-files`.
2. Commit on `chore/may-fixes` (feature branch; never `main`). Check `gh pr list --head
   chore/may-fixes` before opening a new PR.
3. Push (HA auto-pulls ~5–10s). Existing-dashboard YAML edits auto-reload; no restart
   needed (the dashboards are already registered).
4. Playwright verify both views: force-refetch lovelace config over WebSocket, navigate
   to `/wall-tablet/garage` and `/mobile-phone/garage`, screenshot into
   `.playwright-mcp/`. Confirm: BMW card renders (not an error card), garage cover
   buttons present, charging tiles show clean values (no raw `NOCHARGING`/`INVALID`).

## Out of scope

- Garage lights (none confirmed in the garage area during entity sweep; add later if
  they exist).
- `switch.garage_door` Satel pulse fallback (intentionally omitted).
- Garage temperature/environment sensor (none found).
- Any new template/helper entities — this is dashboard-only.
