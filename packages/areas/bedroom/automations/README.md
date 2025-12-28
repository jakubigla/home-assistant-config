# Bedroom Automations

This folder contains automations for bedroom lighting, covers, scene switches, and presence detection.

## Automations

### 1. Bedroom Light Exclusivity (Consolidated)

**Alias:** `Bedroom Light Exclusivity`
**ID:** `bedroom-lights-exclusivity-consolidated`
**Mode:** `single`

**Description:**
Ensures mutual exclusivity between bed lights and other bedroom lights. When bed lights turn on, other lights turn off; when other lights turn on, bed stripe turns off.

**Triggers:**
- `light.bedroom_bed` changes from "off" to "on" (id: `bed_on`)
- Any of `light.bedroom_jakub`, `light.bedroom_sona`, `light.bedroom_leds`, `light.bedroom_main`, `light.bedroom_reflectors` changes from "off" to "on" (id: `other_on`)

**Actions:**
- **bed_on trigger:** Turn off `light.bedroom_non_bed`
- **other_on trigger:** Turn off `light.bed_stripe`

**Example:**
You turn on your bedside lamp, and the overhead reflector lights automatically turn off. When you turn on the main bedroom lights in the morning, the bed strip automatically turns off.

---

### 2. Sona Scene Switch

**Alias:** `Sona Scene Switch`
**ID:** `8ff9934c-8fb9-4be7-98b8-fe23003785cc`
**Mode:** `single`

