# Garage

> Actionable notification when the garage door is left open, with a one-tap close button.

**Package:** `garage` | **Path:** `packages/areas/outdoor/garage/`

## How It Works

When `binary_sensor.garage_door` stays open for 3 continuous minutes, a time-sensitive
push notification is sent to the iPhone (bypasses Do Not Disturb). The notification
presents two buttons:

- **Close** -- pulses `switch.garage_door` (Satel Integra relay output) to close the door
- **Dismiss** -- acknowledges the alert with no action

A state guard checks that the door is still open before pulsing the switch, so tapping
"Close" on a stale notification after manually closing the door won't accidentally
reopen it. Action IDs are scoped to `context.id` to prevent stale notifications
surviving an HA restart from triggering actions.

If no button is tapped within 1 hour, the automation silently stops. If the door closes
and reopens, `mode: restart` cancels any pending wait and starts a fresh 3-minute timer.

## Gotchas

- `switch.garage_door` is a **momentary pulse**, not a toggle state -- calling `turn_on`
  sends a brief contact closure to the door opener. It cycles the door (open if closed,
  close if open), which is why the state guard is essential.
- The Satel integration has a known issue where rapid successive switch activations can
  fail -- a delay of at least 0.5s is needed between pulses.

## Entities

**Sensors:** `binary_sensor.garage_door` -- door contact (Satel zone), `on` = open
**Switch:** `switch.garage_door` -- Satel switchable output, momentary relay pulse
**Motion:** `binary_sensor.garage_motion` -- PIR sensor (Satel zone), currently unused

## Dependencies

- `notify.mobile_app_iglofon_new` -- iPhone push notification (mobile_app integration)
- `binary_sensor.garage_door` -- Satel Integra zone sensor
- `switch.garage_door` -- Satel Integra switchable output

## File Index

| File | Purpose |
|------|---------|
| `config.yaml` | Package entry point, includes automations |
| `automations/garage_door_open_notify.yaml` | Door-open alert with actionable close button |
