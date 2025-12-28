# Implementation Plan: Constitution Compliance Refactoring

**Branch**: `001-constitution-compliance` | **Date**: 2025-12-28 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-constitution-compliance/spec.md`

## Summary

Refactor Home Assistant configuration to achieve full compliance with the project constitution. Key changes include:
- Replace implicit TV-based light suppression with explicit movie mode toggle (Principle III)
- Rename automations to follow `{area}_{action}_{trigger}.yaml` convention (Principle V)
- Move cube controller automation to `/packages/misc/` (Principle V)
- Consolidate duplicate bedroom light control automations (Principle VI)
- Implement bathroom occupancy-based lighting using existing occupancy sensor (Principle II)

## Technical Context

**Language/Version**: YAML (Home Assistant configuration format)
**Primary Dependencies**: Home Assistant Core (existing), Zigbee2MQTT (existing)
**Storage**: N/A (configuration files only)
**Testing**: yamllint for YAML validation, Home Assistant config check via CI/CD
**Target Platform**: Home Assistant on local server (Raspberry Pi/NUC)
**Project Type**: Configuration-based smart home automation
**Performance Goals**: Automation response within 2 seconds of trigger
**Constraints**: Local-first processing, no cloud dependencies for core features
**Scale/Scope**: Single home with 12 area packages, ~31 automations

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Invisible Automation | PASS | Movie mode toggle respects manual overrides; physical controls unchanged |
| II. Reliability First | PASS | Bathroom uses reliable occupancy sensor; graceful degradation documented |
| III. Predictable Behavior | PASS | Removing TV dependency makes behavior deterministic; movie mode is explicit |
| IV. Local-First Processing | PASS | All changes remain local; no cloud dependencies introduced |
| V. Modular Architecture | PASS | File renames follow convention; cube moves to `/packages/misc/` |
| VI. Maintainability | PASS | Consolidating duplicate automations; clear naming improves discoverability |

**Gate Result**: PASS - All principles satisfied. Proceed to Phase 0.

### Post-Design Re-evaluation (Phase 1 Complete)

| Principle | Status | Post-Design Evidence |
|-----------|--------|----------------------|
| I. Invisible Automation | PASS | Movie mode is optional; default behavior unchanged for guests |
| II. Reliability First | PASS | Occupancy sensor is reliable; no new failure modes introduced |
| III. Predictable Behavior | PASS | Explicit movie mode replaces implicit TV dependency |
| IV. Local-First Processing | PASS | All new entities (input_boolean) are local |
| V. Modular Architecture | PASS | All files renamed; cube properly isolated in /packages/misc/ |
| VI. Maintainability | PASS | 2 automations consolidated to 1; patterns documented |

**Post-Design Gate Result**: PASS - Ready for Phase 2 task generation.

## Project Structure

### Documentation (this feature)

```text
specs/001-constitution-compliance/
├── spec.md              # Feature specification (complete)
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── checklists/          # Quality checklists
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
packages/
├── areas/
│   ├── bathroom/
│   │   ├── config.yaml              # Add occupancy-based lighting
│   │   └── automations/
│   │       └── bathroom_lights_occupancy.yaml  # NEW
│   ├── bedroom/
│   │   ├── config.yaml              # Add input_boolean.bedroom_movie_mode
│   │   └── automations/
│   │       ├── bedroom_presence.yaml           # MODIFY (remove TV condition, add movie mode)
│   │       ├── bedroom_lights_exclusivity.yaml # NEW (consolidated from 2 files)
│   │       ├── bedroom_scene_switch_sona.yaml  # RENAME from scene_switch_sona.yaml
│   │       └── bedroom_scene_switch_jakub.yaml # RENAME from scene_switch_jakub.yaml
│   ├── kitchen/
│   │   └── automations/
│   │       └── kitchen_cooking_mode_timeout.yaml  # RENAME from cooking_mode_off.yaml
│   └── living_room/
│       └── automations/
│           └── living_room_tv_playback.yaml   # RENAME from tv.yaml
├── misc/                            # NEW package
│   ├── config.yaml                  # Package definition
│   └── automations/
│       └── misc_cube_control.yaml   # MOVE from bedroom/cube_jakub.yaml
└── [other packages unchanged]
```

**Structure Decision**: Follows existing package-based architecture. Creates new `/packages/misc/` for cross-area automations. All changes confined to specific area packages with clear rename/move/modify operations.

## Complexity Tracking

No constitution violations requiring justification. All changes simplify existing complexity.

## Files to Modify/Create/Delete

### CREATE
1. `/packages/misc/config.yaml` - New misc package
2. `/packages/misc/automations/misc_cube_control.yaml` - Moved cube automation
3. `/packages/areas/bedroom/automations/bedroom_lights_exclusivity.yaml` - Consolidated light control
4. `/packages/areas/bathroom/automations/bathroom_lights_occupancy.yaml` - New occupancy lighting

### MODIFY
1. `/packages/areas/bedroom/config.yaml` - Add `input_boolean.bedroom_movie_mode`
2. `/packages/areas/bedroom/automations/bedroom_presence.yaml` - Remove TV condition, add movie mode check

### RENAME
1. `scene_switch_sona.yaml` → `bedroom_scene_switch_sona.yaml`
2. `scene_switch_jakub.yaml` → `bedroom_scene_switch_jakub.yaml`
3. `cube_jakub.yaml` → DELETE (moved to misc)
4. `cooking_mode_off.yaml` → `kitchen_cooking_mode_timeout.yaml`
5. `tv.yaml` → `living_room_tv_playback.yaml`

### DELETE
1. `/packages/areas/bedroom/automations/cube_jakub.yaml` - Moved to misc
2. `/packages/areas/bedroom/automations/bedroom_switch_off_big_lights_when_bed_lights_on.yaml` - Consolidated
3. `/packages/areas/bedroom/automations/bedroom_switch_off_bed_stripe_when_other_lights_on.yaml` - Consolidated
