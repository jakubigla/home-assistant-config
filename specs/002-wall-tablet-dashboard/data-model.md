# Data Model: Wall Tablet Dashboard

**Feature**: 002-wall-tablet-dashboard
**Date**: 2025-12-28
**Purpose**: Map dashboard sections to Home Assistant entities

## Entity Mapping by Section

### Section 1: Status (Top-Left)

| Card Purpose | Entity ID | Card Type | Notes |
|--------------|-----------|-----------|-------|
| Jakub presence | `person.jakub` | mushroom-person-card | Shows home/away + avatar |
| Sona presence | `person.sona` | mushroom-person-card | Shows home/away + avatar |
| Weather | `weather.forecast_home` | mushroom-chips-card (weather) | Temperature + condition |
| Darkness | `binary_sensor.outdoor_is_dark` | mushroom-chips-card (entity) | Sun icon, on=dark |
| Sleeping time | `binary_sensor.sleeping_time` | mushroom-chips-card (entity) | Moon icon |

### Section 2: Lights (Top-Center-Left)

| Card Purpose | Entity ID | Card Type | Notes |
|--------------|-----------|-----------|-------|
| Ground Floor | `light.ground_floor` | mushroom-light-card | Group control |
| Living Room Lamp | `light.living_room_light_standing_lamp` | mushroom-light-card | With brightness |
| Kitchen | `light.kitchen` | mushroom-light-card | Group |
| Bedroom | `light.bedroom` | mushroom-light-card | Group |
| Bathroom | `light.bathroom_main` | mushroom-light-card | |
| Ensuite | `light.ensuite_bathroom` | mushroom-light-card | Group |
| Hall | `light.hall_bulbs` | mushroom-light-card | Group |
| Stairway | `light.stairway` | mushroom-light-card | |

### Section 3: Climate (Top-Center-Right)

| Card Purpose | Entity ID | Card Type | Notes |
|--------------|-----------|-----------|-------|
| Living Room Climate | `climate.living_room` | mushroom-climate-card | With temperature control |
| Outdoor Temp | `sensor.boschcom_k30_101622729_outdoor_temp_sensor` | mushroom-template-card | Display only |
| Water Heater | `water_heater.boschcom_k30_101622729_waterheater` | mushroom-entity-card | Status + temp |
| DHW Temp | `sensor.boschcom_k30_101622729_dhw1_sensor` | mushroom-template-card | Hot water temp |

### Section 4: Media (Top-Right)

| Card Purpose | Entity ID | Card Type | Notes |
|--------------|-----------|-----------|-------|
| Living Room TV | `media_player.living_room_tv` | mushroom-media-player-card | Play/pause + now playing |
| Bedroom TV | `media_player.bedroom_tv` | mushroom-media-player-card | Play/pause + now playing |
| Spotify | `media_player.spotify_jacob_igla` | mushroom-media-player-card | When active |

### Section 5: Covers (Bottom-Left)

| Card Purpose | Entity ID | Card Type | Notes |
|--------------|-----------|-----------|-------|
| Ground Floor Group | `cover.ground_floor` | mushroom-cover-card | All ground floor curtains |
| Living Room Main | `cover.living_room_main` | mushroom-cover-card | With position |
| Living Room Left | `cover.living_room_left` | mushroom-cover-card | With position |
| Bedroom | `cover.bedroom` | mushroom-cover-card | With position |

### Section 6: Camera (Bottom-Center-Left)

| Card Purpose | Entity ID | Card Type | Notes |
|--------------|-----------|-----------|-------|
| Porch Camera | `camera.porch` | picture-entity | Live stream |
| Motion Detected | `binary_sensor.g5_dome_motion` | mushroom-chips-card | Motion indicator |
| Person Detected | `binary_sensor.g5_dome_person_detected` | mushroom-chips-card | Person indicator |

### Section 7: Modes (Bottom-Center-Right)

| Card Purpose | Entity ID | Card Type | Notes |
|--------------|-----------|-----------|-------|
| Christmas Mode | `input_boolean.christmas_mode` | mushroom-chips-card (toggle) | Tree icon |
| Cooking Mode | `input_boolean.cooking_mode` | mushroom-chips-card (toggle) | Pot icon |
| Hall Override | `input_boolean.hall_manual_override` | mushroom-chips-card (toggle) | Hand icon |

### Section 8: Vacuum (Bottom-Right)

| Card Purpose | Entity ID | Card Type | Notes |
|--------------|-----------|-----------|-------|
| Vacuum Status | `vacuum.sucker` | mushroom-vacuum-card | Status + controls |
| Battery | `sensor.sucker_battery` | (included in vacuum card) | Battery level |

## Entity State Handling

### Unavailable Entity Display

For entities that may be unavailable (e.g., `camera.garden`, some sensors):

```yaml
# Use mushroom card's built-in unavailable handling
# Cards will show "Unavailable" text automatically
# Consider conditional cards to hide completely:
type: conditional
conditions:
  - condition: state
    entity: camera.garden
    state_not: unavailable
card:
  type: picture-entity
  entity: camera.garden
```

### Presence Aggregation

Room presence indicators available but not included in initial scope:

| Entity | Description |
|--------|-------------|
| `binary_sensor.living_room_presence` | Living room occupied |
| `binary_sensor.kitchen_presence` | Kitchen occupied |
| `binary_sensor.bedroom_presence` | Bedroom occupied |
| `binary_sensor.bathroom_presence` | Bathroom occupied |
| `binary_sensor.ground_floor_presence` | Ground floor aggregate |

*Can be added as chips in Status section if dashboard has space.*

## Validation Rules

1. All entity IDs must exist in Home Assistant
2. Group entities (light.*, cover.*) must be pre-configured in packages
3. Media player entities must support play/pause actions
4. Climate entity must support temperature adjustment
5. Vacuum entity must support start/return_to_base actions

## Entity Count Summary

| Section | Entity Count | Card Count |
|---------|--------------|------------|
| Status | 5 | 3 (2 person + 1 chips) |
| Lights | 8 | 8 |
| Climate | 4 | 4 |
| Media | 3 | 3 |
| Covers | 4 | 4 |
| Camera | 3 | 2 (1 camera + 1 chips) |
| Modes | 3 | 1 (chips) |
| Vacuum | 1 | 1 |
| **Total** | **31** | **26** |
