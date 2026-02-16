# Kitchen

> Presence-based LED lighting with a cooking mode override and wall-tablet screen control.

**Package:** `kitchen` | **Path:** `packages/areas/ground-floor/kitchen/`
**Floor:** Ground floor (Parter) | **Area:** 13.35 m²

## How It Works

### Lighting and Presence

The kitchen LED strip (`light.kitchen_led`) is the only light managed by automation. When presence is detected and the room is dark, the LED turns on automatically. Once presence clears, the automation waits 15 seconds before switching it off -- giving you time to walk back in without a flicker. On Home Assistant restart or automation reload, the automation re-evaluates the current state so lights stay consistent.

Only the LED strip participates in presence automation. The other lights in the group (glass case, main, island) are left to manual control.

### Cooking Mode

`input_boolean.cooking_mode` acts as a keep-alive for the kitchen LED. While cooking mode is on, the normal presence-off logic still runs, but cooking mode gives you a second safety net: when you finally toggle cooking mode off, a dedicated automation checks whether the kitchen is still vacant. If it is, the LED turns off after a short 3-second grace period. If someone has wandered back in, the LED stays on and normal presence logic takes over.

### Darkness Detection

`binary_sensor.kitchen_is_dark` decides whether the kitchen is dark enough to need lights. It uses three tiers of logic:

- If `binary_sensor.outdoor_is_dark` is on, the kitchen is unconditionally dark -- no lux check needed.
- Otherwise it reads `sensor.ground_floor_illuminance` and applies hysteresis: the sensor flips to dark at 40 lux, but won't flip back to bright until illuminance rises above 50 lux. This 10-lux dead band prevents rapid toggling around the threshold.
- A 5-second delay-on and 30-second delay-off add additional damping against transient changes (e.g., car headlights, clouds).

### Dashboard Screen

A wall-mounted tablet in the kitchen has its screen managed by `switch.kitchen_dashboard_screen`. A dedicated presence sensor near the tablet (`binary_sensor.dashboard_presence`) wakes the screen when someone approaches. The screen only turns off once both the dashboard proximity sensor and the kitchen-wide presence sensor are clear, so the tablet stays awake while anyone is nearby -- even if they step away from the tablet itself.

## Gotchas

- **Cooking mode does not block the presence-off automation.** If you leave the kitchen while cooking mode is on, the LED will still turn off after 15 seconds of vacancy. Cooking mode only adds a *second* turn-off path when the toggle is flipped off. It is not a manual override that keeps lights on indefinitely.
- **Only the LED strip is automated.** The light group `light.kitchen` contains four lights, but presence logic only controls `light.kitchen_led`. Turning on `light.kitchen_main` or `light.kitchen_island` requires manual action, and those lights will not auto-off.
- **Darkness sensor uses ground-floor illuminance, not a kitchen-specific sensor.** If the ground-floor sensor is in a brighter spot than the kitchen, lights may not trigger when expected.
- **Dashboard screen-off requires both presence sensors to clear.** If `binary_sensor.kitchen_presence` stays on (e.g., someone else is cooking), the tablet screen won't sleep even after you walk away from it.

## Entities

**Lights:** `light.kitchen` (group) -- `light.kitchen_led`, `light.kitchen_glass_case`, `light.kitchen_main`, `light.kitchen_island`
**Sensors:** `binary_sensor.kitchen_is_dark`
**State:** `input_boolean.cooking_mode`

## Dependencies

- `sensor.ground_floor_illuminance` -- ground-floor illuminance sensor (darkness template)
- `binary_sensor.outdoor_is_dark` -- outdoor darkness state (darkness template)
- `binary_sensor.kitchen_presence` -- kitchen presence sensor (lighting and dashboard automations)
- `binary_sensor.dashboard_presence` -- tablet proximity sensor (dashboard screen automation)
- `switch.kitchen_dashboard_screen` -- tablet screen power switch

## File Index

| File | Purpose |
|------|---------|
| `config.yaml` | Package root -- wires up templates, automations, lights, and defines `input_boolean.cooking_mode` |
| `automations/kitchen_presence.yaml` | Turns LED on/off based on presence and darkness |
| `automations/kitchen_cooking_mode_timeout.yaml` | Turns LED off when cooking mode is disabled and kitchen is vacant |
| `automations/kitchen_dashboard_screen.yaml` | Wakes/sleeps the wall tablet screen based on proximity |
| `lights/group.yaml` | Groups all four kitchen lights under `light.kitchen` |
| `templates/binary_sensors/kitchen_is_dark.yaml` | Hysteresis-based darkness sensor using ground-floor illuminance |
