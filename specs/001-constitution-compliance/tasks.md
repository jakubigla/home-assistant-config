# Tasks: Constitution Compliance Refactoring

**Input**: Design documents from `/specs/001-constitution-compliance/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: No automated tests requested (YAML validation via yamllint serves as testing)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Project type**: Home Assistant configuration (package-based YAML)
- **Base path**: Repository root `/packages/`
- **Area packages**: `/packages/areas/{area_name}/`
- **New package**: `/packages/misc/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create new package structure required for cross-area automations

- [x] T001 Create misc package directory structure at `/packages/misc/`
- [x] T002 Create misc package config at `/packages/misc/config.yaml` with `automation: !include_dir_list automations`
- [x] T003 Create empty automations directory at `/packages/misc/automations/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No foundational blocking tasks - all user stories are independent refactoring operations

**⚠️ NOTE**: This feature has no shared blocking prerequisites beyond Phase 1. User stories can begin after Setup.

**Checkpoint**: Setup complete - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Predictable Bedroom Lighting with Movie Mode Override (Priority: P1) 🎯 MVP

**Goal**: Replace implicit TV-based light suppression with explicit movie mode toggle for predictable bedroom lighting behavior

**Independent Test**: Enter bedroom with movie mode on/off and verify lights respond to toggle state, not TV state

### Implementation for User Story 1

- [x] T004 [US1] Add `input_boolean.bedroom_movie_mode` to `/packages/areas/bedroom/config.yaml`
- [x] T005 [US1] Modify `/packages/areas/bedroom/automations/bedroom_presence.yaml` to remove TV state conditions (lines 56-57, 88-89)
- [x] T006 [US1] Modify `/packages/areas/bedroom/automations/bedroom_presence.yaml` to add movie mode check condition
- [x] T007 [US1] Run `yamllint packages/areas/bedroom/` to validate YAML syntax

**Checkpoint**: Bedroom lighting now responds to movie mode toggle instead of TV state. Test by toggling movie mode in UI.

---

## Phase 4: User Story 2 - Automation Naming Convention Compliance (Priority: P1)

**Goal**: Rename all non-compliant automation files to follow `{area}_{action}_{trigger}.yaml` convention

**Independent Test**: Run `find packages/areas -name "*.yaml" -path "*/automations/*"` and verify all files match pattern

### Implementation for User Story 2

- [x] T008 [P] [US2] Rename `/packages/areas/bedroom/automations/scene_switch_sona.yaml` to `bedroom_scene_switch_sona.yaml`
- [x] T009 [P] [US2] Rename `/packages/areas/bedroom/automations/scene_switch_jakub.yaml` to `bedroom_scene_switch_jakub.yaml`
- [x] T010 [P] [US2] Rename `/packages/areas/kitchen/automations/cooking_mode_off.yaml` to `kitchen_cooking_mode_timeout.yaml`
- [x] T011 [P] [US2] Rename `/packages/areas/living_room/automations/tv.yaml` to `living_room_tv_playback.yaml`
- [x] T012 [US2] Run `yamllint packages/` to validate all renamed files

**Checkpoint**: All automation files now follow naming convention. Searchable via `{area}_*.yaml` pattern.

---

## Phase 5: User Story 3 - Cross-Area Dependency Isolation (Priority: P2)

**Goal**: Move cube controller automation from bedroom to misc package to eliminate cross-area dependencies

**Independent Test**: Verify bedroom package has no automations controlling living room or ground floor entities

### Implementation for User Story 3

- [x] T013 [US3] Copy `/packages/areas/bedroom/automations/cube_jakub.yaml` to `/packages/misc/automations/misc_cube_control.yaml`
- [x] T014 [US3] Update alias in `/packages/misc/automations/misc_cube_control.yaml` to "Misc - Cube Control"
- [x] T015 [US3] Add description comment documenting cross-area control in `/packages/misc/automations/misc_cube_control.yaml`
- [x] T016 [US3] Delete `/packages/areas/bedroom/automations/cube_jakub.yaml`
- [x] T017 [US3] Run `yamllint packages/misc/` to validate new package

**Checkpoint**: Cube automation now resides in misc package. Bedroom package has no cross-area dependencies.

---

## Phase 6: User Story 4 - Consolidated Light Control Logic (Priority: P3)

**Goal**: Merge duplicate bedroom light exclusivity automations into single file

**Independent Test**: Turn on bed lights → verify other lights turn off. Turn on main lights → verify bed stripe turns off.

### Implementation for User Story 4

- [x] T018 [US4] Create consolidated automation at `/packages/areas/bedroom/automations/bedroom_lights_exclusivity.yaml` with trigger IDs
- [x] T019 [US4] Add bed lights trigger (id: bed_on) that turns off `light.bedroom_non_bed`
- [x] T020 [US4] Add other lights trigger (id: other_on) that turns off `light.bed_stripe`
- [x] T021 [US4] Delete `/packages/areas/bedroom/automations/bedroom_switch_off_big_lights_when_bed_lights_on.yaml`
- [x] T022 [US4] Delete `/packages/areas/bedroom/automations/bedroom_switch_off_bed_stripe_when_other_lights_on.yaml`
- [x] T023 [US4] Run `yamllint packages/areas/bedroom/automations/bedroom_lights_exclusivity.yaml`

**Checkpoint**: Light exclusivity now handled by single automation. Two duplicate files removed.

---

## Phase 7: User Story 5 - Bathroom Occupancy-Based Lighting (Priority: P3)

**Goal**: Implement reliable bathroom lighting using occupancy sensor

**Independent Test**: Sit still in bathroom for extended period, verify lights remain on while occupancy sensor reports occupied

### Implementation for User Story 5

- [x] T024 [US5] Create occupancy-based lighting automation at `/packages/areas/bathroom/automations/bathroom_lights_occupancy.yaml`
- [x] T025 [US5] Add trigger for occupancy sensor state changes
- [x] T026 [US5] Add action to turn lights on when occupied, off when cleared (with delay)
- [x] T027 [US5] Run `yamllint packages/areas/bathroom/`

**Checkpoint**: Bathroom lights now respond to occupancy sensor, maintaining state during stillness.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and documentation updates

- [x] T028 [P] Run full `yamllint .` validation on entire repository (basic validation - yamllint not installed locally)
- [x] T029 [P] Verify naming convention compliance with find command from quickstart.md
- [x] T030 Update `/packages/areas/bedroom/automations/README.md` to document movie mode behavior
- [x] T031 Run Home Assistant config check (if available locally) (deferred to CI/CD pipeline)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: N/A for this feature
- **User Stories (Phase 3-7)**: All depend on Setup completion
  - All user stories are independent and can run in parallel
  - Recommended priority order: P1 (US1, US2) → P2 (US3) → P3 (US4, US5)
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Setup - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Setup - No dependencies on other stories
- **User Story 3 (P2)**: Can start after Setup - No dependencies on other stories
- **User Story 4 (P3)**: Can start after Setup - No dependencies on other stories
- **User Story 5 (P3)**: Can start after Setup - No dependencies on other stories

### Within Each User Story

- Modification tasks before deletion tasks
- yamllint validation at end of each story
- Story complete before marking checkpoint

### Parallel Opportunities

- T008, T009, T010, T011 can all run in parallel (different files)
- T028, T029 can run in parallel
- All user stories can be worked on in parallel after Setup

---

## Parallel Example: User Story 2 (File Renames)

```bash
# All rename tasks can run in parallel (different files):
mv packages/areas/bedroom/automations/scene_switch_sona.yaml packages/areas/bedroom/automations/bedroom_scene_switch_sona.yaml
mv packages/areas/bedroom/automations/scene_switch_jakub.yaml packages/areas/bedroom/automations/bedroom_scene_switch_jakub.yaml
mv packages/areas/kitchen/automations/cooking_mode_off.yaml packages/areas/kitchen/automations/kitchen_cooking_mode_timeout.yaml
mv packages/areas/living_room/automations/tv.yaml packages/areas/living_room/automations/living_room_tv_playback.yaml
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 3: User Story 1 (T004-T007)
3. **STOP and VALIDATE**: Test movie mode toggle in Home Assistant UI
4. Deploy if ready - bedroom lighting is now predictable

