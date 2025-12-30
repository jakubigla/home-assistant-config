# Tasks: Wall Tablet Dashboard

**Input**: Design documents from `/specs/002-wall-tablet-dashboard/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Not requested - manual UI testing per quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each dashboard section.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different sections, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Dashboard file**: `dashboards/tablet.yaml`
- **Configuration**: `configuration.yaml` at repository root
- **Specs**: `specs/002-wall-tablet-dashboard/`

---

## Phase 1: Setup (Dashboard Infrastructure)

**Purpose**: Install dependencies and register dashboard in Home Assistant

- [ ] T001 Install Mushroom Cards via HACS (Frontend → Search "Mushroom" → Install)
- [ ] T002 Install card-mod via HACS (Frontend → Search "card-mod" → Install)
- [ ] T003 Restart Home Assistant to load new frontend resources
- [x] T004 Register dashboard resources and tablet dashboard in configuration.yaml

**configuration.yaml addition**:
```yaml
lovelace:
  mode: yaml
  resources:
    - url: /homeassistant/www/community/lovelace-mushroom/mushroom.js
      type: module
    - url: /homeassistant/www/community/lovelace-card-mod/card-mod.js
      type: module
  dashboards:
    wall-tablet:
      mode: yaml
      filename: dashboards/tablet.yaml
      title: Tablet
      icon: mdi:tablet
      show_in_sidebar: true
      require_admin: false
