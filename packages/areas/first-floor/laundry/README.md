# Laundry Room

> Lights turn on when you walk in or open the door, and turn off when the door closes. Also handles push notifications when the washer or dryer finishes a cycle.

**Package:** `laundry` | **Path:** `packages/areas/first-floor/laundry/`
**Floor:** First floor (Piętro) | **Area:** 3.40 m²

## How It Works

### Lighting

The laundry room uses a single automation that handles all lighting based on two physical inputs: a motion sensor and a door contact sensor.

When the occupancy sensor detects movement or the door opens, the light turns on (provided it is not already on). When the door closes, the light turns off immediately -- the assumption being that if you closed the door from outside, you have left the room.

As a safety net, if the occupancy sensor reports no movement for five consecutive minutes, the light turns off regardless of door state. This catches cases where someone leaves the room without closing the door. The automation runs in `restart` mode, so each new trigger event resets any pending timeout.

### Appliance Finish Notifications

The washer and dryer each get an independent push-notification subscription controlled from the Appliances dashboard. For each appliance, you pick a **mode** (`off`, `one_cycle`, or `always`) and a **recipient** (`me`, `sona`, or `both`).

When an appliance's power sensor transitions from `on` to `off` (cycle finished), the matching automation checks the mode:

- `off` -- do nothing, stay silent.
- `one_cycle` -- send the notification to the chosen recipient(s), then auto-reset the mode helper back to `off`. This is the "notify me next time it finishes" subscription: it fires exactly once, so you don't keep getting pinged for every cycle after you stopped caring.
- `always` -- send the notification and leave the mode alone, so every finished cycle triggers a push.

The recipient selector routes each notification to `notify.mobile_app_iglofon_new` (me), `notify.mobile_app_iphone_uzivatela_sona` (Sona), or both targets in sequence.

The **Set both** dashboard shortcut calls `script.set_both_laundry_notify` with a `mode` field, which writes the same value to both `input_select.washer_notify_mode` and `input_select.dryer_notify_mode` in a single action -- useful for "mute everything" or "subscribe to both appliances for the next cycle".

## Gotchas

- **Door close always turns off the light.** There is no check for whether someone is still inside. If you close the door while in the room, the light goes off. This works because the laundry room door is typically only closed from outside.
- **No darkness check.** The light turns on any time occupancy or door events fire, even during the day. This is intentional -- the laundry room has no windows.
- **The safety timeout is 5 minutes**, which is relatively short. If you are in the room with the door open and stay very still (e.g., sorting laundry on a table), the light may turn off. Any subsequent movement re-triggers it immediately.
- **`one_cycle` is sticky until the next finish.** If you set it and then open/close the door, nothing resets it -- only an actual `on→off` transition on the power sensor clears it. If the washer was already off when you flipped the mode, the automation will only fire on the next complete cycle.
- **Notification payload is static.** Messages are hardcoded ("Time to unload the washer/dryer") -- there's no dynamic content (e.g., program type, duration).
- **Recipient and mode are independent.** Changing only the recipient does not re-arm a `one_cycle` that already fired; you have to flip the mode back on.

## Entities

**Lights:** `light.laundry` -- ceiling light
**State:**
- `input_select.washer_notify_mode` -- `off` / `one_cycle` / `always` (initial `off`)
- `input_select.dryer_notify_mode` -- `off` / `one_cycle` / `always` (initial `off`)
- `input_select.washer_notify_recipient` -- `me` / `sona` / `both` (initial `me`)
- `input_select.dryer_notify_recipient` -- `me` / `sona` / `both` (initial `me`)

**Scripts:** `script.set_both_laundry_notify` -- takes a `mode` field and writes both washer and dryer notify-mode selectors in one call

## Dependencies

- `binary_sensor.laundry_room_sensor_occupancy` -- motion/occupancy sensor in the laundry room
- `binary_sensor.laundry_doors` -- door contact sensor
- `binary_sensor.washer_power` -- washer power-monitoring sensor (source of truth for cycle finish)
- `binary_sensor.tumble_dryer_power` -- dryer power-monitoring sensor (source of truth for cycle finish)
- `notify.mobile_app_iglofon_new` -- Jakub's iPhone push notification target
- `notify.mobile_app_iphone_uzivatela_sona` -- Sona's iPhone push notification target

## File Index

| File | Purpose |
|------|---------|
| `config.yaml` | Package entry point; includes automations/ and scripts/, defines the four notify input_selects |
| `automations/laundry_room_lights_on_when_occupied.yaml` | Occupancy and door-driven light control with safety timeout |
| `automations/washer_notify_on_finish.yaml` | Push notification when the washer finishes a cycle |
| `automations/dryer_notify_on_finish.yaml` | Push notification when the dryer finishes a cycle |
| `scripts/set_both_laundry_notify.yaml` | Writes both washer + dryer mode selectors in one call |
