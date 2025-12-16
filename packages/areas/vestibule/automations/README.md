# Vestibule Automations

This folder contains automations for vestibule (mudroom/entry) lighting control.

## Automations

### Vestibule presence

**Alias:** `Vestibule presence`
**ID:** `0926eee9-ef8e-4589-86a1-2c917d89f9f2`
**Mode:** `restart`

**Description:**
Automatically controls vestibule/mudroom lighting based on presence detection and garden darkness conditions.

**Triggers:**
- Home Assistant start
- Automation reloaded event
- `binary_sensor.vestibule_presence` changes from "off" to "on"
- `binary_sensor.vestibule_presence` changes from "on" to "off" for 5 seconds

**Conditions:**
- None

**Actions:**

#### When presence detected:
**Conditions:**
- `binary_sensor.vestibule_presence` is "on"
- `binary_sensor.garden_is_dark` is "on"

**Action:**
- Turn on `light.mudroom`

#### When no presence detected for 5 seconds:
**Conditions:**
- `binary_sensor.vestibule_presence` is "off"

**Action:**
- Turn off `light.mudroom`

**Example Scenarios:**

*Evening arrival home:*
1. You enter the vestibule from outside at 7:00 PM
2. It's dark outside (`binary_sensor.garden_is_dark` is "on")
3. `binary_sensor.vestibule_presence` detects you
4. `light.mudroom` turns on immediately
5. You take off your shoes and coat
6. You move into the main house
7. After 5 seconds without presence, light turns off

*Quick entry/exit:*
1. You step into the vestibule to grab your jacket
2. Light turns on when you enter
3. You grab your jacket and leave
4. After 5 seconds, light turns off automatically
5. Very responsive for brief visits

*Daytime use:*
1. You enter the vestibule during daylight hours
2. Garden area is bright (`binary_sensor.garden_is_dark` is "off")
3. Even though presence is detected, lights don't turn on
4. Natural light through windows is sufficient

*Coming home after dark:*
1. You arrive home at 10:00 PM
2. As soon as you step into the vestibule, lights turn on
3. Provides immediate illumination for safe entry
4. You can see to remove shoes, hang coat, etc.
5. Move into the house, light turns off after 5 seconds

**Key Features:**
- Very short turn-off delay (5 seconds) appropriate for an entry area
- Uses garden darkness sensor for appropriate light activation
- Quick response for immediate illumination when entering
- Automatically ensures correct state after Home Assistant restart
- Perfect for transitional space between outdoors and indoors

**Coverage Area:**
The vestibule/mudroom light provides illumination for:
- Entry and exit transitions
- Removing and storing shoes
- Hanging coats and bags
- Package delivery area
- Quick access storage

**Note:** The 5-second timeout is intentionally short because the vestibule is a transit area where people don't typically linger. This ensures lights turn off quickly after passing through, saving energy while maintaining convenience.