```

- [x] T005 Create dashboards/tablet.yaml with base structure

**Checkpoint**: Dashboard accessible at /wall-tablet URL (empty view)

---

## Phase 2: Foundational (Dashboard Layout)

**Purpose**: Create the 8-section grid layout that all user stories will populate

**⚠️ CRITICAL**: Layout must be complete before section content can be added

- [x] T006 Create dashboard title and view structure in dashboards/tablet.yaml
- [x] T007 Define 8 sections using Sections layout (2 rows × 4 columns grid)
- [x] T008 Add section titles: Status, Lights, Climate, Media, Covers, Camera, Modes, Vacuum
- [x] T009 Validate YAML with yamllint and check HA configuration

**Checkpoint**: Dashboard shows 8 empty labeled sections in grid layout

---

## Phase 3: User Story 1 - At-a-Glance Home Status (Priority: P1) 🎯 MVP

**Goal**: Display presence, weather, and environmental status at a glance

**Independent Test**: View dashboard from 2m away - confirm Jakub/Sona presence, weather, outdoor temp, darkness status all visible and readable

### Implementation for User Story 1

- [x] T010 [US1] Add mushroom-person-card for person.jakub in Status section of dashboards/tablet.yaml
- [x] T011 [P] [US1] Add mushroom-person-card for person.sona in Status section of dashboards/tablet.yaml
- [x] T012 [US1] Add mushroom-chips-card with weather chip for weather.forecast_home in Status section
- [x] T013 [P] [US1] Add entity chip for binary_sensor.outdoor_is_dark (sun icon) to chips card
- [x] T014 [P] [US1] Add entity chip for binary_sensor.sleeping_time (moon icon) to chips card
- [x] T015 [US1] Apply card-mod styling for larger fonts (24px minimum) for 2m readability

**Checkpoint**: Status section complete - presence and weather visible at a glance from 2m

---

## Phase 4: User Story 2 - Lighting Control (Priority: P2)

**Goal**: Control lights in all major areas from dashboard

**Independent Test**: Tap each light card and verify physical light toggles within 1 second

### Implementation for User Story 2

- [x] T016 [US2] Add mushroom-light-card for light.ground_floor (group) in Lights section of dashboards/tablet.yaml
- [x] T017 [P] [US2] Add mushroom-light-card for light.living_room_light_standing_lamp in Lights section
- [x] T018 [P] [US2] Add mushroom-light-card for light.kitchen (group) in Lights section
- [x] T019 [P] [US2] Add mushroom-light-card for light.bedroom (group) in Lights section
- [x] T020 [P] [US2] Add mushroom-light-card for light.bathroom_main in Lights section
- [x] T021 [P] [US2] Add mushroom-light-card for light.ensuite_bathroom (group) in Lights section
- [x] T022 [P] [US2] Add mushroom-light-card for light.hall_bulbs (group) in Lights section
- [x] T023 [P] [US2] Add mushroom-light-card for light.stairway in Lights section

**Checkpoint**: Lights section complete - all 8 light controls functional

---

## Phase 5: User Story 3 - Climate & Environment (Priority: P3)

**Goal**: Display and control climate, outdoor temp, and water heater status

**Independent Test**: View climate section - confirm outdoor temp visible, tap climate card to adjust temperature

### Implementation for User Story 3

- [x] T024 [US3] Add mushroom-climate-card for climate.living_room in Climate section of dashboards/tablet.yaml
- [x] T025 [P] [US3] Add mushroom-template-card for sensor.boschcom_k30_101622729_outdoor_temp_sensor (outdoor temp display)
- [x] T026 [P] [US3] Add mushroom-entity-card for water_heater.boschcom_k30_101622729_waterheater in Climate section
- [x] T027 [P] [US3] Add mushroom-template-card for sensor.boschcom_k30_101622729_dhw1_sensor (hot water temp)

**Checkpoint**: Climate section complete - temperature and water heater status visible

---

## Phase 6: User Story 4 - Media Control (Priority: P4)

**Goal**: Display now playing and provide playback controls for TVs

**Independent Test**: Play content on Living Room TV, confirm dashboard shows now playing, tap pause to pause

### Implementation for User Story 4

- [x] T028 [US4] Add mushroom-media-player-card for media_player.living_room_tv in Media section of dashboards/tablet.yaml
- [x] T029 [P] [US4] Add mushroom-media-player-card for media_player.bedroom_tv in Media section
- [x] T030 [P] [US4] Add conditional mushroom-media-player-card for media_player.spotify_jacob_igla (show when active)

**Checkpoint**: Media section complete - TV status and controls functional

---

## Phase 7: User Story 5 - Cover/Curtain Control (Priority: P5)

**Goal**: Control curtains/covers from dashboard

**Independent Test**: Tap cover card, confirm physical curtain opens/closes

### Implementation for User Story 5

- [x] T031 [US5] Add mushroom-cover-card for cover.ground_floor (group) in Covers section of dashboards/tablet.yaml
- [x] T032 [P] [US5] Add mushroom-cover-card for cover.living_room_main in Covers section
- [x] T033 [P] [US5] Add mushroom-cover-card for cover.living_room_left in Covers section
- [x] T034 [P] [US5] Add mushroom-cover-card for cover.bedroom in Covers section

**Checkpoint**: Covers section complete - all 4 cover controls functional

---

## Phase 8: User Story 6 - Security & Camera (Priority: P6)

**Goal**: Display porch camera feed with motion indicators

**Independent Test**: View camera section, confirm live feed visible, wave at camera to test motion indicator

### Implementation for User Story 6

- [x] T035 [US6] Add picture-entity card for camera.porch with camera_view: live in Camera section of dashboards/tablet.yaml
- [x] T036 [US6] Add mushroom-chips-card with motion/person detection indicators in Camera section
- [x] T037 [P] [US6] Add entity chip for binary_sensor.g5_dome_motion in chips card
- [x] T038 [P] [US6] Add entity chip for binary_sensor.g5_dome_person_detected in chips card

**Checkpoint**: Camera section complete - live feed and motion indicators visible

---

## Phase 9: User Story 7 - Quick Actions & Modes (Priority: P7)

**Goal**: Toggle special modes from dashboard

**Independent Test**: Toggle Christmas Mode, confirm associated automations activate

### Implementation for User Story 7

- [x] T039 [US7] Add mushroom-chips-card with toggle chips in Modes section of dashboards/tablet.yaml
- [x] T040 [P] [US7] Add toggle chip for input_boolean.christmas_mode (tree icon: mdi:pine-tree)
- [x] T041 [P] [US7] Add toggle chip for input_boolean.cooking_mode (pot icon: mdi:pot-steam)
- [x] T042 [P] [US7] Add toggle chip for input_boolean.hall_manual_override (hand icon: mdi:hand-back-right)

**Checkpoint**: Modes section complete - all 3 mode toggles functional

---

## Phase 10: User Story 8 - Robot Vacuum Status (Priority: P8)

**Goal**: Display vacuum status and provide start control

**Independent Test**: View vacuum status (docked with battery), tap start button to begin cleaning

### Implementation for User Story 8

- [x] T043 [US8] Add mushroom-vacuum-card for vacuum.sucker in Vacuum section of dashboards/tablet.yaml
- [x] T044 [US8] Configure vacuum card to show battery and dock status

**Checkpoint**: Vacuum section complete - status and controls visible

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Final improvements across all sections

- [x] T045 Review all cards for consistent spacing and alignment in dashboards/tablet.yaml
- [ ] T046 [P] Add unavailable entity handling (conditional cards or styling) for entities that may go offline
- [ ] T047 [P] Optimize camera card performance (consider snapshot mode if live causes issues)
- [x] T048 Final yamllint validation of dashboards/tablet.yaml
- [ ] T049 Run quickstart.md checklist validation on physical tablet
- [ ] T050 Document any tablet-specific browser settings needed in quickstart.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - install HACS cards first
- **Foundational (Phase 2)**: Depends on Setup - creates empty grid
- **User Stories (Phase 3-10)**: All depend on Foundational phase
  - User stories can proceed in parallel (different sections)
  - Or sequentially in priority order (P1 → P8)
- **Polish (Phase 11)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (Status)**: Independent - can start after Phase 2
- **US2 (Lights)**: Independent - can start after Phase 2
- **US3 (Climate)**: Independent - can start after Phase 2
- **US4 (Media)**: Independent - can start after Phase 2
- **US5 (Covers)**: Independent - can start after Phase 2
- **US6 (Camera)**: Independent - can start after Phase 2
- **US7 (Modes)**: Independent - can start after Phase 2
- **US8 (Vacuum)**: Independent - can start after Phase 2

All user stories are independent - they populate different sections of the grid.

### Parallel Opportunities

- All cards within a section marked [P] can be added in parallel (different YAML blocks)
- All 8 user stories can be worked on in parallel after Phase 2 (different sections)
- T010-T015 (US1) can run parallel with T016-T023 (US2), etc.

---

## Parallel Example: User Stories 1 + 2

```bash
# After Phase 2 (Foundational) completes, both can start in parallel:

