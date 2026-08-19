---
summary: onoff-only lights silently drop brightness data — light.turn_on succeeds at full blast, no error.
before_action:
  - About to send brightness/brightness_pct/color data in a light.turn_on
  - About to write dim/night-light logic for a light entity
on_symptom:
  - "light turns on at full brightness despite brightness_pct in the automation"
  - "night dim branch fires (trace confirms) but the light is still blinding"
  - "brightness template renders correctly yet has no effect on the light"
---

# onoff-only lights silently ignore brightness

- **`light.turn_on` with `brightness`/`brightness_pct` on a light whose
  `supported_color_modes` is `[onoff]` is silently accepted — the light goes to FULL brightness,
  no error, no warning, trace looks healthy.** The YAML reads as if dimming works; only a live
  attribute check reveals it can't. (`stairway_presence` "dimmed" `light.stairway` to 3% at night
  for months — always ran full blast; fixed by switching the night branch to the standing lamp.)
- **Before writing any brightness/color logic, check the entity:**
  `curl $HA_URL/api/states/<entity> | jq .attributes.supported_color_modes` — `["onoff"]` means
  on/off only (`supported_features: 0`).
- Known onoff-only lights here: `light.stairway`, `light.living_room_light_standing_lamp`.
- Same silent-acceptance family as **missing-entity-silent-noop** (bad entity_id → silent 200):
  HA service calls validate shape, not capability.
