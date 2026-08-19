# Terrace

> Presence-based terrace lighting plus a weather-aware pergola: bioclimatic roof that opens on dry weekday mornings and slams shut on rain, zip blinds with wind safety, and pergola LED lighting.

**Package:** `terrace` | **Path:** `packages/areas/outdoor/terrace/`

## How It Works

### Terrace wall light

When someone is in the garden (`binary_sensor.garden_presence`) and it is dark outside (`binary_sensor.outdoor_is_dark`), `light.terrace_wall` switches on. When presence clears, the light turns off after a 30-second grace period so brief gaps in motion detection don't cause flicker. Opening either terrace door after dark also turns the light on immediately — but the door trigger never turns it off; the presence automation owns the off-path. The presence automation re-evaluates on HA start and automation reload, so the light reflects reality after a restart.

### Pergola roof (bioclimatic louvres)

`automation.pergola_roof_control` drives `cover.pergola_roof_proxy` (see calibration below; 100 % = open, 0 % = closed):

- **Weekday mornings** (wake-up, `binary_sensor.sleeping_time` on→off): opens fully **unless rain is falling or expected** — gated on `binary_sensor.pergola_rain_expected` (forecast), **not** the rainfall plate. The plate is a wetness sensor, not a raining sensor: it stays saturated for hours after rain stops, so an evening shower used to block the next morning's open on stale data. Weekends stay closed.
- **Sunset** (`binary_sensor.dark_for_curtains`): closes.
- **Rain starts** (`binary_sensor.pergola_rain_active` off→on): closes immediately. This is the plate's job — instant local detection.
- **Forecast flips to rain while the plate is wet**: closes. Covers the gap where the roof opened on a wrong dry forecast; with the plate already wet, `pergola_rain_active` can never re-edge, so the forecast flip is the only remaining close signal. Fires only when both sources agree.
- **HA start / automation reload**: closes if rain is falling or expected (`pergola_rain_expected`, again not the plate — reloads happen on every config push, and residual plate wetness must not shut a deliberately opened roof).

`input_select.pergola_weather_mode` picks the rain source for `pergola_rain_active` (Rainfall Sensor / Forecast / Both); **Manual** disables every automatic roof action.

### Rain sensing

Two complementary sensors:

- `binary_sensor.pergola_rain_active` — "is the plate wet?" per the selected weather mode. Drives instant close.
- `binary_sensor.pergola_rain_expected` — "is rain falling or coming?" from the Met.no hourly forecast: raining now, or ≥ 0.2 mm / a rainy condition within the next 3 h. Refreshes every 30 min. Drives the morning-open and restart decisions. Fail-safe: if the weather entity is unavailable, it reads ON and the roof stays closed.
- `sensor.rainfall_rain_intensity_recorded` — long-term-statistics mirror of the plate's raw mV signal (~20 mV dry, ~3100 mV saturated), kept so "was the sensor right?" audits survive recorder purge.

### Zip blinds

The right zip's physical travel is 35–100 %; `cover.pergola_zip_right_limited` remaps that band to a clean 0–100 % scale — HomeKit, dashboards, and automations all use the wrapper. At **00:30** nightly, `automation.pergola_zip_right_open_after_midnight_wind_safety` retracts the right zip if deployed (a deployed zip is a sail; there is no anemometer, so time-based). It waits up to 3 min for position confirmation and sends a phone notification if the blind didn't actually retract — Overkiz commands can return 200 and silently do nothing.

### Pergola roof calibration (bridge fix)

The Somfy Louver Control has open-limit drift: commanding tilt 100 overshoots and bounces. `cover.pergola_roof_proxy` maps a clean 0–100 % position onto the usable tilt band 0..`input_number.pergola_roof_offset` (default 70). Tune the offset live from the dashboard if drift shifts. Permanent fix = Somfy installer re-commissioning (see `docs/pergola/`); then delete the proxy + helper and repoint consumers to `cover.pergola_roof`.

## Gotchas

- **Never gate the morning open on the rainfall plate** — residual wetness holds it ON for 12 h+ after rain stops. That's what `pergola_rain_expected` is for.
- The roof does **not** re-open when rain clears mid-day — next open is the following weekday morning (deliberate).
- All roof branches drive `cover.pergola_roof_proxy`, never `cover.pergola_roof` directly — raw tilt commands bypass the calibration.
- "Open" on a zip blind means **rolled up / retracted** (the safe position), not covering the terrace.
- Overkiz/Tahoma commands can be accepted (200) yet move nothing — see the `overkiz-duplicate-entry` knowledge leaf. The zip safety automation logs/notifies on this; the roof branches do not.
- No manual override flag for the terrace wall light; Manual weather mode is the pergola's override.
- The terrace wall light has no darkness check on the off-branch: if the sun rises with someone still outside, it stays on until presence clears.

## Entities

**Lights:** `light.terrace_wall` (physical), `light.pergola_leds_main` (group: left/right/top/bottom pergola LED strips)
**Covers:** `cover.pergola_roof_proxy` — calibrated roof façade; `cover.pergola_zip_right_limited` — range-remapped right zip
**Sensors:** `binary_sensor.pergola_rain_active` — plate wet (mode-aware); `binary_sensor.pergola_rain_expected` — rain now/next 3 h (forecast); `sensor.rainfall_rain_intensity_recorded` — plate mV with long-term stats
**Helpers:** `input_select.pergola_weather_mode` — rain source / Manual; `input_number.pergola_roof_offset` — roof max-tilt calibration

## Dependencies

- `binary_sensor.garden_presence` — garden occupancy (presence package)
- `binary_sensor.outdoor_is_dark` — shared outdoor darkness gate
- `binary_sensor.sleeping_time` — household wake/sleep window (bootstrap)
- `binary_sensor.dark_for_curtains` — sunset threshold shared with cover logic
- `binary_sensor.raining` — Met.no condition-based "raining now" (bootstrap)
- `binary_sensor.rainfall_rain` + `sensor.rainfall_rain_intensity` — Zigbee2MQTT rainfall plate
- `binary_sensor.terrace_left_door` / `binary_sensor.terrace_main_door` — Satel door zones
- `cover.pergola_roof`, `cover.pergola_zip_right` — raw Overkiz/Somfy covers
- `weather.forecast_home` — Met.no forecast (via `weather.get_forecasts`)
- `notify.mobile_app_iglofon_new` — zip safety alerts

## File Index

| File | Purpose |
|------|---------|
| `config.yaml` | Package entry; weather-mode select + roof tilt calibration helper |
| `automations/garden_presence.yaml` | Terrace wall light on presence + darkness, 30 s off-delay |
| `automations/terrace_door_trigger.yaml` | Wall light on when a terrace door opens after dark |
| `automations/pergola_roof_control.yaml` | Roof: morning open (forecast-gated), sunset/rain/restart close |
| `automations/pergola_zip_right_open_after_midnight.yaml` | 00:30 zip retract + confirmation + failure alert |
| `lights/pergola_leds_main.yaml` | Group of the four pergola LED strips |
| `templates/cover_pergola_roof.yaml` | Calibrated 0–100 % roof proxy over the drifted tilt band |
| `templates/cover_pergola_zip_right_limited.yaml` | Remaps zip's 35–100 % physical travel to 0–100 % |
| `templates/pergola_rain_active.yaml` | Plate-wet binary per selected weather mode |
| `templates/pergola_rain_expected.yaml` | Forecast gate: raining now or rain within ~3 h |
| `templates/rainfall_rain_intensity_recorded.yaml` | Long-term-stats mirror of the plate's raw mV |
