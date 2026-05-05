# Garden

> Automated irrigation for 3 lawn zones and drip irrigation, driven by mode profiles with weather-aware scheduling.

**Package:** `garden` | **Path:** `packages/areas/outdoor/garden/`

## How It Works

### Scheduled Irrigation

Single daily trigger:

- **04:00** — picks lawn+drip (full), lawn-only, or drip-only based on profile + per-type skip sensors. Drip runs once per day on the same days as lawn.

Per-type skip:

- **Lawn skip** — lawn season (May–Sep), raining now, or rain forecast within 6h.
- **Drip skip** — drip season (May–Oct) or raining now. No forecast lookahead — drip OK with rain coming since foliage stays dry.

### Modes

`input_select.garden_irrigation_mode` controls everything. The mode persists across HA restarts. Named modes ignore the calendar month — they run as configured. Only Smart inspects the month.

| Mode | Lawn (total) | Lawn freq | Drip dur | Drip freq |
|------|------|------|------|------|
| **Manual** | — | — | — | — |
| **Eco** | 1h30 | Sat | 45m ×1/day | Sat |
| **Standard** | 1h45 | Wed + Sat | 45m ×1/day | Wed + Sat |
| **Intensive** | 1h45 | Mon + Wed + Sat | 60m ×1/day | Mon + Wed + Sat |
| **Testing** | 30s/zone | daily | 30s ×1/day | daily |
| **Smart** | per month (see below) | per month | per month | per month |

**Smart mode by month:**

| Month | Lawn (total) | Lawn freq | Drip dur | Drip freq |
|-------|------|------|------|------|
| May | 1h45 | Tue + Sat | 45m ×1/day | Tue + Sat |
| June | 2h00 | Tue + Sat | 45m ×1/day | Tue + Sat |
| Jul–Aug | 1h45 | Mon + Wed + Sat | 60m ×1/day | Mon + Wed + Sat |
| September | 1h30 | Sat | 45m ×1/day | Sat |
| October | OFF | — | 15m ×1/day | every 3 days |
| Nov–Apr | OFF | — | OFF | — |

Lawn total is split per zone in **3:2:1 ratio** (`zone_1` biggest+most exposed → `zone_3` smallest). Example 1h45 → z1 52m, z2 35m, z3 18m.

### How Valves Are Controlled

The **auto-off automation** is the single source of truth for durations. Any valve that opens — schedule, script, or HomeKit — gets automatically closed after the profile-driven duration. Scripts open valves and wait for them to close.

The **lawn irrigation script** runs zones sequentially. The **full irrigation script** chains lawn → drip.

### Cleanup Safety

The cleanup automation closes all valves when an irrigation script ends. To avoid killing the parent during chained runs, it skips when `script.garden_full_irrigation` is still running.

### On-Demand Control

All 4 valves and 3 sequence scripts are exposed to **HomeKit**:

- Open any individual valve — auto-off handles the duration
- Close any valve — stops immediately
- Trigger `script.garden_lawn_irrigation` — runs all 3 zones sequentially
- Trigger `script.garden_drip_irrigation` — drip only
- Trigger `script.garden_full_irrigation` — lawn zones then drip

## Gotchas

- **Valves can't run simultaneously** — the Tuya controller doesn't support it.
- **Auto-off reads duration at valve-open time** — changing mode mid-run won't affect an already-running valve.
- **Zones 5-8 on the Tuya controller are unused** — hardware supports 4 zones.

## Entities

**Valves:** `valve.lawn_sprinkler_zone_1`, `valve.lawn_sprinkler_zone_2`, `valve.lawn_sprinkler_zone_3`, `valve.drip_irrigation`

**Mode:** `input_select.garden_irrigation_mode` — Manual / Eco / Standard / Intensive / Testing / Smart

**Sensors:**
- `binary_sensor.garden_lawn_should_skip` — on = skip lawn
- `binary_sensor.garden_drip_should_skip` — on = skip drip
- `binary_sensor.garden_should_skip_irrigation` — legacy alias of lawn skip
- `sensor.garden_irrigation_profile` — resolved schedule. Attributes: `lawn_durations` (per-zone seconds dict), `drip_duration`, `drip_runs_per_day`, `lawn_today`, `drip_today`

**Scripts:**
- `script.garden_lawn_irrigation` — zones 1→2→3 sequential
- `script.garden_drip_irrigation` — drip only
- `script.garden_full_irrigation` — lawn then drip

## Dependencies

- `binary_sensor.raining` — current rain state
- `weather.forecast_home` — Met.no, used for 6h rain forecast (lawn only)

## File Index

| File | Purpose |
|------|---------|
| `config.yaml` | Package entry, input_select definition |
| `automations/garden_valve_auto_off.yaml` | Auto-closes valves after profile duration |
| `automations/garden_scheduled_irrigation.yaml` | 04:00 trigger with per-type skip |
| `automations/garden_irrigation_cleanup.yaml` | Closes all valves on script end (skips when parent full irrigation running) |
| `scripts/garden_lawn_irrigation.yaml` | Sequential zones 1→2→3 |
| `scripts/garden_drip_irrigation.yaml` | Drip valve with wait-for-close |
| `scripts/garden_full_irrigation.yaml` | Chains lawn + drip |
| `templates/garden_should_skip_irrigation.yaml` | Lawn + drip skip sensors |
| `templates/garden_irrigation_profile.yaml` | Mode → duration/days mapping |
