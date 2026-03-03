# Bedroom (First Floor)

> Master bedroom with ensuite bathroom and wardrobe -- presence-aware lighting, automated covers, smart humidifier control, and per-person bedside switches.

**Package:** `bedroom` | **Path:** `packages/areas/first-floor/bedroom/`
**Floor:** First floor (Piętro) | **Area:** 16.65 m² (bedroom) + 5.24 m² (ensuite) + 3.52 m² (wardrobe)

## How It Works

### Lighting

When someone enters the bedroom and it is dark, the bed stripe turns on automatically. During daytime (non-sleeping hours) it comes on at 50% warm white (2951 K); during sleeping time it dims to 20%. If movie mode is enabled, presence-based lighting is suppressed entirely so the room stays dark.

Bed lights and non-bed lights are mutually exclusive. Turning on any bedside lamp (`light.bedroom_jakub`, `light.bedroom_sona`, LEDs, main, or reflectors) automatically kills the bed stripe. Turning on the bed group switches off the non-bed lights. This prevents conflicting light scenes from stacking.

During sleeping time, any movement detected by the bed-side or walking-area presence sensors triggers a minimal nightlight: the bed stripe at 1% with a warm tint (RGB 249, 255, 194). It stays on while presence is detected and turns off 3 seconds after the last sensor clears (30-second timeout if sensors never clear).

If both the bedroom and ensuite bathroom are vacant for 10 minutes, all lights in both areas are force-turned off as a safety net.

### Ensuite Bathroom

The ensuite has its own presence-based lighting. During the day, entering turns on the main ceiling bulbs (6 bulbs) at 20% -- or 100% if the bedroom lights are already on (the assumption being you want full brightness when you are awake and active). At night (23:00--07:30), only a single bulb (`light.en_suite_bulb_top_middle`) comes on at 1% to avoid blinding anyone. Opening the door also triggers lights proactively, even before presence is confirmed.

When presence clears (2-second delay), all ensuite lights turn off.

### Wardrobe

The wardrobe light turns on when `binary_sensor.bedroom_wardrobe_occupancy` detects someone. If the light was turned on by automation (changed less than 5 minutes ago), it turns off after 30 seconds of vacancy. If it was turned on manually, the automation leaves it alone but forces it off after 30 minutes of vacancy as a cleanup safety net.

### Covers

Bedroom window covers close automatically at sunset (when `binary_sensor.dark_for_curtains` activates) and 1 hour before sunrise (to prevent early morning light from waking anyone). On weekday mornings, covers open when sleeping time ends. Weekends are excluded -- covers stay closed until manually opened.

### Humidifier

The humidifier uses a three-layer control system: a standalone humidity sensor (`sensor.bedroom_hygro_humidity`), a hysteresis flag, and a proportional fan speed controller.

