# Stairway Automations

This folder contains automations for stairway and first-floor hall lighting control.

## Automations

### 1. Stairway presence

**Alias:** `Stairway presence`
**ID:** `80741f39-9e04-408b-90bf-dcde194198bb`
**Mode:** `restart`

**Description:**
Automatically controls stairway lights based on presence detection and darkness conditions from adjacent areas (living room or hall).

**Triggers:**

- Home Assistant start
- Automation reloaded event
- `binary_sensor.stairway_presence` changes from "off" to "on"
- `binary_sensor.stairway_presence` changes from "on" to "off" for 20 seconds

**Conditions:**

- None

**Actions:**

#### When presence detected in stairway

**Conditions:**

- `binary_sensor.stairway_presence` is "on"
- AND at least one area is dark:
  - `binary_sensor.living_room_is_dark` is "on", OR
  - `binary_sensor.hall_is_dark` is "on"

**Action:**

- Turn on `light.stairway`

#### When no presence detected for 20 seconds

**Conditions:**

- `binary_sensor.stairway_presence` is "off"

**Action:**

- Turn off `light.stairway`

**Example Scenarios:**

*Going upstairs in the evening:*

1. You walk toward the stairway from the living room at 8:00 PM
2. Living room is dark (`binary_sensor.living_room_is_dark` is "on")
3. `binary_sensor.stairway_presence` detects you
4. `light.stairway` turns on immediately
5. You climb the stairs and reach the hall
6. After 20 seconds without presence, stairway light turns off

*Daytime with natural light:*

1. You walk to the stairway at noon
2. Both living room and hall have plenty of natural light
3. Neither `binary_sensor.living_room_is_dark` nor `binary_sensor.hall_is_dark` is "on"
4. Even though presence is detected, lights don't turn on
5. Natural light is sufficient for safe navigation

*Coming downstairs at night:*

1. Hall is dark at 10:00 PM
2. You start descending the stairs
3. `binary_sensor.stairway_presence` detects you
4. `light.stairway` turns on because hall is dark
5. You reach the ground floor and move away
6. After 20 seconds, stairway light turns off

**Benefits:**

- Quick turn-off (20 seconds) is appropriate for a transit area
- Checks darkness in adjacent areas (living room and hall) to determine if lighting is needed
- Won't turn on during bright daylight
- Ensures safe navigation on stairs when ambient light is low
- Automatically handles both upstairs and downstairs traffic

---

### 2. Hall presence

**Alias:** `Hall presence`
**ID:** `927c6842-e874-4a1d-8182-4a454a7c38d6`
**Mode:** `restart`

**Description:**
Controls first-floor corridor (hall) lighting with minimal brightness for nighttime navigation.

**Triggers:**

- Home Assistant start
- Automation reloaded event
- `binary_sensor.first_floor_corridor_presence` changes from "off" to "on"
- `binary_sensor.first_floor_corridor_presence` changes from "on" to "off" for 5 seconds

**Conditions:**

- None

**Actions:**

#### When presence detected

**Conditions:**

- `binary_sensor.first_floor_corridor_presence` is "on"
- `light.hall_bulbs` is "off"
- `binary_sensor.hall_is_dark` is "on"

**Action:**

- Turn on `light.hall_bulbs` at brightness level 2 (very dim)

#### When no presence detected for 5 seconds

**Conditions:**

- `binary_sensor.first_floor_corridor_presence` is "off"

**Action:**

- Turn off `light.hall_bulbs`

**Example Scenarios:**

*Nighttime navigation:*

1. You walk into the first-floor corridor at 2:00 AM
2. Hall is dark (`binary_sensor.hall_is_dark` is "on")
3. `binary_sensor.first_floor_corridor_presence` detects you
4. `light.hall_bulbs` turns on at brightness 2 (very minimal)
5. Just enough light to navigate safely without being jarring
6. You enter a bedroom
7. After 5 seconds, hall lights turn off

*Lights already on:*

1. Hall lights are already on from manual control
2. You walk through the corridor
3. Presence is detected but lights are already on
4. Automation doesn't interfere with manual control
5. Lights won't be adjusted or turned off until no presence for 5 seconds

*Daytime:*

1. You walk through the hall at noon
2. Natural light is present (`binary_sensor.hall_is_dark` is "off")
3. Even though presence is detected, condition fails
4. Lights don't turn on unnecessarily

**Key Features:**

- Very short turn-off delay (5 seconds) suitable for a corridor
- Minimal brightness (level 2) for gentle nighttime lighting
- Won't override if lights are already on
- Only activates when hall is actually dark
- Perfect for middle-of-the-night bathroom trips

---

### 3. Hall Switch Control

**Alias:** `Hall Switch Control`
**ID:** `f8d2e7a1-9c4b-4f3e-8a5d-2b1c9e6f7a8b`
**Mode:** `single`

**Description:**
Manual control of hall bulbs using a dual-button MQTT switch with different brightness presets for various needs.

**Triggers:**
MQTT device actions (device_id: `7b1b9100e4c3a1fe271d5e258e4e82ee`):

- Left button: single press, double press
- Right button: single press, double press

**Conditions:**

- None

**Actions:**

| Button | Action | Behavior |
|--------|--------|----------|
| Left - Single | Turn off | Turn off `light.hall_bulbs` |
| Right - Single | Turn on | Turn on `light.hall_bulbs` (default brightness) |
| Left - Double | Minimal | Turn on `light.hall_bulbs` at 5% brightness |
| Right - Double | Maximum | Turn on `light.hall_bulbs` at 100% brightness |

**Example Scenarios:**

*Normal nighttime use:*

1. You press the right button (single press)
2. Hall bulbs turn on at default brightness
3. Good for general nighttime navigation
4. Press left button (single press) to turn off when done

*Very dim light for sleeping household:*

1. It's 3:00 AM and everyone is asleep
2. You double-press the left button
3. Hall bulbs turn on at 5% brightness
4. Provides just enough light to navigate without disturbing others

*Maximum brightness for tasks:*

1. You need to clean the hall or look for something
2. You double-press the right button
3. Hall bulbs turn on at 100% brightness
4. Full illumination for detailed work

*Quick toggle:*

1. Single press right to turn on
2. Single press left to turn off
3. Simple on/off control without adjusting brightness

**Button Layout Summary:**

```
[LEFT]  [RIGHT]

Single: Off      Single: On (default)
Double: 5%       Double: 100%
```

**Benefits:**

- Quick access to different brightness levels
- Single press for simple on/off
- Double press for specific brightness needs
- Physical control complements automated presence-based lighting
- Left side controls lower light/off, right side controls higher light/on (intuitive)
