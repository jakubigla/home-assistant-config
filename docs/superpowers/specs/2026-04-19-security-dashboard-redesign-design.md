# Security Dashboard Redesign — Expanded Zones + Entry/Exit Logbook

**Date:** 2026-04-19
**Scope:** `dashboards/tablet/security.yaml`, `packages/presence/`

## Goal

1. Replace the short, Satel-only motion list with a richer set of security-relevant motion/presence sensors.
2. Add a derived "House Access Event" signal so the Recent Activity log shows human-readable entry/exit lines (`Entry via Garage`, `Exit via Terrace Main`, `Remote open via Garage`) instead of raw binary toggles alone.

Private spaces (bathrooms, wardrobes, bedroom sofa, toilet, laundry, boiler room) are deliberately excluded from the security view.

## Components

### A. Direction-aware template sensor — `sensor.house_access_event`

Trigger-based template, located in `packages/presence/config.yaml`. Listens for a custom `house_access` event and renders its state as a sentence.

```yaml
template:
  - trigger:
      - platform: event
        event_type: house_access
    sensor:
      - name: House Access Event
        state: "{{ trigger.event.data.direction }} via {{ trigger.event.data.via }}"
```

Possible states: `Entry via <door>`, `Exit via <door>`, `Opened via <door>`, `Remote open via Garage`.

### B. Automation — `packages/presence/automations/presence_log_entry_exit.yaml`

Single automation, mode `queued`, produces `house_access` events based on three signals:

- Exterior door opens (`terrace_main_door`, `terrace_left_door`, `balcony_door`, `garage_door`)
- `switch.garage_door` turning on (Satel pulse = remote garage open)
- `binary_sensor.vestibule_motion` (used only as directional context, not a trigger for logging)

Decision table:

| Trigger | Prior signal (last 30s) | Post signal (next 30s) | Emitted event |
|---|---|---|---|
| `switch.garage_door` ON | — | — | `Remote open via Garage` |
| `binary_sensor.garage_door` ON within 60s of switch | — | — | *(suppressed — duplicates the switch event)* |
| Any exterior door opens | vestibule active | — | `Exit via <door>` |
| Any exterior door opens | vestibule quiet | vestibule fires | `Entry via <door>` |
| Any exterior door opens | vestibule quiet | nothing | `Opened via <door>` |

Vestibule motion *without* a door event is intentionally ignored — it's most likely internal transit, not house access.

Sketch:

```yaml
alias: "Presence — log house entry/exit"
id: presence_log_entry_exit
mode: queued
trigger:
  - platform: state
    entity_id:
      - binary_sensor.terrace_main_door
      - binary_sensor.terrace_left_door
      - binary_sensor.balcony_door
      - binary_sensor.garage_door
    from: "off"
    to: "on"
    id: door
  - platform: state
    entity_id: switch.garage_door
    from: "off"
    to: "on"
    id: garage_switch
action:
  - variables:
      door_name: >
        {{ trigger.to_state.attributes.friendly_name if trigger.id == 'door' else 'Garage' }}
      garage_remote_recent: >
        {{ trigger.id == 'door'
           and trigger.entity_id == 'binary_sensor.garage_door'
           and (as_timestamp(now())
                - as_timestamp(states.switch.garage_door.last_changed | default(0))) < 60 }}
      vestibule_recent: >
        {{ is_state('binary_sensor.vestibule_motion', 'on')
           or (as_timestamp(now())
               - as_timestamp(states.binary_sensor.vestibule_motion.last_changed | default(0))) < 30 }}
  - choose:
      - conditions: "{{ trigger.id == 'garage_switch' }}"
        sequence:
          - event: house_access
            event_data: { direction: "Remote open", via: "Garage" }
      - conditions: "{{ garage_remote_recent }}"
        sequence: []   # suppressed duplicate
      - conditions: "{{ vestibule_recent }}"
        sequence:
          - event: house_access
            event_data: { direction: "Exit", via: "{{ door_name }}" }
    default:
      - wait_for_trigger:
          - platform: state
            entity_id: binary_sensor.vestibule_motion
            to: "on"
        timeout: "00:00:30"
        continue_on_timeout: true
      - event: house_access
        event_data:
          direction: "{{ 'Entry' if wait.trigger is not none else 'Opened' }}"
          via: "{{ door_name }}"
```

### C. Dashboard — `dashboards/tablet/security.yaml`

**Alarm column** — unchanged (alarm-panel + ready-to-arm template card + open-garage button).

**Zones column** — replaced with three cards:

1. `type: entities`, title **Perimeter**
   - `binary_sensor.terrace_left_door` (Terrace Left)
   - `binary_sensor.terrace_main_door` (Terrace Main)
   - `binary_sensor.balcony_door` (Balcony)
   - `binary_sensor.garage_door` (Garage)

2. `type: entities`, title **Entry & Outdoor**
   - `binary_sensor.g5_dome_motion` (Front Camera)
   - `binary_sensor.garden_presence` (Garden Camera)
   - `binary_sensor.vestibule_motion` (Vestibule — Satel)
   - `binary_sensor.vestibule_presence` (Vestibule — mmWave)
   - `binary_sensor.garage_motion` (Garage)

3. `type: entities`, title **Interior Transit**
   - `binary_sensor.living_room_motion` (Living Room — Satel)
   - `binary_sensor.living_room_presence` (Living Room — mmWave)
   - `binary_sensor.kitchen_presence` (Kitchen)
   - `binary_sensor.stairway_presence` (Hall / Stairway)
   - `binary_sensor.ground_floor_stairs_presence` (Ground Stairs)
   - `binary_sensor.first_floor_corridor_presence` (First Floor Corridor)
   - `binary_sensor.first_floor_stairs_presence` (First Floor Stairs)

**Doorbell column — logbook card** replaced entity list:

```yaml
- type: logbook
  title: Recent Activity
  hours_to_show: 24
  entities:
    - sensor.house_access_event
    - binary_sensor.presence_someone_at_home
    - alarm_control_panel.main
    - switch.garage_door
    - binary_sensor.terrace_left_door
    - binary_sensor.terrace_main_door
    - binary_sensor.balcony_door
    - binary_sensor.garage_door
```

## Edge Cases

- **Door held open / closed then re-opened** — each `off → on` transition fires a new event; acceptable noise.
- **Garage door opened by remote outside the automation** (e.g., physical remote) — `switch.garage_door` is not involved, so the event falls through to the normal door-open logic (most likely `Entry` if someone then walks into the vestibule, `Opened` otherwise).
- **Vestibule motion that stays active** — `vestibule_recent` uses either current state `on` OR last change < 30s, so stale sensors are handled.
- **Automation queued mode** — two near-simultaneous door events are serialised, so wait-for-trigger logic doesn't collide.

## Out of Scope

- Replacing `alarm-panel` with a keypad-less variant (deferred per user).
- Migrating per-floor section layout; we keep the existing 3-section Home-style layout.
- Per-person arrival/departure (already handled by HA's native `person.*` logbook rendering — not needed here).

## Deployment

Standard workflow per `CLAUDE.md`:
1. Make file changes.
2. `git push` to branch.
3. Trigger HA reload (`homeassistant.reload_config_entry` / full restart for new template sensor if required).
4. Verify the Security tab on the wall tablet via Playwright.