**Humidity targeting** reads from the dedicated hygro sensor (more accurate and always-on, unlike the humidifier's built-in sensor). Thresholds shift depending on the time of day:

| Period | Activate below | Deactivate at |
|--------|---------------|---------------|
| Comfort (bed time or after 21:00) | 45% | 50% |
| Daytime | 35% | 40% |

When humidity reaches the target, `input_boolean.bedroom_humidification_active` turns off. The humidifier stays physically on -- only the fan speed changes.

**Fan speed** is proportional to the humidity gap (how far below target), computed by `sensor.bedroom_humidifier_target_speed`. The further from target, the harder the fan works -- but capped by presence and time of day:

| Humidity gap | Base speed | Occupied cap | Vacant cap |
|-------------|-----------|-------------|-----------|
| < 3% | 20% | 20% | 20% |
| 3--6% | 40% | 40% | 40% |
| 6--10% | 60% | 40% | 60% |
| > 10% | 80% | 40% | 60% |

Night mode (bed time) always overrides to 20% with the display turned off. Morning restores the display and re-evaluates speed. The target speed sensor exposes debug attributes (humidity, gap, mode, max_speed, presence) visible in Developer Tools.

### Wall Button Switch (dual-button, near door)

| Button | Press | Effect |
|--------|-------|--------|
| Left | Single | Toggle main light |
| Right | Single | Toggle LEDs (with power relay) |
| Right | Double | Cycle LED color (Warm White, Soft Purple, Deep Blue, Amber, Coral, Lavender) |
| Left | Hold | Decrease LED brightness by 20% |
| Right | Hold | Increase LED brightness by 20% |

Hold actions only work when the LEDs are already on.

### Jakub's Bedside Switch (4-button)

| Button | Press | Effect |
|--------|-------|--------|
| 1 | Single | Toggle Jakub's bedside lamp |
| 3 | Single | Toggle LEDs |
| 1 | Hold | Turn off all bedroom lights |
| 3 | Hold | Turn off all lights in the house |
| 2 | Single | Open covers |
| 4 | Single | Close covers |
| 2 | Double | Stop covers |
| 4 | Double | Set covers to 20% |

### Sona's Bedside Switch (4-button)

| Button | Press | Effect |
|--------|-------|--------|
| 2 | Single | Toggle Sona's bedside lamp |
| 4 | Single | Toggle LEDs |
| 2 | Hold | Turn off all bedroom lights |
| 4 | Hold | Turn off all lights in the house |
| 2 | Double | Increase Sona bulbs brightness +20% |
| 4 | Double | Decrease Sona bulbs brightness -20% (floors at 1%) |
| 1 | Single | Open covers |
| 3 | Single | Close covers |
| 1 | Double | Stop covers |
| 3 | Double | Set covers to 20% |

### Sona's Dial Switch (rotary + 3 buttons)

The dial controls different entities depending on which button was last pressed. Rotating the dial adjusts brightness (for lights) or position (for covers) of the currently selected target.

| Button | Effect |
|--------|--------|
| 1 | Toggle Sona lamp, set dial target to **light** |
| 2 | Toggle reflectors, set dial target to **reflectors** |
| 3 | Toggle cover, set dial target to **cover** |
| Rotation | Adjust the current target's brightness or position |

The dial target resets back to "light" after 30 seconds of inactivity to prevent accidentally adjusting the wrong entity.

### Ensuite Bathroom Switch (dual-button)

| Button | Press | Effect |
|--------|-------|--------|
| Left | Single | Toggle main ceiling bulbs |
| Right | Single | Turn on main bulbs at 100% (with power relay) |

## Gotchas

- **Light exclusivity is immediate**: turning on any non-bed light kills the bed stripe and vice versa -- this is intentional to keep the room in a single lighting mode
- **Movie mode** blocks all automatic lighting; it must be toggled off manually (e.g., via the UI) for presence automation to resume
- **Presence turn-off only kills the bed stripe**, not all lights -- the 10-minute vacancy timeout handles the full sweep of bedroom + ensuite
- **Covers skip weekends**: the morning open only fires Monday through Friday
- **Cover close fires twice**: once at sunset and once 1 hour before sunrise (catches the case where covers were manually opened at night)
- **Humidifier never turns off physically** -- the `bedroom_humidification_active` flag only changes fan speed between idle (20%) and active (proportional 20--60%)
- **Humidity is read from `sensor.bedroom_hygro_humidity`**, not the humidifier's built-in sensor -- the hygro sensor is more accurate and stays available when the humidifier is off
- **Ensuite brightness depends on bedroom lights**: if bedroom lights are on, ensuite comes on at 100%; otherwise 20% during the day
- **Wardrobe 30-second vs 30-minute off**: short delay for automation-triggered on, long safety delay for manually-triggered on (detected by checking `last_changed` age)

## Entities

**Lights:** `light.bedroom` (master group), `light.bedroom_bed` (Jakub + Sona bedside), `light.bedroom_non_bed` (LEDs power + main + reflectors), `light.bedroom_leds_with_power`, `light.bedroom_reflectors_with_power`, `light.bedroom_sona_with_power`, `light.bed_stripe`, `light.bedroom_wardrobe`
**Ensuite lights:** `light.ensuite_bathroom` (all), `light.ensuite_bathroom_main` (6 ceiling bulbs), `light.ensuite_bathroom_main_with_power`
**Sensors:** `binary_sensor.bedroom_is_dark`, `binary_sensor.ensuite_bathroom_is_dark`, `sensor.bedroom_humidifier_target_speed`
**State:** `input_boolean.bedroom_movie_mode`, `input_boolean.bedroom_humidification_active`, `input_select.bedroom_leds_color`, `input_select.sona_dial_rotation_target`

## Dependencies

- `binary_sensor.outdoor_is_dark` -- global darkness sensor (used by dark templates)
- `binary_sensor.sleeping_time` -- global sleeping schedule (presence lighting, covers)
- `binary_sensor.bed_time` -- global bed time schedule (humidifier night mode, humidity targets)
- `binary_sensor.dark_for_curtains` -- global curtain darkness threshold (cover close trigger)
- `binary_sensor.bedroom_presence` -- hardware presence sensor
- `binary_sensor.bedroom_entrance_presence` -- entrance presence sensor
- `binary_sensor.bedroom_walking_area_presence` -- walking area presence sensor
- `binary_sensor.presence_sensor_bedroom_jakub_side` -- Jakub's bed presence
- `binary_sensor.presence_sensor_bedroom_sona_side` -- Sona's bed presence
- `binary_sensor.ensuite_bathroom_presence` -- ensuite presence sensor
- `binary_sensor.ensuite_door` -- ensuite door contact sensor
- `binary_sensor.bedroom_wardrobe_occupancy` -- wardrobe occupancy sensor
- `cover.bedroom` -- bedroom window covers
- `humidifier.bedroom` -- bedroom humidifier device
- `fan.bedroom_humidifier` -- humidifier fan entity
- `light.bedroom_humidifier_display` -- humidifier display backlight
- `sensor.bedroom_illuminance` -- bedroom illuminance sensor
- `sensor.ensuite_bathroom_illuminance` -- ensuite illuminance sensor
- `sensor.bedroom_hygro_humidity` -- standalone humidity sensor (more accurate than humidifier built-in)

## File Index

| File | Purpose |
|------|---------|
| `config.yaml` | Input booleans, input selects, package includes |
| `automations/bedroom_presence.yaml` | Presence-based bed stripe on/off |
| `automations/bedroom_bed_presence_sleeping.yaml` | Nightlight on bed movement during sleeping time |
| `automations/bedroom_lights_exclusivity.yaml` | Mutual exclusion between bed and non-bed lights |
| `automations/bedroom_ensuite_vacancy_timeout.yaml` | 10-min vacancy safety off for bedroom + ensuite |
| `automations/bedroom_button_switch.yaml` | Dual-button wall switch (main light, LEDs, colors) |
| `automations/bedroom_scene_switch_jakub.yaml` | Jakub's 4-button bedside switch |
| `automations/bedroom_scene_switch_sona.yaml` | Sona's 4-button bedside switch |
| `automations/bedroom_sona_dial_switch.yaml` | Sona's rotary dial (brightness/cover control) |
| `automations/bedroom_sona_dial_rotation_reset.yaml` | Auto-reset dial target to "light" after 30s |
| `automations/bedroom_cover_windows_when_sunset.yaml` | Close covers at sunset and before sunrise |
| `automations/bedroom_uncover_windows_when_sleeping_time_off.yaml` | Open covers on weekday mornings |
| `automations/bedroom_humidifier_on_off.yaml` | Humidity threshold control (activate/deactivate flag) |
| `automations/bedroom_humidifier_fan_speed.yaml` | Apply computed fan speed and manage display |
| `automations/ensuite_bathroom_presence.yaml` | Ensuite presence-based lighting with night mode |
| `automations/ensuite_bathroom_lights_switch.yaml` | Ensuite dual-button wall switch |
| `automations/wardrobe_lights_on_when_occupied.yaml` | Wardrobe occupancy-based light with dual timeout |
| `lights/bedroom.yaml` | Master bedroom light group |
| `lights/bedroom_bed.yaml` | Bed lights group (Jakub + Sona) |
| `lights/bedroom_non_bed.yaml` | Non-bed lights group (LEDs power, main, reflectors) |
| `lights/bedroom_leds_with_power.yaml` | LEDs + power relay group |
| `lights/bedroom_reflector_bulbs.yaml` | 8 individual reflector bulbs group |
| `lights/bedroom_reflectors_with_power.yaml` | Reflectors + power relay group |
| `lights/bedroom_sona_bulbs.yaml` | Sona's high + low bulbs group |
| `lights/bedroom_sona_with_power.yaml` | Sona bulbs + power relay group |
| `lights/ensuite_bathroom.yaml` | All ensuite lights group |
| `lights/ensuite_bathroom_main.yaml` | 6 ensuite ceiling bulbs group |
| `lights/ensuite_bathroom_main_with_power.yaml` | Ensuite main + power relay group |
| `templates/binary_sensors/bedroom_is_dark.yaml` | Bedroom darkness with hysteresis (5/8 lux) |
| `templates/binary_sensors/ensuite_bathroom_is_dark.yaml` | Ensuite darkness with hysteresis (5/10 lux) |
| `templates/sensors/bedroom_humidifier_target_speed.yaml` | Proportional fan speed based on humidity gap, presence, time |
