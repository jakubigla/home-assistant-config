# Porch

> Outdoor lighting driven by sunset/sunrise and doorbell notifications pushed to the wall tablet, phone, and laptop.

**Package:** `porch` | **Path:** `packages/areas/outdoor/porch/`

## How It Works

### Lighting

All porch lights turn on 30 minutes after sunset and turn off at sunrise. The automation also re-evaluates on Home Assistant restart and automation reload, so the correct state is always restored. The 30-minute delay after the sun drops below the horizon avoids switching on while ambient light is still sufficient.

### Doorbell Notifications

When the doorbell rings, the kitchen wall tablet navigates to a dedicated doorbell camera view and its screen wakes up. At the same time, a push notification with a camera snapshot is sent to the iPhone. During working hours (08:00--18:00) the MacBook also receives a notification. After the doorbell motion sensor clears for 10 seconds (or after a 30-second timeout, whichever comes first), the tablet automatically returns to the home dashboard.

A helper template sensor (`binary_sensor.doorbell_press`) stays `on` for 5 seconds after each doorbell event, providing a short window that other automations or UI elements can react to.

## Gotchas

- The lights automation uses `mode: restart` -- if the sun state changes rapidly (e.g., during HA restarts), the last evaluation wins.
- The doorbell notification navigates the tablet by a hardcoded `browser_id`. If the tablet is re-provisioned, that ID must be updated in the automation.
- MacBook notifications are time-gated to 08:00--18:00; outside that window only the iPhone and tablet are notified.
- The doorbell press template sensor uses `device_class: occupancy` solely to get a boolean on/off behaviour -- it does not represent physical occupancy.

## Entities

| Entity | Type | Description |
|--------|------|-------------|
| `binary_sensor.doorbell_press` | Template binary sensor (occupancy) | `on` for 5 seconds after the last `event.doorbell` state change |

## Dependencies

| Entity | Why |
|--------|-----|
| `sun.sun` | Determines when to toggle porch lights |
| `event.doorbell` | Doorbell press event that triggers notifications |
| `camera.doorbell` | Snapshot image included in push notifications |
| `binary_sensor.doorbell_motion_sensor` | Holds the tablet on the camera view until motion clears |
| `switch.kitchen_dashboard_screen` | Wakes the wall tablet screen |
| `notify.mobile_app_iglofon_new` | iPhone push notification service |
| `notify.mobile_app_jakubs_macbook_pro` | MacBook push notification service (working hours only) |
| `browser_mod.navigate` | Steers the tablet browser to doorbell/home views |

## File Index

| File | Purpose |
|------|---------|
| `config.yaml` | Package entry point -- includes automations and templates |
| `automations/porch_lights.yaml` | Sunset/sunrise light control |
| `automations/porch_doorbell_notify_tablet.yaml` | Doorbell notification routing to tablet, phone, and laptop |
| `templates/binary_sensors/doorbell_press.yaml` | 5-second doorbell press indicator sensor |
