# Living Room

> Entertainment hub with TV ambient lighting, automated curtains, and smart humidity control.

**Package:** `living_room` | **Path:** `packages/areas/ground-floor/living-room/`
**Floor:** Ground floor (Parter) | **Area:** 38.76 m²

## How It Works

### Covers

Both living room curtains (`cover.living_room_main` and `cover.living_room_left`) are grouped as `cover.ground_floor` and move together. They close automatically when `binary_sensor.dark_for_curtains` turns on and open when it turns off or at 07:00 -- whichever comes first. The automation only acts if at least one cover is not already in the target position, avoiding redundant commands.

### Media & TV Lighting

The TV is exposed as a single universal media player (`media_player.living_room_tv`) that wraps the Sony Bravia, Chromecast, and Apple TV. The active child is selected automatically: Apple TV takes priority when the Bravia source is set to "Living Room Ap" and the Apple TV is not off; otherwise, the Bravia handles playback. All power and transport commands route through the Bravia.

Behind the TV, a warm-orange LED strip (RGB 255, 193, 132) adjusts its brightness based on the TV state. All LED changes only happen when the room is dark.

| TV State   | LED Brightness |
|------------|----------------|
| Playing    | 20%            |
| Paused     | 100%           |
| Idle / On  | 50%            |
| Off        | LEDs off       |

When the TV turns off, the LEDs switch off unconditionally. If the room is dark, someone is on the ground floor, and no powerful lights are already on, the standing lamp turns on as a soft fallback.

### Climate (Humidifier)

The humidifier runs a three-layer control system: a standalone humidity sensor (`sensor.living_room_hygro_humidity`), a hysteresis flag, and a proportional fan speed controller.

**Humidity control** reads from the dedicated hygro sensor (more accurate and always-on, unlike the humidifier's built-in sensor). It toggles `input_boolean.living_room_humidification_active` using hysteresis thresholds that shift with the time of day. The humidifier stays physically on at all times -- only the "active" flag changes.

| Period        | Activate below | Deactivate at |
|---------------|----------------|---------------|
| Evening prep  | 40%            | 45%           |
| All other     | 38%            | 40%           |

**Fan speed** is proportional to the humidity gap, computed by `sensor.living_room_humidifier_target_speed`. The further from target, the harder the fan works -- but capped by presence and time-of-day:

| Humidity gap | Base speed | Occupied/Quiet cap | Active hours cap | Prep boost cap |
|-------------|-----------|-------------------|-----------------|---------------|
| < 3% | 20% | 20% | 20% | 20% |
| 3--6% | 40% | 40% | 40% | 40% |
| 6--10% | 60% | 40% | 60% | 60% |
| > 10% | 80% | 40% | 60% | 80% |

The "prep boost" ceiling of 80% only applies during the overlap of `evening_prep` and `office_hours` (weekdays 17:00-18:00) -- a window to push humidity up before the household arrives. The target speed sensor exposes debug attributes (humidity, gap, mode, max_speed, presence) visible in Developer Tools.

### Standing Lamp (HomeKit)

A template light wraps `light.living_room_light_standing_lamp` for HomeKit exposure. Its display name dynamically switches to "Christmas Tree" when `input_boolean.christmas_mode` is on.

### Darkness Detection

`binary_sensor.living_room_is_dark` combines illuminance readings with outdoor darkness state. If `binary_sensor.outdoor_is_dark` is on, the room is always considered dark regardless of the lux sensor. Otherwise it uses hysteresis thresholds on `sensor.living_room_illuminance` (on at < 7 lux, off at > 10 lux) with a 5-second on-delay and 30-second off-delay to prevent flicker.

## Gotchas

- The cover group is named `cover.ground_floor`, not `cover.living_room` -- it lives here but the name is floor-scoped.
- The humidifier never turns off physically. The "idle standby" state keeps the fan at 20% for air circulation even when humidity targets are met.
- Humidity is read from `sensor.living_room_hygro_humidity`, not the humidifier's built-in sensor -- the hygro sensor is more accurate and stays available when the humidifier is off.
- TV LED changes are gated on darkness. If the room is bright, playback state changes are silently ignored and the LEDs stay in their last state.
- The standing lamp fallback when the TV turns off requires three simultaneous conditions: dark, presence, and no powerful lights. If any one fails, you get darkness after TV-off.
- The `binary_sensor.living_room_tv_is_playing` template sensor exists but appears to have a logic bug (checks illuminance sensor state against "playing" and has contradictory cast conditions). It is not referenced by any automation in this package.
- Fan speed changes are proportional to the humidity gap -- near-target conditions result in lower speeds, preventing unnecessary noise when only minor humidification is needed.

## Entities

**Lights:** `light.living_room_tv_leds` (group), `light.living_room_tv_leds_with_power` (group with power switch), `light.living_room_standing_lamp_homekit` (template)

**Sensors:** `binary_sensor.living_room_is_dark`, `binary_sensor.living_room_tv_is_playing`, `sensor.living_room_humidifier_target_speed`

**State:** `input_boolean.living_room_humidification_active`

**Covers:** `cover.ground_floor` (group of `cover.living_room_main`, `cover.living_room_left`)

**Media:** `media_player.living_room_tv` (universal: Sony Bravia, Chromecast, Apple TV)

## Dependencies

- `binary_sensor.dark_for_curtains` -- bootstrap darkness sensor for curtain timing
- `binary_sensor.outdoor_is_dark` -- outdoor darkness state, overrides local illuminance
- `binary_sensor.ground_floor_presence` -- floor-level occupancy detection
- `light.ground_floor_powerful` -- powerful lights group, used in TV-off fallback logic
- `binary_sensor.evening_prep` -- time-of-day period for evening preparation
- `binary_sensor.office_hours` -- time-of-day period for working hours
- `sensor.living_room_illuminance` -- physical lux sensor
- `input_boolean.christmas_mode` -- global flag that renames the standing lamp template
- `sensor.living_room_hygro_humidity` -- standalone humidity sensor (more accurate than humidifier built-in)

## File Index

| File | Purpose |
|------|---------|
| `config.yaml` | Package entry point; defines cover group, input_boolean, and includes subdirectories |
| `automations/living_room_curtains.yaml` | Open/close curtains based on darkness and morning schedule |
| `automations/living_room_tv_playback.yaml` | Adjust TV LED brightness by playback state; standing lamp fallback |
| `automations/living_room_humidifier_on_off.yaml` | Toggle humidification active flag based on humidity thresholds |
| `automations/living_room_humidifier_fan_speed.yaml` | Apply computed fan speed from target speed sensor |
| `lights/group_tv_leds.yaml` | Light group for TV LED strips (up + down) |
| `lights/group_tv_leds_with_power.yaml` | Light group including the LED power switch |
| `media_players/tv.yaml` | Universal media player wrapping Bravia, Chromecast, and Apple TV |
| `templates/binary_sensors/living_room_is_dark.yaml` | Darkness sensor with hysteresis and outdoor override |
| `templates/binary_sensors/living_room_tv_is_playing.yaml` | TV playing state sensor (unused) |
| `templates/lights/standing_lamp_homekit.yaml` | HomeKit-compatible standing lamp with Christmas mode naming |
| `templates/sensors/living_room_humidifier_target_speed.yaml` | Proportional fan speed based on humidity gap, presence, time |
