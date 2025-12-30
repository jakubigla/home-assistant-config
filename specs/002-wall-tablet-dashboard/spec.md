# Feature Specification: Wall Tablet Dashboard

**Feature Branch**: `002-wall-tablet-dashboard`
**Created**: 2025-12-28
**Status**: Draft
**Input**: User description: "create me a dashboard that will include most important things about my home that can be displayed on my tablet which hangs on wall"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - At-a-Glance Home Status (Priority: P1)

As a household member passing by the wall-mounted tablet, I want to quickly see the overall status of my home without interacting with the screen, so I can understand who's home, current conditions, and any issues at a glance.

**Why this priority**: This is the core purpose of a wall-mounted dashboard - passive information display that provides value without requiring interaction. The tablet should serve as an ambient information display first and foremost.

**Independent Test**: Can be fully tested by viewing the dashboard from 1-2 meters away and confirming all key status information is visible and readable without touching the screen.

**Acceptance Scenarios**:

1. **Given** the tablet is mounted on the wall, **When** I walk past it, **Then** I can see at-a-glance: who is home (Jakub/Sona), current weather, outdoor temperature, and whether it's dark outside.
2. **Given** the home has active presence in rooms, **When** I view the dashboard, **Then** I can see which areas of the home are currently occupied.
3. **Given** the dashboard is displaying, **When** the outdoor temperature or weather changes, **Then** the display updates automatically without manual refresh.

---

### User Story 2 - Lighting Control (Priority: P2)

As a household member, I want to control lights throughout the home from the wall tablet, so I can quickly turn lights on/off or adjust brightness without using voice commands or finding individual switches.

**Why this priority**: Lighting control is the most frequently used smart home interaction and provides immediate value from a central location.

**Independent Test**: Can be fully tested by tapping light controls and verifying corresponding lights respond within 1 second.

**Acceptance Scenarios**:

1. **Given** I am at the dashboard, **When** I tap a light control, **Then** the corresponding light toggles on/off within 1 second.
2. **Given** the dashboard shows room lighting, **When** a light is on, **Then** I can see its current state (on/off) and adjust brightness if supported.
3. **Given** I want to control multiple lights, **When** I use an area-level control (e.g., "Ground Floor"), **Then** all lights in that area respond together.

---

### User Story 3 - Climate & Environment Monitoring (Priority: P3)

As a household member, I want to see and control the home's climate system, so I can ensure comfortable temperatures and monitor the heating/hot water status.

**Why this priority**: Climate comfort is important but less frequently adjusted than lighting. Monitoring is more important than control for day-to-day use.

**Independent Test**: Can be fully tested by viewing current temperature readings and adjusting the climate control, then verifying the Bosch heating system responds.

**Acceptance Scenarios**:

1. **Given** I view the dashboard, **When** I look at the climate section, **Then** I can see the current outdoor temperature (from Bosch sensor), living room climate status, and water heater status.
2. **Given** the climate control is visible, **When** I tap to adjust, **Then** I can change the heating mode or target temperature.
3. **Given** the water heater has a current state, **When** I view its status, **Then** I can see if hot water is available (current temperature reading).

---

### User Story 4 - Media Control (Priority: P4)

As a household member, I want to see what's playing on the TVs and control media playback, so I can pause/play content or see what's currently on.

**Why this priority**: Media control is convenient but typically done through dedicated remotes. Dashboard provides a useful secondary control point.

**Independent Test**: Can be fully tested by viewing currently playing media and using play/pause controls.

**Acceptance Scenarios**:

1. **Given** the Living Room TV is playing content, **When** I view the media section, **Then** I can see what's currently playing and control playback.
2. **Given** multiple media players exist, **When** I view the dashboard, **Then** I can see status of both Living Room TV and Bedroom TV.
3. **Given** Spotify is available, **When** I access media controls, **Then** I can see and control Spotify playback.

---

### User Story 5 - Cover/Curtain Control (Priority: P5)

As a household member, I want to control window covers and curtains from the dashboard, so I can adjust privacy and light without walking to each window.

**Why this priority**: Curtain control is less frequent but valuable, especially at sunrise/sunset times.

**Independent Test**: Can be fully tested by opening/closing a curtain from the dashboard and verifying physical response.

**Acceptance Scenarios**:

1. **Given** curtains are closed, **When** I tap the open control, **Then** the selected curtain opens.
2. **Given** I want to control all ground floor curtains, **When** I use the ground floor cover group, **Then** all ground floor curtains respond together.
3. **Given** bedroom curtains have a specific position, **When** I view the dashboard, **Then** I can see their current state (open/closed/partially open).

---

### User Story 6 - Security & Camera View (Priority: P6)

As a household member, I want to see the porch camera feed and security status, so I can check who's at the door or monitor the entrance.

**Why this priority**: Security monitoring is important but the porch camera is the primary use case for a wall-mounted display.

**Independent Test**: Can be fully tested by viewing the camera feed on the dashboard and verifying it shows the live porch view.

**Acceptance Scenarios**:

1. **Given** the G5 Dome camera is recording, **When** I view the security section, **Then** I can see a live or recent snapshot from the porch camera.
2. **Given** motion is detected at the porch, **When** person/vehicle detection triggers, **Then** I receive a visual indication on the dashboard.

---

### User Story 7 - Quick Actions & Modes (Priority: P7)

As a household member, I want to toggle special modes like Christmas Mode or Cooking Mode, so I can activate predefined behaviors without configuring individual devices.

**Why this priority**: Mode toggles provide convenience but are used less frequently than direct controls.

**Independent Test**: Can be fully tested by toggling Christmas Mode and verifying the associated automations activate.

