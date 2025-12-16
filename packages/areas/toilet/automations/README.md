# Toilet Automations

This folder contains automations for toilet lighting control with both presence-based and timeout safety features.

## Automations

### 1. Toilet presence

**Alias:** `toilet_presence`
**ID:** `0d36e3a9-0067-4460-b9c8-e86fe86b8b29`
**Mode:** `restart`

**Description:**
Smart toilet lighting that automatically chooses between ambient and main lighting based on outdoor darkness, with intelligent timeout handling for both automated and manual control.

**Triggers:**
- `binary_sensor.toilet_presence` turns "on" (id: `presence_detected`)
- `binary_sensor.toilet_presence` turns "off" for 3 minutes (id: `no_presence_short`)
- `binary_sensor.toilet_presence` turns "off" for 45 minutes (id: `no_presence_long`)

**Conditions:**
- None

**Actions:**

#### Presence detected:
**When dark outside:**
- **Conditions:**
  - `binary_sensor.outdoor_is_dark` is "on"
  - `light.toilet_ambient` is "off"
- **Action:**
  - Turn on `light.toilet_ambient` (softer lighting)

**When not dark outside:**
- **Conditions:**
  - `binary_sensor.outdoor_is_dark` is "off"
  - `light.toilet_main` is "off"
- **Action:**
  - Turn on `light.toilet_main` (brighter lighting)

#### No presence for 3 minutes (short timeout):
**Conditions:**
- Trigger ID is `no_presence_short`
- At least one light was changed in the last 10 minutes (600 seconds):
  - `light.toilet_ambient` was changed within 10 minutes, OR
  - `light.toilet_main` was changed within 10 minutes

**Action:**
- Turn off both `light.toilet_ambient` and `light.toilet_main`

#### No presence for 45 minutes (long timeout):
**Conditions:**
- Trigger ID is `no_presence_long`
- No additional conditions (safety cleanup)

**Action:**
- Turn off both `light.toilet_ambient` and `light.toilet_main`

**Example Scenarios:**

*Nighttime use:*
1. You enter the toilet at 11:00 PM
2. It's dark outside (`binary_sensor.outdoor_is_dark` is "on")
3. `light.toilet_ambient` turns on (softer lighting)
4. You finish and leave
5. After 3 minutes without presence, light turns off

*Daytime use:*
1. You enter the toilet at 2:00 PM
2. It's not dark outside
3. `light.toilet_main` turns on (brighter lighting)
4. You leave
5. After 3 minutes, light turns off

*Manual override respected:*
1. You manually turn on the toilet light before automation triggers
2. You use the toilet and leave
3. Light was not changed by automation recently
4. Short timeout (3 minutes) doesn't turn off the light
5. After 45 minutes (safety timeout), light finally turns off

*Forgotten light cleanup:*
1. Someone manually turns on the light and forgets to turn it off
2. They leave the toilet
3. After 45 minutes without any presence, lights turn off automatically
4. Prevents energy waste from forgotten lights

**Benefits:**
- Automatic lighting selection based on time of day
- Quick turn-off (3 minutes) for automation-controlled lights
- Respects manual control by checking recent light changes
- Safety timeout (45 minutes) ensures forgotten lights are eventually turned off
- Dual-light system (ambient vs main) for comfort

---

### 2. Toilet lights (timeout safety)

**Alias:** `Toilet lights`
**ID:** `d2557486-4168-40b4-b708-c5517ed1e0a1`
**Mode:** `restart`

**Description:**
Safety automation that prevents toilet lights from being left on for extended periods. This is a backup to the presence-based automation and handles cases where lights are manually controlled or presence detection fails.

**Triggers:**
- `light.toilet_main` changes from "off" to "on" for 20 minutes
- `light.toilet_ambient` changes from "off" to "on" for 20 minutes

**Conditions:**
- None

**Actions:**
- Turn off the light that triggered the automation (`{{ trigger.entity_id }}`)

**Example Scenarios:**

*Forgotten main light:*
1. Someone turns on `light.toilet_main` manually
2. They leave but the light stays on
3. Presence automation might not detect the vacancy
4. After 20 minutes of being continuously on, this automation triggers
5. `light.toilet_main` turns off automatically

*Forgotten ambient light:*
1. `light.toilet_ambient` is turned on at night
2. Light stays on for extended period
3. After 20 minutes, automation turns it off
4. Prevents energy waste

*Normal use - no interference:*
1. You use the toilet normally (less than 20 minutes)
2. Either presence automation turns off lights, or you do it manually
3. This timeout automation never triggers
4. No interference with normal use

**Benefits:**
- Acts as a safety net for the presence-based automation
- Prevents lights from being on for unreasonably long periods
- 20-minute timeout is long enough for normal use but short enough to save energy
- Each light (main and ambient) is monitored independently
- Works even if presence detection fails or is unavailable

**Relationship with toilet_presence automation:**
- `toilet_presence`: Primary automation, handles normal operations
- `toilet_lights`: Safety backup, handles edge cases and failures
- Together they ensure toilet lights are never left on indefinitely
- `toilet_presence` has 3-minute and 45-minute timeouts based on presence
- `toilet_lights` has 20-minute absolute timeout regardless of presence
