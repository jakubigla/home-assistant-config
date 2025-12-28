# Data Model: Constitution Compliance Refactoring

**Date**: 2025-12-28
**Feature**: 001-constitution-compliance

## Entities

This feature primarily modifies automation configurations rather than creating new data entities. The following entities are relevant:

### New Entities

#### input_boolean.bedroom_movie_mode

**Purpose**: Manual override flag for movie-watching mode in bedroom

| Attribute | Value |
|-----------|-------|
| Name | Bedroom Movie Mode |
| Initial | false |
| Icon | mdi:movie-open |
| Package | /packages/areas/bedroom/config.yaml |

**State Transitions**:
- `off` → `on`: User enables movie mode (via UI, scene switch, or automation)
- `on` → `off`: User disables movie mode OR safety timeout expires

**Relationships**:
- Checked by: `bedroom_presence.yaml` automation
- Set by: Scene switch automations, Home Assistant UI
- Timeout by: (Optional) Movie mode safety timeout automation

---

### Existing Entities (Referenced)

#### input_boolean.hall_manual_override

**Purpose**: Reference pattern for movie mode implementation

| Attribute | Value |
|-----------|-------|
| Location | /packages/areas/stairway/config.yaml |
| Pattern | Manual override with 15-minute safety timeout |

#### input_boolean.toilet_occupied

**Purpose**: State machine for toilet occupancy (not modified in this feature)

| Attribute | Value |
|-----------|-------|
| Location | /packages/areas/toilet/config.yaml |
| Pattern | Entry/exit detection with input_boolean persistence |

---

## Automation Files

### Modified Automations

| File | Changes |
|------|---------|
| bedroom_presence.yaml | Replace TV state conditions with movie mode check |

### New Automations

| File | Purpose |
|------|---------|
| bedroom_lights_exclusivity.yaml | Consolidated light mutual exclusion |
| bathroom_lights_occupancy.yaml | Occupancy-based lighting |
| misc_cube_control.yaml | Moved cube controller (new location) |

### Renamed Automations

| Old Name | New Name |
|----------|----------|
| scene_switch_sona.yaml | bedroom_scene_switch_sona.yaml |
| scene_switch_jakub.yaml | bedroom_scene_switch_jakub.yaml |
| cooking_mode_off.yaml | kitchen_cooking_mode_timeout.yaml |
| tv.yaml | living_room_tv_playback.yaml |
| cube_jakub.yaml | misc_cube_control.yaml (moved) |

### Deleted Automations

| File | Reason |
|------|--------|
| bedroom_switch_off_big_lights_when_bed_lights_on.yaml | Consolidated |
| bedroom_switch_off_bed_stripe_when_other_lights_on.yaml | Consolidated |
| cube_jakub.yaml | Moved to /packages/misc/ |

---

## Package Structure

### New Package: misc

```yaml
# /packages/misc/config.yaml
automation: !include_dir_list automations
```

**Directory Structure**:
```
packages/misc/
├── config.yaml
└── automations/
    └── misc_cube_control.yaml
```

---

## Entity Relationships Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        BEDROOM AREA                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────┐    ┌─────────────────────────┐   │
│  │ input_boolean.       │    │ binary_sensor.          │   │
│  │ bedroom_movie_mode   │◄───│ bedroom_presence        │   │
│  │                      │    │                         │   │
│  │ Controls whether     │    │ Triggers automation     │   │
│  │ lights auto-turn-on  │    │                         │   │
│  └──────────────────────┘    └─────────────────────────┘   │
│           │                             │                    │
│           ▼                             ▼                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              bedroom_presence.yaml                    │   │
│  │                                                       │   │
│  │  IF presence AND dark AND NOT movie_mode:            │   │
│  │     Turn on lights                                    │   │
│  │  ELIF no presence:                                    │   │
│  │     Turn off lights                                   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │          bedroom_lights_exclusivity.yaml              │   │
│  │                                                       │   │
│  │  IF bed lights on: Turn off non-bed lights           │   │
│  │  IF other lights on: Turn off bed stripe             │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                         MISC PACKAGE                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              misc_cube_control.yaml                   │   │
│  │                                                       │   │
│  │  Controls:                                            │   │
│  │  - media_player.living_room_tv                       │   │
│  │  - light.living_room_light_standing_lamp             │   │
│  │  - All ground floor lights (dynamic)                 │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                       BATHROOM AREA                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────┐    ┌─────────────────────────┐   │
│  │ binary_sensor.       │───►│ bathroom_lights_        │   │
│  │ bathroom_occupancy   │    │ occupancy.yaml          │   │
│  │                      │    │                         │   │
│  │ Maintains state      │    │ Simple on/off based on  │   │
│  │ during stillness     │    │ occupancy sensor        │   │
│  └──────────────────────┘    └─────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Validation Rules

### File Naming
- All automation files MUST match pattern: `{area}_{action}_{trigger}.yaml`
- Exception: Files in `/packages/misc/` use `misc_` prefix

### YAML Linting
- All files MUST pass `yamllint` with project `.yamllint` configuration
- All automations MUST include `alias` and `description` fields

### Cross-Area Dependencies
- Area packages MUST NOT directly control entities from other areas
- Cross-area control automations MUST reside in `/packages/misc/`, `/packages/presence/`, or `/packages/bootstrap/`
