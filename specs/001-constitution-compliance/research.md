# Research: Constitution Compliance Refactoring

**Date**: 2025-12-28
**Feature**: 001-constitution-compliance

## Research Summary

All "NEEDS CLARIFICATION" items have been resolved through codebase exploration. This refactoring uses existing patterns already implemented in the codebase.

---

## 1. Manual Override Pattern (for Movie Mode)

**Decision**: Implement movie mode using the same pattern as hall manual override

**Rationale**: The hall implementation is already documented in CLAUDE.md and proven reliable. It consists of:
1. `input_boolean` for state persistence
2. Safety timeout automation to auto-clear override after inactivity
3. Condition gates in presence automation to check override state

**Source Files**:
- `/packages/areas/stairway/config.yaml` (lines 6-10) - input_boolean definition
- `/packages/areas/stairway/automations/hall_manual_override_safety.yaml` - timeout pattern
- `/packages/areas/stairway/automations/hall_presence.yaml` (lines 45-46, 59-60) - condition gates

**Alternatives Considered**:
- Using TV state directly (current approach) - Rejected: Violates Principle III (unpredictable)
- No override at all - Rejected: Loses movie-watching use case

---

## 2. TV Condition Replacement

**Decision**: Replace TV state conditions with movie mode input_boolean check

**Rationale**: The bedroom_presence.yaml automation currently checks `media_player.bedroom_tv` state at lines 56-57 and 88-89. These conditions will be replaced with `input_boolean.bedroom_movie_mode` checks.

**Current Implementation** (to be removed):
```yaml
# Lines 56-57 and 88-89 in bedroom_presence.yaml
- condition: state
  entity_id: media_player.bedroom_tv
  state: "off"
```

**New Implementation**:
```yaml
- condition: state
  entity_id: input_boolean.bedroom_movie_mode
  state: "off"
```

**Alternatives Considered**:
- Keeping both TV and movie mode conditions - Rejected: Over-complicated, still unpredictable

---

## 3. Light Exclusivity Consolidation

**Decision**: Merge two automations into single `bedroom_lights_exclusivity.yaml`

**Rationale**: Both automations follow identical pattern (trigger on light turn-on, turn off conflicting light). A single automation with multiple triggers is simpler and more maintainable.

**Current Files** (to be deleted):
1. `bedroom_switch_off_big_lights_when_bed_lights_on.yaml` - Trigger: bed lights → Action: turn off non-bed
2. `bedroom_switch_off_bed_stripe_when_other_lights_on.yaml` - Trigger: 5 specific lights → Action: turn off bed stripe

**Consolidated Pattern**:
```yaml
automation:
  - alias: Bedroom Light Exclusivity
    mode: single
    trigger:
      - platform: state
        entity_id: light.bedroom_bed
        to: "on"
        id: bed_on
      - platform: state
        entity_id:
          - light.bedroom_jakub
          - light.bedroom_sona
          - light.bedroom_leds
          - light.bedroom_main
          - light.bedroom_reflectors
        to: "on"
        id: other_on
    action:
      - choose:
          - conditions:
              - condition: trigger
                id: bed_on
            sequence:
              - service: light.turn_off
                target:
                  entity_id: light.bedroom_non_bed
          - conditions:
              - condition: trigger
                id: other_on
            sequence:
              - service: light.turn_off
                target:
                  entity_id: light.bed_stripe
```

**Alternatives Considered**:
- Keeping separate files - Rejected: Duplicate logic, harder to maintain

---

## 4. Cube Automation Relocation

**Decision**: Move cube_jakub.yaml to `/packages/misc/automations/misc_cube_control.yaml`

**Rationale**: The cube automation controls cross-area entities:
- `media_player.living_room_tv` (lines 54-56, 86-93)
- `light.living_room_light_standing_lamp` (line 80)
- All ground floor lights via dynamic variable (lines 8-12)

Placing in bedroom package violates Principle V (Modular Architecture).

**New Package Structure**:
```
packages/misc/
├── config.yaml          # automation: !include_dir_list automations
└── automations/
    └── misc_cube_control.yaml
```

**Alternatives Considered**:
- `/packages/presence/` - Rejected: Presence package is for detection, not manual control
- `/packages/bootstrap/` - Rejected: Bootstrap is for templates and core config, not automations

---

## 5. Automation Naming Convention

**Decision**: Rename files to follow `{area}_{action}_{trigger}.yaml` pattern

**Rationale**: Constitution Principle V requires this naming convention for discoverability.

**Rename Map**:

| Current Name | New Name | Location |
|--------------|----------|----------|
| `scene_switch_sona.yaml` | `bedroom_scene_switch_sona.yaml` | /bedroom/automations/ |
| `scene_switch_jakub.yaml` | `bedroom_scene_switch_jakub.yaml` | /bedroom/automations/ |
| `cooking_mode_off.yaml` | `kitchen_cooking_mode_timeout.yaml` | /kitchen/automations/ |
| `tv.yaml` | `living_room_tv_playback.yaml` | /living_room/automations/ |

**Alternatives Considered**:
- No rename (accept non-compliance) - Rejected: Violates constitution

---

## 6. Bathroom Occupancy Lighting

**Decision**: Use existing occupancy sensor directly; no state machine needed

**Rationale**: Per clarification, bathroom has an occupancy sensor (not just motion). This sensor maintains state during stillness, so no `input_boolean` state machine is required like the toilet.

**Current State**:
- `/packages/areas/bathroom/config.yaml` - Minimal (only includes automations)
- `/packages/areas/bathroom/automations/bathroom_presence.yaml` - May already exist

**Implementation Approach**:
- Add/modify presence automation to use occupancy sensor for reliable lighting
- No need for entry/exit automations or input_boolean

**Alternatives Considered**:
- Full state machine like toilet - Rejected: Occupancy sensor already handles this

---

## Key Patterns Reference

### Pattern: Manual Override with Safety Timeout

```yaml
# config.yaml
input_boolean:
  area_override:
    name: Area Override
    initial: false
    icon: mdi:hand-back-right

# Override safety timeout automation
automation:
  mode: restart  # Key: restarts timer on presence
  trigger:
    - platform: state
      entity_id: input_boolean.area_override
      to: "on"
    - platform: state
      entity_id: binary_sensor.presence
      to: "on"
  condition:
    - condition: state
      entity_id: input_boolean.area_override
      state: "on"
  action:
    - delay:
        minutes: 15  # Safety timeout
    - condition: state  # Gate: only proceed if still no presence
      entity_id: binary_sensor.presence
      state: "off"
    - service: input_boolean.turn_off
      target:
        entity_id: input_boolean.area_override
    - service: light.turn_off
      target:
        entity_id: light.area_lights
```

### Pattern: Override Check in Presence Automation

```yaml
# In presence automation action sequence
- choose:
    - conditions:
        - condition: state
          entity_id: binary_sensor.presence
          state: "on"
        - condition: state
          entity_id: input_boolean.area_override
          state: "off"  # Key: Skip if override active
      sequence:
        - service: light.turn_on
          target:
            entity_id: light.area_lights
```

---

## Research Complete

All technical decisions resolved. Ready for Phase 1 design artifacts.
