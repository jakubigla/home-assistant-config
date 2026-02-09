# Ground Floor

> Floor-level aggregation package -- rolls up lights, presence, and utility scripts that span every ground-floor room into a single place.

**Package:** `ground_floor` | **Path:** `packages/areas/ground-floor/_floor/`

## How It Works

This is not a room -- it is the umbrella package for the entire ground floor. It exists so that other automations and dashboards can ask simple, floor-wide questions ("is anyone downstairs?", "are any lights on?") and trigger floor-wide actions ("turn everything off", "vacuum a specific room").

**Floor-wide presence** (`binary_sensor.ground_floor_presence`) combines the individual presence/occupancy sensors from six areas -- common area, living room, kitchen, vestibule, toilet, and garden -- into one binary sensor. If any of those areas report someone present, the floor is occupied. It also exposes an `areas_occupied` attribute that lists exactly which rooms are active, which is handy for dashboards and conditional automations.

**Light status** (`binary_sensor.ground_floor_light_status`) dynamically discovers every light entity assigned to a ground-floor area and reports `on` when at least one is lit. It deliberately ignores the living room TV LED strips (`light.living_room_tv_up`, `light.living_room_tv_down`, `light.living_room_leds`) because those are ambient/media lights that should not count as "the lights are on downstairs".

**Powerful lights group** (`light.ground_floor_powerful`) bundles the six brightest fixtures across the floor (kitchen LEDs, kitchen main, kitchen island, dining room, painting walls, hall) into a single group entity. Useful for scenes that need to blast full brightness across the whole floor at once.

**Turn off all lights** (`script.ground_floor_turn_off_all_lights`) targets `floor_id: ground_floor`, which means it automatically catches every light on the floor -- including any new ones added later -- without needing to maintain a manual entity list.

**Vacuum scripts** send the Dreame L10 Ultra to clean specific segments at suction level 3 with mopping (water volume 3):

- `script.vacuum_clean_kitchen` -- segment 2 (kitchen)
- `script.vacuum_clean_mudroom` -- segment 8 (mudroom)

## Gotchas

- The light status sensor uses `floor_areas('ground_floor')` to auto-discover lights, so it picks up new entities as soon as they are assigned to a ground-floor area. The ignored-lights list, however, is hardcoded -- if you add more ambient lights that should be excluded, update `lights_status.yaml` manually.
- The "turn off all lights" script also relies on `floor_id`, not the light group. It will turn off lights the group does not contain (e.g. toilet, vestibule). This is intentional.
- Vacuum segment IDs (`2` for kitchen, `8` for mudroom) are mapped inside the Dreame vacuum's firmware. If you re-map rooms in the Dreame app, these IDs will change silently and the scripts will clean the wrong areas.
- `binary_sensor.common_area_presence` appears in the presence aggregation but does not correspond to a dedicated area package -- it likely comes from a shared/presence package or a Zigbee2MQTT group.

## Entities

**Lights:** `light.ground_floor_powerful` (group of 6 fixtures)

**Sensors:** `binary_sensor.ground_floor_presence` (floor occupancy), `binary_sensor.ground_floor_light_status` (any light on)

**Scripts:** `script.ground_floor_turn_off_all_lights`, `script.vacuum_clean_kitchen`, `script.vacuum_clean_mudroom`

## Dependencies

- `binary_sensor.common_area_presence` -- common area presence
- `binary_sensor.living_room_presence` -- living room presence
- `binary_sensor.kitchen_presence` -- kitchen presence
- `binary_sensor.vestibule_presence` -- vestibule presence
- `binary_sensor.toilet_occupancy` -- toilet occupancy (state-machine pattern)
- `binary_sensor.garden_presence` -- garden/terrace presence
- `vacuum.dreamebot_l10_ultra` -- Dreame L10 Ultra robot vacuum (via `dreame_vacuum.vacuum_clean_segment`)
- `light.kitchen_led`, `light.kitchen_main`, `light.kitchen_island` -- kitchen package
- `light.dining_room` -- dining room light
- `light.ground_floor_painting_walls` -- accent wall lights
- `light.ground_floor_hall` -- ground floor hall light

## File Index

| File | Purpose |
|------|---------|
| `config.yaml` | Entry point -- includes lights/, scripts/, and templates/ subdirectories |
| `lights/powerful.yaml` | Light group combining the six brightest ground-floor fixtures |
| `scripts/switch_off_all_lights.yaml` | Turns off every light on the ground floor via floor_id |
| `scripts/vacuum_clean_kitchen.yaml` | Sends vacuum to clean kitchen segment |
| `scripts/vacuum_clean_mudroom.yaml` | Sends vacuum to clean mudroom segment |
| `templates/binary_sensors/ground_floor_occupied.yaml` | Aggregated floor-wide presence from six area sensors |
| `templates/binary_sensors/lights_status.yaml` | Reports whether any ground-floor light is on (excludes TV LEDs) |