**Acceptance Scenarios**:

1. **Given** Christmas Mode is available, **When** I toggle it on, **Then** the input_boolean.christmas_mode turns on and associated lighting behaviors activate.
2. **Given** Cooking Mode exists, **When** I toggle it, **Then** kitchen lighting adjusts accordingly.

---

### User Story 8 - Robot Vacuum Status (Priority: P8)

As a household member, I want to see the robot vacuum status and send it to clean, so I can monitor cleaning progress and start cleaning when needed.

**Why this priority**: Vacuum control is useful but infrequent - starting a clean or checking status is occasional.

**Independent Test**: Can be fully tested by viewing vacuum status (docked/cleaning) and sending a clean command.

**Acceptance Scenarios**:

1. **Given** the vacuum is docked, **When** I view its status, **Then** I can see it's docked with battery level.
2. **Given** I want to start cleaning, **When** I tap the start button, **Then** the vacuum begins cleaning.

---

### Edge Cases

- What happens when the tablet loses network connectivity? Display a clear offline indicator and show last-known states.
- How does the dashboard handle unavailable entities (e.g., G5 Bullet camera is currently unavailable)? Show unavailable state clearly without breaking the layout.
- What happens during Home Assistant restart? Display reconnecting status and gracefully recover.
- How does the dashboard behave in direct sunlight or at night? Consider brightness auto-adjustment for wall-mounted tablet visibility.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Dashboard MUST display current presence status for all household members (Jakub, Sona) showing home/away state.
- **FR-002**: Dashboard MUST show real-time weather information including current conditions and outdoor temperature.
- **FR-003**: Dashboard MUST display darkness/daylight status using the outdoor_is_dark sensor.
- **FR-004**: Dashboard MUST provide lighting controls for all major areas: Living Room, Kitchen, Bedroom, Bathroom, Ensuite, Hall, Vestibule, Toilet, Stairway, Boiler Room, Laundry, and grouped controls (Ground Floor).
- **FR-005**: Dashboard MUST display climate status including living room climate, outdoor temperature (Bosch sensor), and water heater status.
- **FR-006**: Dashboard MUST show media player status for Living Room TV and Bedroom TV with playback controls.
- **FR-007**: Dashboard MUST provide cover/curtain controls for: Ground Floor group, Living Room Main, Living Room Left, and Bedroom.
- **FR-008**: Dashboard MUST display porch camera feed (G5 Dome) with live or recent snapshot.
- **FR-009**: Dashboard MUST provide toggle controls for special modes: Christmas Mode, Cooking Mode, and Hall Manual Override.
- **FR-010**: Dashboard MUST show robot vacuum status including dock state and battery level, with ability to start cleaning.
- **FR-011**: Dashboard MUST show sleeping time status for context-aware information.
- **FR-012**: Dashboard MUST be optimized for 10-inch tablet display in landscape orientation using a single-page grid layout with all features visible without scrolling or navigation.
- **FR-013**: Dashboard MUST update automatically when entity states change without requiring manual refresh.
- **FR-014**: Dashboard MUST handle unavailable entities gracefully, showing clear unavailable state without breaking layout.

### Key Entities

- **Person**: Jakub, Sona - household members with home/away tracking
- **Weather**: Current conditions, temperature, forecast from weather.forecast_home
- **Climate**: Living room climate control, Bosch heating outdoor temperature, water heater
- **Lighting**: Organized by area (Living Room, Kitchen, Bedroom, Bathroom, Ensuite, Hall, Vestibule, Toilet, etc.) with group controls
- **Covers**: Ground floor, living room (main + left), bedroom curtains
- **Media**: Living Room TV, Bedroom TV, Spotify, HomePod
- **Vacuum**: Robot vacuum "sucker" with dock status and controls
- **Camera**: Porch camera (G5 Dome) for security monitoring
- **Modes**: Christmas Mode, Cooking Mode, Hall Manual Override input_booleans
- **Status Sensors**: Darkness, sleeping time, room occupancy/presence

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can determine home occupancy status (who's home) within 2 seconds of viewing the dashboard.
- **SC-002**: Users can control any light in the home within 3 taps from the main dashboard view.
- **SC-003**: Dashboard displays update within 2 seconds of actual state changes in the home.
- **SC-004**: Dashboard is readable from 2 meters distance for key status information (presence, weather, time).
- **SC-005**: Users can complete common tasks (toggle a light, check camera, view weather) without scrolling on the main view.
- **SC-006**: Dashboard remains responsive and usable during typical daily use without requiring restarts or manual refreshes.
- **SC-007**: 90% of daily interactions can be completed from the main dashboard view without navigating to sub-pages.

## Clarifications

### Session 2025-12-28

- Q: What is the expected tablet screen size? → A: 10-inch tablet (standard wall mount size)
- Q: How should features be organized on screen? → A: Single-page grid (all features visible, compact cards)

## Assumptions

- The wall-mounted tablet is a 10-inch display in landscape orientation (standard wall mount size).
- Dashboard uses a single-page grid layout with compact cards; all 8 feature areas visible without scrolling or tab navigation.
- The wall-mounted tablet runs a modern browser capable of displaying Home Assistant Lovelace dashboards.
- Network connectivity is generally stable within the home.
- The tablet has always-on display or motion-activated wake functionality (handled by tablet settings, not this dashboard).
- Primary use is passive monitoring with occasional interactive control.
- Dashboard is primarily used by Jakub and Sona who are familiar with the home's smart devices.
- The porch camera (G5 Dome) is the primary security camera of interest; garden camera (G5 Bullet) is currently unavailable.
