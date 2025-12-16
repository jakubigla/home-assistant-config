# Laundry Room Automations

This folder contains automations for laundry room lighting control.

## Automations

### Laundry room lights on when occupied

**Alias:** `laundry_room_lights_on_when_occupied`
**ID:** `618bc813-203f-42cc-8a55-21e89c0ca4b1`
**Mode:** `restart`

**Description:**
Smart laundry room lighting that automatically turns on when occupied and intelligently manages turn-off behavior based on whether lights were turned on by automation or manually.

**Triggers:**
- `binary_sensor.laundry_room_sensor_occupancy` turns "on" (id: `occupancy_detected`)
- `binary_sensor.laundry_room_sensor_occupancy` turns "off" for 30 seconds (id: `no_occupancy_short`)
- `binary_sensor.laundry_room_sensor_occupancy` turns "off" for 30 minutes (id: `no_occupancy_long`)

**Conditions:**
- None (conditions are handled within the choose actions)

**Actions:**

#### Occupancy detected:
**Conditions:**
- Trigger ID is `occupancy_detected`
- `light.laundry` is "off"

**Action:**
- Turn on `light.laundry`

#### No occupancy for 30 seconds (short timeout):
**Conditions:**
- Trigger ID is `no_occupancy_short`
- Light was changed less than 5 minutes ago (300 seconds)
  - This indicates the light was likely turned on by automation

**Action:**
- Turn off `light.laundry`

#### No occupancy for 30 minutes (long timeout):
**Conditions:**
- Trigger ID is `no_occupancy_long`
- No additional conditions (cleanup timeout)

**Action:**
- Turn off `light.laundry` regardless of how it was turned on

**Example Scenarios:**

*Automated control:*
1. You enter the laundry room
2. `binary_sensor.laundry_room_sensor_occupancy` turns "on"
3. `light.laundry` automatically turns on
4. You finish loading the washing machine and leave
5. After 30 seconds with no occupancy, lights turn off automatically

*Manual override respected:*
1. You manually turn on the laundry room light
2. You're doing a long task like folding laundry
3. You step out briefly to get something, and the sensor loses occupancy
4. Because the light wasn't changed recently by automation, it stays on during the 30-second window
5. After 30 minutes without occupancy (safety timeout), the light finally turns off

*Safety cleanup:*
1. You manually turn on the light and forget to turn it off
2. You leave the laundry room and don't return
3. After 30 minutes without any occupancy detected, the automation turns off the light to prevent energy waste

**Benefits:**
- Quick turn-off (30 seconds) for automation-controlled lights
- Respects manual control by checking if light was recently changed
- Long timeout (30 minutes) ensures forgotten lights eventually turn off
- Prevents premature turn-offs during tasks that require stepping away briefly
