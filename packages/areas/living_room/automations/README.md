# Living Room Automations

This folder contains automations for living room curtains and TV lighting control.

## Automations

### 1. Living room curtains

**Alias:** `Living room curtains`
**ID:** `27b3c9f1-c2c3-46c5-bd2a-2bd47abbfe20`
**Mode:** `restart`

**Description:**
Automatically opens and closes living room curtains based on darkness conditions for privacy and natural light management.

**Triggers:**
- `binary_sensor.dark_for_curtains` state changes

**Conditions:**
- None

**Actions:**

#### When dark (close curtains):
**Conditions:**
- `binary_sensor.dark_for_curtains` is "on"
- At least one cover is not fully closed:
  - `cover.living_room_main` is not "closed", OR
  - `cover.living_room_left` is not "closed"

**Action:**
- Close all living room area covers

#### When not dark (open curtains):
**Conditions:**
- `binary_sensor.dark_for_curtains` is "off"
- At least one cover is not fully open:
  - `cover.living_room_main` is not "open", OR
  - `cover.living_room_left` is not "open"

**Action:**
- Open all living room area covers

**Example Scenarios:**

*Evening - closing curtains:*
1. Sun sets and ambient light decreases
2. `binary_sensor.dark_for_curtains` turns "on"
3. Both living room curtains (main and left) automatically close
4. This provides privacy and helps with TV viewing

*Morning - opening curtains:*
1. Sun rises and natural light increases
2. `binary_sensor.dark_for_curtains` turns "off"
3. Both living room curtains automatically open
4. Natural light fills the room

*Partial closure handled:*
1. You manually closed one curtain but left the other open
2. When darkness conditions change, the automation checks each cover independently
3. Only curtains that are not in the target state will be adjusted

---

### 2. Living Room TV

**Alias:** `Living Room TV`
**ID:** `9e959848-5de4-4e82-8874-5250fbc72929`
**Mode:** `queued`

**Description:**
Sophisticated automation that controls TV backlight LEDs based on TV state (playing, paused, off) and manages ambient lighting when TV is turned off.

**Triggers:**
- `media_player.living_room_tv` state changes
- `binary_sensor.ground_floor_presence` turns "off" for 1 hour
- `binary_sensor.living_room_is_dark` changes from "off" to "on"

**Conditions:**
- None

**Actions:**

#### TV is playing and room is dark:
**Conditions:**
- `media_player.living_room_tv` state is "playing"
- `binary_sensor.living_room_is_dark` is "on"
- Trigger was not from the darkness sensor

**Action:**
- Turn on `light.living_room_tv_leds_with_power` at 20% brightness with warm orange color (RGB: 255, 193, 132)

#### TV is paused and room is dark:
**Conditions:**
- `media_player.living_room_tv` state is "paused"
- `binary_sensor.living_room_is_dark` is "on"

**Action:**
- Turn on `light.living_room_tv_leds_with_power` at 100% brightness with warm orange color (RGB: 255, 193, 132)
- Provides more light when content is paused

#### TV is off:
**Conditions:**
- `media_player.living_room_tv` state is "off"

**Actions:**
- **If TV was just turned off AND conditions are met:**
  - Trigger was TV turning off
  - `light.ground_floor_powerful` is "off"
  - `binary_sensor.ground_floor_presence` is "on"
  - `binary_sensor.living_room_is_dark` is "on"
  - **Then:** Turn on `light.living_room_light_standing_lamp` for ambient lighting
- Turn off `light.living_room_tv_leds`

#### TV is on (but not playing):
**Conditions:**
- `media_player.living_room_tv` state is not "off" or "standby"
- `binary_sensor.living_room_is_dark` is "on"

**Action:**
- Turn on `light.living_room_tv_leds_with_power` at 80% brightness with warm orange color (RGB: 255, 193, 132)

**Example Scenarios:**

*Movie night:*
1. Room is dark, you start playing a movie
2. TV enters "playing" state
3. TV LEDs turn on at 20% brightness with warm orange color
4. Provides gentle backlighting without distracting from content
5. You pause the movie to grab snacks
6. TV LEDs immediately increase to 100% brightness
7. More light is available during the pause
8. You resume the movie
9. LEDs return to 20% brightness

*Finishing TV watching:*
1. You're watching TV with LED backlighting at 20%
2. You turn off the TV
3. TV LEDs turn off
4. If room is dark and there's still presence, standing lamp turns on automatically
5. This prevents the room from being completely dark

*Daytime viewing:*
1. You turn on TV during the day
2. Room is not dark (`binary_sensor.living_room_is_dark` is "off")
3. TV LEDs don't turn on
4. Natural light is sufficient

*TV on but idle:*
1. TV is on at home screen (not playing content)
2. Room is dark
3. TV LEDs turn on at 80% brightness
4. Provides good ambient lighting while navigating menus

**LED Brightness Summary:**
- Playing: 20% (minimal distraction)
- Paused: 100% (full lighting)
- On but idle: 80% (good ambient lighting)
- Off: LEDs off (standing lamp may turn on)

**Color:** All TV LED states use warm orange (RGB: 255, 193, 132) for comfortable viewing
