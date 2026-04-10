# Garden

> Automated irrigation for 3 lawn zones and drip irrigation, driven by mode profiles with weather-aware scheduling.

**Package:** `garden` | **Path:** `packages/areas/outdoor/garden/`

## How It Works

### Scheduled Irrigation

Every morning at 6:00 AM, the system checks two things: should it skip (rain, forecast, season), and what should run today (lawn, drip, or both). The active mode determines which days each type runs and for how long.

Irrigation only operates **May through September**. It also skips if it's currently raining or rain is forecasted within 6 hours (using Met.no). The `reason` attribute on the skip sensor makes it easy to see why irrigation was skipped.

### Modes

`input_select.garden_irrigation_mode` controls everything. The mode persists across HA restarts.

| Mode | Lawn | Drip |
|------|------|------|
| **Eco** | 10 min/zone, Mon + Thu | 30 min, Mon + Wed + Fri |
| **Standard** | 15 min/zone, Mon + Wed + Fri | 45 min, weekdays |
| **Intensive** | 20 min/zone, daily | 60 min, daily |
| **Smart** | Auto-selects based on month and temperature | Same logic, different values |

Smart mode ramps up through the season: lighter in May/September, heavier in July, and overrides to Intensive-level during heatwaves (>30°C).

**Adding a new mode** requires just two edits: add a profile entry in `garden_irrigation_profile.yaml` and add the option to `input_select` in `config.yaml`. See the inline docs in the profile template for details.

### How Valves Are Controlled

The **auto-off automation** is the single source of truth for durations. Any valve that opens — whether via schedule, script, or HomeKit — gets automatically closed after the profile-driven duration. Scripts don't manage durations; they just open valves and wait for them to close.

The **lawn irrigation script** runs zones sequentially: opens zone 1, waits for auto-off to close it, pauses 5 seconds, opens zone 2, and so on. The **full irrigation script** chains the lawn script followed by drip.

### On-Demand Control

All 4 valves and 2 sequence scripts are exposed to **HomeKit**:

- Open any individual valve — auto-off handles the duration
- Close any valve — stops immediately
- Trigger `script.garden_lawn_irrigation` — runs all 3 zones sequentially
- Trigger `script.garden_full_irrigation` — lawn zones then drip

## Gotchas

- **Valves can't run simultaneously** — the Tuya controller doesn't support it. The sequential scripts enforce this, but if you manually open two valves via HomeKit, the hardware may not behave as expected.
- **Auto-off reads duration at valve-open time** — changing the mode mid-run won't affect an already-running valve, but the next valve in a sequence will pick up the new duration.
- **Forecast attribute access** — `weather.forecast_home` forecast attribute may need adaptation for newer HA versions that use the `weather.get_forecasts` service instead.
- **Zones 5-8 on the Tuya controller are unused** — the hardware supports 4 physical zones only.

## Entities

**Valves:** `valve.lawn_sprinkler_zone_1`, `valve.lawn_sprinkler_zone_2`, `valve.lawn_sprinkler_zone_3`, `valve.drip_irrigation`

**Mode:** `input_select.garden_irrigation_mode` — Eco / Standard / Intensive / Smart

**Sensors:**
- `binary_sensor.garden_should_skip_irrigation` — on = skip (check `reason` attribute)
- `sensor.garden_irrigation_profile` — resolved durations and schedule (check `lawn_duration`, `drip_duration`, `lawn_today`, `drip_today` attributes)

**Scripts:**
- `script.garden_lawn_irrigation` — zones 1→2→3 sequential
- `script.garden_drip_irrigation` — drip only
- `script.garden_full_irrigation` — lawn then drip

## Dependencies

- `binary_sensor.raining` — current rain state (from `packages/bootstrap/templates/`)
- `weather.forecast_home` — Met.no weather forecast for rain lookahead and temperature
- `sun.sun` — indirectly via season logic (month-based)

## File Index

| File | Purpose |
|------|---------|
| `config.yaml` | Package entry, input_select definition |
| `automations/garden_valve_auto_off.yaml` | Auto-closes valves after profile duration |
| `automations/garden_scheduled_irrigation.yaml` | Daily 6 AM trigger with skip logic |
| `scripts/garden_lawn_irrigation.yaml` | Sequential zones 1→2→3 |
| `scripts/garden_drip_irrigation.yaml` | Drip valve with wait-for-close |
| `scripts/garden_full_irrigation.yaml` | Chains lawn + drip scripts |
| `templates/garden_should_skip_irrigation.yaml` | Skip logic (rain, forecast, season) |
| `templates/garden_irrigation_profile.yaml` | Mode → duration/days mapping |
