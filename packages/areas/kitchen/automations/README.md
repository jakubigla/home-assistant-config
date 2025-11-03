# Kitchen Automations

This folder contains automations for kitchen lighting and cooking mode management.

## Automations

### 1. Kitchen presence

**Alias:** `Kitchen presence`
**ID:** `2441c759-3b60-497b-99d0-4bd1d6f1ef28`
**Mode:** `restart`

**Description:**
Automatically controls kitchen LED lights based on presence detection and darkness conditions.

**Triggers:**
- Home Assistant start
- Automation reloaded event
- `binary_sensor.kitchen_presence` changes from "off" to "on"
- `binary_sensor.kitchen_presence` changes from "on" to "off" for 15 seconds

**Conditions:**
- None

**Actions:**

#### When presence detected:
**Conditions:**
- `binary_sensor.kitchen_presence` is "on"
- `binary_sensor.kitchen_is_dark` is "on"

**Action:**
- Turn on `light.kitchen_led`

#### When no presence detected for 15 seconds:
**Conditions:**
- `binary_sensor.kitchen_presence` is "off"

**Action:**
- Turn off `light.kitchen_led`

**Example Scenario:**

*Normal use:*
1. You enter the kitchen at 7:00 PM
2. The kitchen is dark (`binary_sensor.kitchen_is_dark` is "on")
3. `light.kitchen_led` turns on immediately
4. You leave the kitchen
5. After 15 seconds with no presence, the LED lights turn off

*Daytime:*
1. You enter the kitchen at noon with bright sunlight
2. The kitchen is not dark, so lights don't turn on
3. You can manually turn on lights if needed for task lighting

---

### 2. Cooking mode off

**Alias:** `Cooking mode on`
**ID:** `913a01e6-f368-423d-bacf-c04ef2f71385`
**Mode:** `restart`

**Description:**
Automatically turns off kitchen lights when cooking mode is turned off and no one is present in the kitchen. This prevents lights from staying on after you finish cooking.

**Triggers:**
- `input_boolean.cooking_mode` changes from "on" to "off"

**Conditions:**
- `binary_sensor.kitchen_presence` is "off" (no one in the kitchen)

**Actions:**
1. Wait 3 seconds
2. Turn off `light.kitchen_led`

**Example Scenario:**

*After cooking:*
1. You finish cooking and leave the kitchen
2. You turn off cooking mode via your dashboard
3. The automation detects no presence in the kitchen
4. After a 3-second delay, the kitchen LED lights turn off automatically
5. This ensures the kitchen lights don't stay on unnecessarily

*Someone still in kitchen:*
1. You turn off cooking mode but remain in the kitchen
2. The automation detects presence (`binary_sensor.kitchen_presence` is "on")
3. The condition fails, so lights remain on
4. The regular kitchen presence automation will handle turning off lights when you leave

**Note:** The cooking mode is useful when you want to override automatic light control while actively cooking, ensuring lights stay on even if the presence sensor temporarily misses you. When cooking mode is off, normal presence-based automation resumes.