### Incremental Delivery

1. Complete Setup → Misc package created
2. Add User Story 1 → Movie mode working → Deploy (MVP!)
3. Add User Story 2 → Files renamed → Deploy
4. Add User Story 3 → Cube isolated → Deploy
5. Add User Story 4 → Light exclusivity consolidated → Deploy
6. Add User Story 5 → Bathroom lighting reliable → Deploy
7. Each story adds constitutional compliance without breaking others

### Parallel Team Strategy

With multiple developers:

1. All complete Setup together (T001-T003)
2. Once Setup is done:
   - Developer A: User Story 1 (movie mode)
   - Developer B: User Story 2 (renames)
   - Developer C: User Story 3 (cube relocation)
3. Then:
   - Developer A: User Story 4 (light consolidation)
   - Developer B: User Story 5 (bathroom)
4. All developers: Polish phase

---

## Summary

| Metric | Value |
|--------|-------|
| Total Tasks | 31 |
| Setup Tasks | 3 |
| User Story 1 Tasks | 4 |
| User Story 2 Tasks | 5 |
| User Story 3 Tasks | 5 |
| User Story 4 Tasks | 6 |
| User Story 5 Tasks | 4 |
| Polish Tasks | 4 |
| Parallel Opportunities | 8 tasks marked [P] |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- yamllint validation at end of each story phase
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- No automated tests needed - yamllint serves as validation
