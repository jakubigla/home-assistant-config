# Presence Automations

This folder contains whole-home presence automations that manage lighting and media based on whether anyone is home or present on specific floors.

## Automations

### 1. Presence - no one at home

**Alias:** `Presence - no one at home`
**ID:** `36979f90-ca9d-4a2b-9fa8-296adc42c473`
**Mode:** `single`

**Description:**
Comprehensive automation that turns off all lights and TVs throughout the home when everyone has been away for an extended period. This is an energy-saving and security measure.

**Triggers:**

- `binary_sensor.presence_someone_at_home` changes from "on" to "off" for 15 minutes

**Conditions:**

- None

**Actions:**

1. Turn off all lights on ground floor and first floor
2. Turn off all TVs:
   - `remote.bedroom_tv`
   - `remote.living_room_tv`

**Example Scenarios:**

*Leaving for work:*

1. The last person leaves the house at 8:00 AM
2. `binary_sensor.presence_someone_at_home` turns "off"
3. After 15 minutes (8:15 AM), automation triggers
4. All lights on ground floor and first floor turn off
5. Both bedroom and living room TVs turn off
6. House is in energy-saving mode
7. No lights or media left running unnecessarily

*Brief departure ignored:*

1. You step outside to take out the trash
2. Presence sensor briefly shows no one home
3. You return within 10 minutes
4. The 15-minute condition is never met
5. Automation doesn't trigger
6. Lights and devices remain as they were

*Family departure:*

1. Last family member leaves at 6:00 PM
2. Forgot to turn off several lights and the TV
3. After 15 minutes, all are turned off automatically
4. Saves energy and provides peace of mind
5. Don't need to worry about what was left on

*Return home:*

1. You return home after being away
2. `binary_sensor.presence_someone_at_home` turns "on"
3. This automation won't trigger
4. Other presence automations handle turning on appropriate lights
5. House welcomes you with appropriate lighting

**Key Features:**

- 15-minute delay prevents false triggers from brief absences
- Turns off lights on multiple floors at once
- Handles both TV remotes centrally
- Energy-saving measure
- Security feature (no lights visible from outside when away)
- Works with whole-home presence detection

**Covered Areas:**

- Ground floor: All lights
- First floor: All lights
- Bedroom TV
- Living room TV

**Note:** The backyard floor is not included, which may be intentional to maintain security lighting or other outdoor automations.

---

### 2. Presence - ground floor with 1 min threshold

**Alias:** `Presence - ground floor absent for 1 min`
**ID:** `173458d4-d369-40ba-b239-7299293d1e31`
**Mode:** `restart`

**Description:**
Controls the living room standing lamp based on ground floor presence, providing ambient lighting when someone is present on the ground floor and it's dark.

**Triggers:**

- Home Assistant start
- Automation reloaded event
- `binary_sensor.ground_floor_presence` changes from "off" to "on"
- `binary_sensor.ground_floor_presence` changes from "on" to "off" for 1 minute

**Conditions:**

- None

**Actions:**

#### When presence detected on ground floor

**Conditions:**

- `binary_sensor.ground_floor_presence` is "on"
- `binary_sensor.living_room_is_dark` is "on"

**Action:**

- Turn on `light.living_room_light_standing_lamp`

#### When no presence on ground floor for 1 minute

**Conditions:**

- `binary_sensor.ground_floor_presence` is "off"

**Action:**

- Turn off `light.living_room_light_standing_lamp`

**Example Scenarios:**

*Evening at home:*

1. You come downstairs at 7:00 PM
2. `binary_sensor.ground_floor_presence` turns "on"
3. Living room is dark (`binary_sensor.living_room_is_dark` is "on")
4. `light.living_room_light_standing_lamp` turns on immediately
5. Provides pleasant ambient lighting
6. You stay on ground floor watching TV, working, etc.
7. Light stays on continuously

*Going upstairs for the night:*

1. You leave the ground floor and go to bed at 11:00 PM
2. `binary_sensor.ground_floor_presence` turns "off"
3. After 1 minute of no presence, standing lamp turns off
4. Ground floor is dark for the night

*Daytime presence:*

1. You're on the ground floor during the day
2. Living room has natural light
3. `binary_sensor.living_room_is_dark` is "off"
4. Even though presence is detected, lamp doesn't turn on
5. Natural light is sufficient

*Quick trip upstairs:*

1. You go upstairs briefly to get something
2. Ground floor presence turns "off"
3. You return within 1 minute
4. Light stays on (1-minute threshold not reached)
5. No annoying light cycling for brief absences

*Moving between rooms:*

1. You move from kitchen to living room
2. Both are on ground floor
3. `binary_sensor.ground_floor_presence` stays "on"
4. Standing lamp remains on continuously
5. Provides consistent ambient lighting throughout ground floor

**Key Features:**

- 1-minute threshold prevents light cycling during brief absences
- Only operates when living room is actually dark
- Provides ambient lighting without being too bright
- Standing lamp is ideal for background lighting
- Works with other living room automations (TV, etc.)
- Restart-safe: Ensures correct state after Home Assistant restart

**Why Standing Lamp:**
The standing lamp is chosen because it:

- Provides gentle ambient lighting
- Is less intrusive than overhead lights
- Creates comfortable atmosphere for evening activities
- Complements other living room lighting (TV backlights, etc.)
- Positioned well for general ground floor illumination

**Relationship with Other Automations:**

- Works alongside TV automation which may turn on the standing lamp when TV turns off
- Other area-specific automations control task lighting
- This provides baseline ambient lighting for ground floor presence
