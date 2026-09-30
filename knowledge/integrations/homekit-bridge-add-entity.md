---
summary: Add entity to HomeKit bridge via homekit.reload (no restart); verify by AID in .storage aids keyed by unique_id.
before_action:
  - About to add or remove an entity in the HomeKit bridge config
  - About to restart HA just to register a new HomeKit accessory
  - About to verify a new HomeKit accessory was exposed
on_symptom:
  - "new entity added to homekit include_entities but not in the Home app"
  - "grep for entity_id in homekit aids file finds nothing"
---

# HomeKit bridge: add entity + verify

- **Apply with `homekit.reload`, not a restart and not `reload_core_config`.** Core reload ignores
  the bridge; `homekit.reload` re-reads YAML and restarts only the bridge (brief HomeKit blip, rest
  of HA untouched). Verified 2026-09-30 adding `climate.office_ac` / `climate.gym_ac`.
- **Fix entity_id typos BEFORE the first reload.** HomeKit keys accessories by entity; renaming later
  = new accessory in the Home app, room/scene assignments lost. Z2M device: MQTT publish
  `zigbee2mqtt/bridge/request/device/rename` `{"from","to","homeassistant_rename":true}`. Other
  integrations: WS `config/entity_registry/update` with `new_entity_id` for every entity on the
  device.
- **Verify via the aids file, keyed by unique_id — not entity_id.** On the box,
  `/config/.storage/homekit.<entry_id>.aids` → `data.allocations`, keys
  `<platform>.<domain>.<unique_id>` (e.g. `tuya_local.climate.<uid>`); only entities without a
  unique_id (YAML light groups) are keyed by entity_id. Join via `.storage/core.entity_registry`.
  Key present = bridge created the accessory. `grep entity_id` false-negatives.
