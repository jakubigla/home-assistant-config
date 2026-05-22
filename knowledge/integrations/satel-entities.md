---
summary: Satel ETHM-1 at 192.168.100.7; entity names lack "satel" — query by config_entry_id.
before_action:
  - About to find or control a Satel alarm entity
  - About to work with the alarm panel, garage door, or a motion/door zone
on_symptom:
  - "grep for satel returns no entities"
  - "cannot locate alarm or zone entity"
---

# Satel Integra alarm

ETHM-1 Plus module at **192.168.100.7** (not .1 — that's the UDM gateway). Integration `satel_integra`, config entry `01KJQNXAFJ9VWP5C29P6YY6QH6`. Ports: 7094 (integration), 7090 (GUARDX), 7091 (DLOADX).

## Gotchas

- **Entity names contain no "satel".** Grepping for "satel" finds nothing. Filter the entity registry by `config_entry_id` instead.
- **9 entities:** `alarm_control_panel.main`, `switch.garage_door`, plus motion/door `binary_sensor.*` zones (living_room, vestibule, garage, terrace_left_door, terrace_main_door, garage_door, balcony_door).
