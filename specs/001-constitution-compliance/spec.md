# Feature Specification: Constitution Compliance Refactoring

**Feature Branch**: `001-constitution-compliance`
**Created**: 2025-12-28
**Status**: Draft
**Input**: User description: "Make sure the current implementation adheres to constitution if not refactor"

## Clarifications

### Session 2025-12-28

- Q: Should TV-based light suppression (movie mode) be removed entirely or preserved via different mechanism? → A: Replace with manual override toggle (like hall) - user controls movie mode
- Q: Does bathroom have door sensor for occupancy state machine? → A: Bathroom has occupancy sensor - sufficient for implementation
- Q: Where should cube automation move to? → A: Move to `/packages/misc/` - new package for miscellaneous cross-area automations

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Predictable Bedroom Lighting with Movie Mode Override (Priority: P1)

When a resident enters the bedroom at night, lights should turn on by default. A manual "movie mode" toggle allows users to suppress automatic lighting when desired (e.g., watching TV in the dark). This replaces the unpredictable TV-state-based behavior with explicit user control.

**Why this priority**: This directly addresses Principle III (Predictable Behavior) while respecting Principle I (manual overrides respected). The current implicit TV dependency is replaced with explicit user control.

**Independent Test**: Can be tested by entering the bedroom with movie mode on/off and verifying lights respond to the toggle state, not TV state.

**Acceptance Scenarios**:

1. **Given** bedroom is dark and movie mode is off, **When** resident enters bedroom, **Then** lights turn on automatically
2. **Given** bedroom is dark and movie mode is on, **When** resident enters bedroom, **Then** lights remain off (user explicitly requested dark)
3. **Given** movie mode is on, **When** user disables movie mode, **Then** normal presence-based lighting resumes
4. **Given** bedroom lights are on, **When** resident leaves bedroom for extended period, **Then** lights turn off regardless of movie mode state

---

### User Story 2 - Automation Naming Convention Compliance (Priority: P1)

All automations must follow the naming convention `{area}_{action}_{trigger}.yaml` as required by Principle V (Modular Architecture).

**Why this priority**: This is a constitutional requirement and affects maintainability and discoverability of automations across the codebase.

**Independent Test**: Can be verified by listing all automation files and checking they follow the pattern.

**Acceptance Scenarios**:

1. **Given** automation files exist in area packages, **When** reviewing file names, **Then** all follow `{area}_{action}_{trigger}.yaml` pattern
2. **Given** a developer searches for bedroom automations, **When** using glob pattern `bedroom_*.yaml`, **Then** all bedroom automations are found

---

### User Story 3 - Cross-Area Dependency Isolation (Priority: P2)

Automations in one area package should not directly control entities in other areas. The cube automation in bedroom currently controls ground floor lights and living room TV.

**Why this priority**: Violates Principle V (Modular Architecture) - "Cross-area dependencies MUST be minimized and explicitly documented." Moving this to `/packages/misc/` improves maintainability.

**Independent Test**: Can be tested by reviewing each area's automations and ensuring they only reference entities within their own area or explicitly shared resources.

**Acceptance Scenarios**:

1. **Given** the cube controller automation, **When** moved to `/packages/misc/automations/`, **Then** it no longer resides in bedroom package
2. **Given** a bedroom area package, **When** reviewing all automations, **Then** no direct control of living room, ground floor, or other area entities

---

### User Story 4 - Consolidated Light Control Logic (Priority: P3)

Duplicate bedroom light control automations should be merged into a single, maintainable automation to reduce complexity.

**Why this priority**: Supports Principle VI (Maintainability & Simplicity) - "Each automation SHOULD have a single, clear purpose" and avoids duplicate logic.

**Independent Test**: Can be tested by verifying light exclusivity behavior still works with a single automation.

**Acceptance Scenarios**:

1. **Given** bed stripe light is turned on, **When** user turns on main bedroom light, **Then** bed stripe turns off automatically
2. **Given** main bedroom light is on, **When** user turns on bed stripe, **Then** main bedroom light turns off automatically
3. **Given** the light control logic, **When** reviewing automation files, **Then** only one file handles light exclusivity (not two separate files)

---

### User Story 5 - Bathroom Occupancy-Based Lighting (Priority: P3)

Bathroom has an occupancy sensor that maintains presence state during stillness. The automation should leverage this sensor for reliable lighting control without requiring a door-based state machine.

**Why this priority**: Supports Principle II (Reliability First) - the existing occupancy sensor provides reliable presence detection even during stillness.

**Independent Test**: Can be tested by sitting still in bathroom for extended period and verifying lights remain on while occupancy sensor reports occupied.

**Acceptance Scenarios**:

1. **Given** bathroom occupancy sensor detects presence, **When** person is still (no motion), **Then** lights remain on because occupancy sensor maintains state
2. **Given** person leaves bathroom, **When** occupancy sensor clears, **Then** lights turn off after appropriate delay

---

### Edge Cases

- What happens when TV media player entity goes offline? Bedroom lights should not be affected (solved by removing TV dependency).
- What happens if cube controller is used while ground floor presence is detected? Lights should respond to cube, then resume normal presence behavior.
- What happens during yamllint validation after file renames? All renamed files must pass linting.
- What happens if bathroom occupancy sensor fails? Fallback to safe state (lights on until manual off or timeout).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Bedroom presence automation MUST turn on lights when dark and presence is detected, unless movie mode override is enabled
- **FR-001a**: Bedroom MUST provide a movie mode manual override toggle (input_boolean) that suppresses automatic lighting when enabled
- **FR-002**: All automation files MUST follow naming convention `{area}_{action}_{trigger}.yaml`
- **FR-003**: Cross-area control automations MUST be relocated to `/packages/misc/` package
- **FR-004**: Duplicate light control logic MUST be consolidated into single automation
- **FR-005**: Bathroom MUST use occupancy sensor for presence-based lighting (no state machine needed - sensor handles stillness)
- **FR-006**: All refactored automations MUST pass yamllint validation
- **FR-007**: All refactored automations MUST include descriptive alias and description fields
- **FR-008**: Cross-area dependencies MUST be documented in automation comments when unavoidable

### Key Entities

- **Bedroom Automations**: Files controlling bedroom lighting and presence behavior
- **Cube Controller**: Multi-gesture device that controls various home functions across the house
- **Bathroom Occupancy**: New input_boolean and automations for bathroom state machine
- **Light Control Logic**: Automation handling mutual exclusivity of bedroom lights

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Bedroom lights turn on within 2 seconds of presence detection in 100% of scenarios when movie mode is disabled (TV state no longer affects behavior)
- **SC-002**: 100% of automation files in area packages follow the `{area}_{action}_{trigger}.yaml` naming convention
- **SC-003**: Zero cross-area entity references exist within individual area automation packages (excluding explicitly shared resources in bootstrap/presence packages)
- **SC-004**: Number of bedroom light control automations reduces from 2 to 1 while maintaining same functionality
- **SC-005**: Bathroom occupancy persists during stillness periods up to 30 minutes without manual intervention
- **SC-006**: All YAML files pass yamllint validation with zero errors
- **SC-007**: Constitutional compliance score improves from current 7.2/10 to at least 8.5/10 based on audit criteria

## Assumptions

- The TV condition use case (watching movies in dark) will be preserved via explicit movie mode toggle, replacing implicit TV state dependency
- Cube controller automation belongs in `/packages/misc/` as it controls cross-area entities
- Bathroom has an occupancy sensor that maintains state during stillness (no door sensor or state machine needed)
- Existing automation behavior for non-refactored areas will remain unchanged
- CI/CD pipeline will validate all changes before merge
