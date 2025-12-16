# Bathroom Automations

This folder contains automations for the main bathroom lighting control.

## Automations

### Bathroom lights

**Alias:** `Bathroom lights`
**ID:** `0502c715-74bd-461e-8fc7-189e8b6e4a0f`
**Mode:** `restart`

**Description:**
Automatically controls bathroom lighting based on presence detection, with different behaviors depending on the time of day.

**Triggers:**
- Home Assistant start
- Automation reloaded event
- `binary_sensor.bathroom_presence` changes from "off" to "on"
- `binary_sensor.bathroom_presence` changes from "on" to "off" for 30 seconds

**Conditions:**
- None

**Actions:**

#### When presence detected (`binary_sensor.bathroom_presence` is "on"):
- **After 22:00 (10 PM):**
  - Turn on `light.bathroom_ambient` (ambient lighting for nighttime)
- **Before 22:00:**
  - Turn on `light.bathroom_main` (main bathroom lighting)

#### When no presence detected (`binary_sensor.bathroom_presence` is "off" for 30 seconds):
- Turn off all bathroom lights:
  - `light.bathroom_main`
  - `light.bathroom_ambient`
  - `light.bathroom_mirror`

**Example Scenario:**

*Daytime use:*
1. You enter the bathroom at 3:00 PM
2. `binary_sensor.bathroom_presence` turns "on"
3. `light.bathroom_main` turns on immediately
4. You leave the bathroom
5. After 30 seconds with no presence, all bathroom lights turn off

*Nighttime use:*
1. You enter the bathroom at 11:00 PM
2. `binary_sensor.bathroom_presence` turns "on"
3. `light.bathroom_ambient` turns on (softer lighting)
4. You leave the bathroom
5. After 30 seconds with no presence, all bathroom lights turn off
