---
summary: Area-to-floor mapping lives in .storage, not this repo — floor_id can silently span the wrong physical floor.
before_action:
  - About to target lights or switches by floor_id or area_id
  - About to trust that an area's floor matches the packages/areas/{floor}/ path it is documented under
on_symptom:
  - "lights on one floor turn off when the automation was scoped to the other floor"
  - "a room's lights get turned off by a sweep that a dedicated area automation should own"
  - "floor_entities() returns entities whose ids are prefixed with the other floor"
---

**Area→floor assignment lives in HA's registry (`.storage/core.area_registry`), which is not in this
repo — the `packages/areas/{floor}/…` path an entity is documented under proves nothing about what
`floor_id` will actually target.** Grep cannot detect the mismatch; only the live registry can.

- **Verify a floor target by rendering it, never by reading the package tree.** `POST /api/template`
  with `{{ floor_entities('ground_floor') | select('match','light\\.') | list }}` and compare
  against the repo layout. Entity ids prefixed with the *other* floor are the tell. (Found live:
  area `hall` sat on floor Ground Floor while holding the eight `light.first_floor_hall_bulb_*`
  entities plus `light.stairway`, so the ground-floor vacancy sweep killed the upstairs corridor
  every time downstairs emptied — and bypassed `input_boolean.hall_manual_override`, which
  `hall_presence` respects.)
- **A floor-wide sweep silently overrides the per-area automation that owns those lights**,
  including its manual-override flag. Two automations targeting one light via different scopes is
  the real defect; scope the sweep, don't add another override check.
- **One physical multi-gang device can legitimately span two floors, so no single area is correct
  for it.** The stairs run on one 2-gang module (device `stairway`, `0xa4c13849ec3b42fd`): gang 1 is
  `light.stairway`, gang 2 is `light.ground_floor` — the *downstairs* hall light (`switch_as_x`,
  `original_name: L2`, despite the floor-sounding entity id). Fix is per-entity, not per-device:
  **an entity-level `area_id` overrides its device's area.**
- **`config/entity_registry/get` returning `area_id: None` means inherited from the device**, not
  unassigned — check the device's area before concluding an entity has none.
- Repair via WebSocket: `config/area_registry/update` (`{area_id, floor_id}`) to move a whole area,
  `config/entity_registry/update` (`{entity_id, area_id}`) to pin one entity out of its device's
  area. Both take effect immediately, no restart.
- Domain-level exclusions within a correct floor (indicator LEDs, bulb-feeding relays) are a
  separate hazard — see the missing-entity-silent-noop and relay-feeds-zigbee-bulbs leaves.
