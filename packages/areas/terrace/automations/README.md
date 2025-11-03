# Terrace Automations

This folder contains automations for terrace/garden lighting control.

## Automations

### Terrace lights (Garden presence)

**Alias:** `Terrace lights`
**ID:** `2ad35dfd-49f3-40e3-978d-2cfdfb1ca9c4`
**Mode:** `restart`

**Description:**
Automatically controls terrace wall lights based on garden presence detection and darkness conditions.

**Triggers:**
- Home Assistant start
- Automation reloaded event
- `binary_sensor.garden_presence` changes from "off" to "on"
- `binary_sensor.garden_presence` changes from "on" to "off" for 30 seconds

**Conditions:**
- None

**Actions:**

#### When presence detected in garden:
**Conditions:**
- `binary_sensor.garden_presence` is "on"
- `binary_sensor.garden_is_dark` is "on"

**Action:**
- Turn on `light.terrace_wall`

#### When no presence detected for 30 seconds:
**Conditions:**
- `binary_sensor.garden_presence` is "off"

**Action:**
- Turn off `light.terrace_wall`

**Example Scenarios:**

*Evening garden visit:*
1. You step out onto the terrace at 8:00 PM
2. Garden is dark (`binary_sensor.garden_is_dark` is "on")
3. `binary_sensor.garden_presence` detects you
4. `light.terrace_wall` turns on immediately
5. You're illuminated while on the terrace
6. You go back inside
7. After 30 seconds without presence, terrace light turns off

*Daytime use:*
1. You go out to the garden during the day
2. Garden has plenty of natural light
3. `binary_sensor.garden_is_dark` is "off"
4. Even though presence is detected, lights don't turn on
5. Natural light is sufficient

*Quick trips outside:*
1. You step out to check something at night
2. Lights turn on when you're detected
3. You finish quickly and go back inside
4. After 30 seconds, lights automatically turn off
5. No need to remember to turn them off manually

*Extended outdoor time:*
1. You're having dinner on the terrace at night
2. Lights turn on when you first arrive
3. Lights stay on continuously while presence is detected
4. When you finish and go inside, lights turn off after 30 seconds

**Benefits:**
- 30-second timeout balances energy savings with convenience
- Only operates when garden is actually dark
- Provides safety lighting for outdoor areas
- Automatically handles varying durations of outdoor activity
- Restart-safe: Ensures correct light state after Home Assistant restart

**Coverage Area:**
The terrace wall light provides illumination for:
- Terrace/patio area
- Garden access paths
- Outdoor seating areas
- Safety and security lighting
