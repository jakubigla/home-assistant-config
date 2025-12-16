# Porch Automations

This folder contains automations for porch lighting control based on sun position.

## Automations

### Porch lights

**Alias:** `Porch lights`
**ID:** `8c4dfa1a-b0ab-4b7e-bd88-5bdb8e5c17a8`
**Mode:** `restart`

**Description:**
Automatically controls porch lights based on the sun's position, turning them on after sunset and off after sunrise.

**Triggers:**
- Home Assistant start
- Automation reloaded event
- `sun.sun` changes from "below_horizon" to "above_horizon" (sunrise)
- `sun.sun` changes from "above_horizon" to "below_horizon" for 30 minutes (30 minutes after sunset)

**Conditions:**
- None

**Actions:**

#### When sun is above horizon (daytime):
**Conditions:**
- `sun.sun` state is "above_horizon"

**Action:**
- Turn off all porch area lights

#### When sun is below horizon (nighttime):
**Conditions:**
- `sun.sun` state is "below_horizon"

**Action:**
- Turn on all porch area lights

**Example Scenarios:**

*Evening - lights turn on:*
1. Sun sets at 6:00 PM
2. Automation waits 30 minutes after sunset
3. At 6:30 PM, `sun.sun` has been "below_horizon" for 30 minutes
4. All porch lights turn on automatically
5. Porch is illuminated for evening arrivals and security

*Morning - lights turn off:*
1. Sun rises at 6:00 AM
2. `sun.sun` changes to "above_horizon"
3. All porch lights turn off immediately
4. No need for outdoor lighting during daylight

*Home Assistant restart:*
1. Home Assistant restarts during the evening
2. The automation triggers on startup
3. Checks current sun position
4. If sun is below horizon, turns on porch lights
5. Ensures lights are in correct state after restart

**Note:** The 30-minute delay after sunset ensures lights don't turn on during the "golden hour" when there's still plenty of ambient light. This saves energy while ensuring lights are on when actually needed.

**Covered Areas:**
All lights in the porch area are controlled together, providing consistent illumination for:
- Front door visibility
- Safe navigation
- Security lighting
- Welcoming appearance
