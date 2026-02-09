# Living Room

> Entertainment hub with TV ambient lighting, automated curtains, and smart humidity control.

**Package:** `living_room` | **Path:** `packages/areas/ground-floor/living-room/`

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

The humidifier runs a two-layer control system: a humidity control layer that decides _whether_ to humidify, and a fan speed layer that decides _how hard_.

**Humidity control** toggles `input_boolean.living_room_humidification_active` using hysteresis thresholds that shift with the time of day. The humidifier stays physically on at all times -- only the "active" flag changes.

| Period        | Activate below | Deactivate at |
|---------------|----------------|---------------|
| Evening prep  | 40%            | 45%           |
| All other     | 38%            | 40%           |

**Fan speed** reacts to the active flag, ground-floor presence, and time-of-day periods. When the flag is off the fan idles at 20% to keep air circulating. When active, speed ramps up based on whether anyone is home and what time window is current.

| State                                        | Fan Speed |
|----------------------------------------------|-----------|
| Idle (humidification not needed)             | 20%       |
| Active + occupied                            | 40%       |
| Active + vacant + quiet hours                | 40%       |
| Active + vacant + active hours               | 60%       |
| Active + vacant + prep boost (weekday 17-18) | 80%       |

The "prep boost" fires during the overlap of `evening_prep` and `office_hours`, which corresponds to weekdays 17:00-18:00 -- a window to push humidity up before the household arrives.

### Standing Lamp (HomeKit)

A template light wraps `light.living_room_light_standing_lamp` for HomeKit exposure. Its display name dynamically switches to "Christmas Tree" when `input_boolean.christmas_mode` is on.

### Darkness Detection

`binary_sensor.living_room_is_dark` combines illuminance readings with outdoor darkness state. If `binary_sensor.outdoor_is_dark` is on, the room is always considered dark regardless of the lux sensor. Otherwise it uses hysteresis thresholds on `sensor.living_room_illuminance` (on at < 7 lux, off at > 10 lux) with a 5-second on-delay and 30-second off-delay to prevent flicker.

## Gotchas

- The cover group is named `cover.ground_floor`, not `cover.living_room` -- it lives here but the name is floor-scoped.
- The humidifier never turns off physically. The "idle standby" state keeps the fan at 20% for air circulation even when humidity targets are met.
- TV LED changes are gated on darkness. If the room is bright, playback state changes are silently ignored and the LEDs stay in their last state.
- The standing lamp fallback when the TV turns off requires three simultaneous conditions: dark, presence, and no powerful lights. If any one fails, you get darkness after TV-off.
- The `binary_sensor.living_room_tv_is_playing` template sensor exists but appears to have a logic bug (checks illuminance sensor state against "playing" and has contradictory cast conditions). It is not referenced by any automation in this package.
- Vacancy for fan speed uses a 30-second debounce before the ground floor is considered vacant.

## Entities

**Lights:** `light.living_room_tv_leds` (group), `light.living_room_tv_leds_with_power` (group with power switch), `light.living_room_standing_lamp_homekit` (template)

**Sensors:** `binary_sensor.living_room_is_dark`, `binary_sensor.living_room_tv_is_playing`

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

## File Index

| File | Purpose |
|------|---------|
| `config.yaml` | Package entry point; defines cover group, input_boolean, and includes subdirectories |
| `automations/living_room_curtains.yaml` | Open/close curtains based on darkness and morning schedule |
| `automations/living_room_tv_playback.yaml` | Adjust TV LED brightness by playback state; standing lamp fallback |
| `automations/living_room_humidifier_on_off.yaml` | Toggle humidification active flag based on humidity thresholds |
| `automations/living_room_humidifier_fan_speed.yaml` | Set fan speed by presence, humidification state, and time period |
| `lights/group_tv_leds.yaml` | Light group for TV LED strips (up + down) |
| `lights/group_tv_leds_with_power.yaml` | Light group including the LED power switch |
| `media_players/tv.yaml` | Universal media player wrapping Bravia, Chromecast, and Apple TV |
| `templates/binary_sensors/living_room_is_dark.yaml` | Darkness sensor with hysteresis and outdoor override |
| `templates/binary_sensors/living_room_tv_is_playing.yaml` | TV playing state sensor (unused) |
| `templates/lights/standing_lamp_homekit.yaml` | HomeKit-compatible standing lamp with Christmas mode naming |
