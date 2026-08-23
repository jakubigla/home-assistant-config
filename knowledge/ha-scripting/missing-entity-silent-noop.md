---
summary: A call to a non-existent entity_id is a silent 200 no-op; broad floor/area targets sweep entities you must exclude.
before_action:
  - About to write or review an automation that targets remote.* or media_player.* entities
  - About to sweep lights/switches by floor_id, area_id, or entity_id: all
on_symptom:
  - "automation looks healthy and fires, but one device it targets never responds"
  - "TV / device never turns off on departure while lights work fine"
  - "Entity not found (from /api/states/<entity_id>)"
---

**A service call to an entity_id that does not exist returns HTTP 200 and does not abort the
automation — it is a silent no-op.** No log error, no failed trace step; every later action still
runs. An automation can therefore look perfectly healthy (fires on schedule, `state: on`, recent
`last_triggered`) while one of its targets has never once responded.

- **Grep cannot catch this.** The entity was never declared in any YAML — it doesn't exist anywhere
  to be found. Only the live registry knows: `curl /api/states/<entity_id>` →
  `{"message": "Entity not found."}`. Verify entity_ids against the running instance, not the repo.
- **`remote.X` and `media_player.X` are separate namespaces.** One existing is no evidence the other
  does. `presence_turn_off_lights_and_media_when_away` targeted `remote.living_room_tv` for months;
  `media_player.living_room_tv` (universal) exists, the `remote.` twin never did, so the living room
  TV silently never turned off. Real off paths there: `media_player.living_room_tv_sony_bravia` +
  `media_player.living_room_apple_tv`; the bedroom TV genuinely is `remote.bedroom_tv`.
- **Broad targets (`floor_id`, `area_id`, `entity_id: all`) silently pick up entities you must not
  touch** — and grow new ones as devices are added, so a sweep that was safe when written rots. The
  same away automation swept `light.ensuite_bathroom_main_power` via `floor_id: first_floor`; see
  the relay-feeds-zigbee-bulbs leaf for why cutting it is destructive. Indicator LEDs
  (`*_humidifier_display`, `air_conditioner_display`, `connectivity_kit_ledbox`) also land in
  `light.*` sweeps. Prefer enumerating via template with an explicit exclusion list.
- **Verify a sweep by rendering it before trusting it** — `POST /api/template` with the same
  expression returns the exact entity list the automation will hit. This also catches the case where
  the floor boundary itself is wrong in the registry; see the area-floor-registry-mismatch leaf.