# User Story 1 (Status section):
Task: "Add mushroom-person-card for person.jakub in Status section"
Task: "Add mushroom-person-card for person.sona in Status section"
Task: "Add mushroom-chips-card with weather chip"

# User Story 2 (Lights section) - same time:
Task: "Add mushroom-light-card for light.ground_floor"
Task: "Add mushroom-light-card for light.kitchen"
Task: "Add mushroom-light-card for light.bedroom"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (install cards)
2. Complete Phase 2: Foundational (grid layout)
3. Complete Phase 3: User Story 1 (Status section)
4. **STOP and VALIDATE**: Mount tablet, verify presence/weather visible from 2m
5. Deploy if basic status display is sufficient

### Incremental Delivery

1. Setup + Foundational → Empty grid ready
2. Add US1 (Status) → Test → Can see who's home + weather (MVP!)
3. Add US2 (Lights) → Test → Can control lights (most used feature)
4. Add US3-8 → Test each → Full dashboard complete
5. Each section adds value without breaking previous sections

### Full Build Strategy

All 8 user stories are independent sections, so they can all be implemented in a single session after Phase 2 completes.

---

## Notes

- [P] tasks = different YAML blocks within same file, no conflicts
- [Story] label maps task to specific dashboard section
- Each section should work independently once added
- Test each section before moving to next
- Commit after each phase or logical group
- Validate on actual tablet at checkpoints