**Description:**
Controls bedroom lights, LEDs, and covers using a 4-button MQTT scene switch (Sona's bedside switch).

**Triggers:**
MQTT device actions (device_id: `1a3b7e0a2d7d4b03cb7671077b0f6d77`):
- Buttons 1-4: single, double, and hold actions

**Actions:**

| Button | Action | Behavior |
|--------|--------|----------|
| 2 - Single | Toggle | Toggle `light.bedroom_sona` |
| 4 - Single | Toggle | Toggle `light.bedroom_leds` |
| 2 - Hold | Turn off | Turn off all bedroom area lights |
| 4 - Hold | Turn off | Turn off all lights on ground floor, first floor, and backyard |
| 2 - Double | Brightness up | Increase `light.bedroom_sona_bulbs` brightness by 20% |
| 4 - Double | Brightness down | Decrease brightness by 20% (or set to 1% if below 21%) |
| 1 - Single | Cover open | Open all bedroom covers |
| 3 - Single | Cover close | Close all bedroom covers |
| 1 - Double | Cover stop | Stop all bedroom covers |
| 3 - Double | Cover position | Set bedroom covers to 20% open |

**Example:**
Sona presses button 2 once to toggle her bedside light, or holds button 2 to turn off all bedroom lights before sleep.

---

### 4. Jakub Scene Switch

**Alias:** `Jakub Scene Switch`
**ID:** `8cf28416-b602-42e4-bb6b-c3684d5641e3`
**Mode:** `single`

**Description:**
Controls bedroom lights, LEDs, and covers using a 4-button MQTT scene switch (Jakub's bedside switch).

**Triggers:**
MQTT device actions (device_id: `69ae3ac5ef96ef91b933cdd39a92b6c2`):
- Buttons 1-4: single, double, and hold actions

**Actions:**

| Button | Action | Behavior |
|--------|--------|----------|
| 1 - Single | Toggle | Toggle `light.bedroom_jakub` |
| 3 - Single | Toggle | Toggle `light.bedroom_leds` |
| 1 - Hold | Turn off | Turn off all bedroom area lights |
| 3 - Hold | Turn off | Turn off all lights on ground floor, first floor, and backyard |
| 2 - Single | Cover open | Open all bedroom covers |
| 4 - Single | Cover close | Close all bedroom covers |
| 2 - Double | Cover stop | Stop all bedroom covers |
| 4 - Double | Cover position | Set bedroom covers to 20% open |

**Example:**
Jakub presses button 1 once to toggle his bedside light, or presses button 2 to open the bedroom blinds in the morning.

---

### 5. Bedroom Wardrobe Light Switch

**Alias:** `Bedroom Wardrobe Light Switch`
**ID:** `38fcd1d1-292c-4e13-8d52-af8b78a21df2`
**Mode:** `single`

**Description:**
Simple toggle control for the wardrobe light using an MQTT button.

**Triggers:**
- MQTT device (device_id: `42a3d9a108ccf15bca1014a5148c16c6`) single button press

**Actions:**
- Toggle `light.bedroom_wardrobe`

**Example:**
You press the button near the wardrobe to turn the light on or off.

---

### 6. Bedroom bed presence during sleeping time

**Alias:** `Bedroom bed presence during sleeping time`
**ID:** `40f5de15-b7e6-4fea-9cd4-9fdccc564d87`
**Mode:** `restart`

**Description:**
Provides gentle bed stripe lighting when movement is detected in bed during sleeping time, automatically turning off when movement stops.

**Triggers:**
Any of these presence sensors turn "on":
- `binary_sensor.presence_sensor_bedroom_jakub_side`
- `binary_sensor.presence_sensor_bedroom_sona_side`
- `binary_sensor.bedroom_walking_area_presence`

**Conditions:**
All must be true:
- At least one bed presence sensor is "on"
- `binary_sensor.bedroom_is_dark` is "on"
- `binary_sensor.sleeping_time` is "on"

**Actions:**
1. Turn on `light.bed_stripe` at 1% brightness with warm color (RGB: 249, 255, 194)
2. Wait until all presence sensors turn "off" (timeout: 30 seconds)
3. Wait additional 3 seconds
4. Turn off `light.bed_stripe`

**Example:**
At 2:00 AM during sleeping time, you get up to go to the bathroom. The bed stripe light turns on at minimal brightness. When you return and settle back in bed, the light automatically turns off after no movement is detected for 3 seconds.

---

### 7. Cover windows when sunset

**Alias:** `bedroom_cover_windows_when_sunset_on_just_before_sunrise`
**ID:** `95466e53-ec2b-4c08-ad2b-c7edba4158ff`
**Mode:** `single`

**Description:**
Automatically closes bedroom window covers for privacy at sunset and before sunrise.

**Triggers:**
- Sunset + 30 minutes offset
- Sunrise - 1 hour offset (1 hour before sunrise)

**Conditions:**
- `cover.bedroom` is not already "closed"

**Actions:**
- Close all bedroom area covers

**Example:**
At 6:30 PM (30 minutes after sunset), the bedroom blinds automatically close for privacy. They also close at 5:00 AM (1 hour before sunrise).

---

### 8. Uncover windows when sleeping time off

**Alias:** `bedroom_uncover_windows_when_sleeping_time_off`
**ID:** `3edc8a96-1be1-4396-88bc-da64ab5d7436`
**Mode:** `single`

**Description:**
Opens bedroom window covers when sleeping time ends to let in natural light.

**Triggers:**
- `binary_sensor.sleeping_time` changes from "on" to "off"

**Conditions:**
- `cover.bedroom` is not already "open"

**Actions:**
- Open all bedroom area covers

**Example:**
When your morning alarm goes off and sleeping time ends, the bedroom blinds automatically open to help you wake up naturally.

---

### 9. Wardrobe lights on when occupied

**Alias:** `wardrobe_lights_on_when_occupied`
**ID:** `618bc813-203f-42cc-8a55-21e89c0ca4b0`
**Mode:** `restart`

**Description:**
Smart wardrobe lighting that turns on when occupied and turns off based on usage patterns.

**Triggers:**
- `binary_sensor.bedroom_wardrobe_occupancy` turns "on" (id: `occupancy_detected`)
- `binary_sensor.bedroom_wardrobe_occupancy` turns "off" for 30 seconds (id: `no_occupancy_short`)
- `binary_sensor.bedroom_wardrobe_occupancy` turns "off" for 30 minutes (id: `no_occupancy_long`)

**Actions:**

#### Occupancy detected:
- If `light.bedroom_wardrobe` is "off", turn it on

#### No occupancy for 30 seconds:
- If light was changed within last 5 minutes (300 seconds), turn it off
- This handles automation-controlled lights

#### No occupancy for 30 minutes:
- Turn off light regardless of how it was turned on
- This is cleanup for manually controlled lights

**Example:**
You open the wardrobe door to get clothes. The light automatically turns on. After you close the door and walk away (30 seconds), the light turns off. If you manually turned the light on and forgot to turn it off, it will automatically turn off after 30 minutes.

---

### 10. Bedroom and ensuite vacancy timeout

**Alias:** `Bedroom and ensuite vacancy timeout`
**ID:** `a8f3c9d2-7e41-4b2a-9c1e-5d8f2b4e6a3c`
**Mode:** `single`

**Description:**
Safety automation that turns off all bedroom and ensuite lights after extended absence.

**Triggers:**
Either sensor turns "off" for 10 minutes:
- `binary_sensor.bedroom_presence`
- `binary_sensor.ensuite_bathroom_presence`

**Conditions:**
Both sensors must be "off":
- `binary_sensor.bedroom_presence` is "off"
- `binary_sensor.ensuite_bathroom_presence` is "off"

**Actions:**
- Turn off `light.bedroom` and `light.ensuite_bathroom`

**Example:**
You leave the bedroom to go downstairs. After 10 minutes with no presence detected in either the bedroom or ensuite, all lights are turned off to save energy.

---

### 11. En suite Bathroom lights

**Alias:** `En suite Bathroom lights`
**ID:** `067898ef-0474-4733-b2c9-763d270d432b`
**Mode:** `restart`

**Description:**
Automated ensuite bathroom lighting with brightness control based on time of day and darkness.

**Triggers:**
- Home Assistant start
- Automation reloaded event
- `binary_sensor.ensuite_bathroom_presence` changes from "off" to "on"
- `binary_sensor.ensuite_bathroom_presence` changes from "on" to "off" for 2 seconds

**Actions:**

#### When presence detected and dark:
- **Between 23:00 (11 PM) and 07:00 (7 AM):**
  - Turn on `light.en_suite_bulb_top_middle` at 1% brightness (nighttime mode)
- **Other times:**
  - Turn on `light.ensuite_bathroom_main_with_power` at 17% brightness

#### When no presence detected for 2 seconds:
- Turn off all ensuite bathroom lights

**Example:**
At 2:00 AM, you enter the ensuite bathroom. Only the top middle bulb turns on at 1% brightness, providing minimal light. During the day at 3:00 PM, the main lights turn on at 17% brightness.

---

### 12. En suite Bathroom lights switch

**Alias:** `En suite Bathroom lights switch`
**ID:** `af54c161-50b6-4fd6-8839-2f2a2cd25fb7`
**Mode:** `single`

**Description:**
Manual control of ensuite bathroom lights using a 2-button MQTT switch.

**Triggers:**
MQTT device actions (device_id: `0cdbfa488fc3cf989f29e4fa01cd6520`):
- Button 1: single press
- Button 2: single press, double press

**Actions:**

| Button | Action | Behavior |
|--------|--------|----------|
| 1 - Single | Toggle | Toggle `light.ensuite_bathroom_leds` |
| 2 - Single | Toggle | Toggle `light.ensuite_bathroom_main` |
| 2 - Double | Full brightness | Turn on `light.ensuite_bathroom_main` at 100% |

**Example:**
You press button 1 to toggle the LED strip lighting, or double-press button 2 for full brightness when you need maximum light.

---

### 13. Bedroom presence

**Alias:** `Bedroom presence`
**ID:** `13b5c7e1-409e-485e-b52b-b4f07adbe059`
**Mode:** `restart`

**Description:**
Main bedroom presence automation that controls lighting based on time of day, sleeping time, and movie mode. Uses `input_boolean.bedroom_movie_mode` for explicit control of dark-room scenarios (replaces implicit TV state dependency for predictable behavior).

**Movie Mode:**
When `input_boolean.bedroom_movie_mode` is enabled, automatic lighting is suppressed. This allows watching TV or movies in the dark without the lights turning on automatically. Toggle movie mode in the Home Assistant UI when you want to watch something in the dark.

**Triggers:**
- Home Assistant start
- Automation reloaded event
- Multiple presence sensors change state:
  - `binary_sensor.bedroom_entrance_presence`
  - `binary_sensor.bedroom_presence`
  - `binary_sensor.bedroom_walking_area_presence`

**Actions:**

#### Daytime presence (not sleeping time):
**Conditions:**
- Entrance or walking area presence detected
- `binary_sensor.bedroom_is_dark` is "on"
- `binary_sensor.sleeping_time` is "off"
- `light.bedroom` is "off"
- `input_boolean.bedroom_movie_mode` is "off"

**Action:**
- Turn on `light.bed_stripe` at 50% brightness, 2951K color temperature (warm light)

#### Sleeping time presence:
**Conditions:**
- Entrance presence detected
- `binary_sensor.bedroom_is_dark` is "on"
- `binary_sensor.sleeping_time` is "on"
- `light.bedroom` is "off"
- `input_boolean.bedroom_movie_mode` is "off"

**Action:**
- Turn on `light.bed_stripe` at 20% brightness, 2951K color temperature (dimmed warm light)

#### No presence (all areas vacant for 5 seconds):
**Conditions:**
- All presence sensors are "off":
  - `binary_sensor.bedroom_presence`
  - `binary_sensor.bedroom_entrance_presence`
  - `binary_sensor.ensuite_bathroom_presence`

**Action:**
- Turn off `light.bed_stripe`

**Example:**
At 10:00 PM (sleeping time), you enter the bedroom. The bed stripe light turns on at 20% with warm lighting. When you leave to go downstairs, after 5 seconds all presence sensors are off and the light turns off. During the day, the same light would turn on at 50% brightness instead. If you want to watch a movie in the dark, enable "Bedroom Movie Mode" in the UI first - lights will stay off when you enter.

---

### 14. Jakub's Cube (MOVED)

> **NOTE:** This automation has been moved to `/packages/misc/automations/misc_cube_control.yaml` per Principle V (Modular Architecture) as it controls cross-area entities (living room TV, ground floor lights).

See `/packages/misc/automations/misc_cube_control.yaml` for the current implementation.
