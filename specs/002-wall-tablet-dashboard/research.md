# Research: Wall Tablet Dashboard

**Feature**: 002-wall-tablet-dashboard
**Date**: 2025-12-28
**Purpose**: Resolve technical decisions for Lovelace dashboard implementation

## Research Topics

### 1. Dashboard Card Framework Selection

**Decision**: Use Mushroom Cards as the primary card framework

**Rationale**:
- Most popular and actively maintained custom card collection for Home Assistant
- Clean, modern Material Design aesthetic suitable for wall-mounted displays
- Comprehensive coverage: entity, light, climate, media, cover, person, vacuum cards
- "Chip" cards provide compact status indicators (ideal for single-page layout)
- Clear iconography makes dashboard easy to understand at a glance
- Great for households with varying tech-savviness
- Full editor support and works with light/dark themes

**Alternatives Considered**:
- Default Lovelace cards: Less visually cohesive, larger footprint per card
- Dwains Dashboard: Auto-generating but less control over layout
- Button Card: More powerful but requires more configuration overhead

**Installation**: Via HACS (Home Assistant Community Store)

### 2. Layout Strategy for 10-inch Tablet

**Decision**: Use native Sections layout (HA 2024.3+) with grid organization

**Rationale**:
- Native HA feature (no custom card dependency for layout)
- Drag-and-drop support for easy rearrangement
- Responsive grid system designed for different screen sizes
- Sections can group related cards (Status, Lights, Climate, etc.)

**Alternatives Considered**:
- Layout Card (custom): More powerful but adds dependency
- Masonry Layout: Less predictable positioning for fixed displays
- Vertical Stack/Horizontal Stack: Works but less flexible

**Grid Organization** (8 sections for 10-inch landscape):
```
┌─────────────┬─────────────┬─────────────┬─────────────┐
│   Status    │   Lights    │   Climate   │    Media    │
│  (Presence, │  (Area      │  (Temp,     │  (TV, Now   │
│   Weather)  │   controls) │   Heating)  │   Playing)  │
├─────────────┼─────────────┼─────────────┼─────────────┤
│   Covers    │   Camera    │    Modes    │   Vacuum    │
│  (Curtains) │  (Porch)    │  (Quick     │  (Status,   │
│             │             │   Actions)  │   Control)  │
└─────────────┴─────────────┴─────────────┴─────────────┘
```

### 3. Card Type Mapping to Features

| Feature Area | Mushroom Card Type | Entities |
|--------------|-------------------|----------|
| Presence | `mushroom-person-card` | person.jakub, person.sona |
| Weather | `mushroom-chips-card` + weather chip | weather.forecast_home |
| Status | `mushroom-chips-card` | outdoor_is_dark, sleeping_time |
| Lights | `mushroom-light-card` | light.* by area |
| Climate | `mushroom-climate-card` | climate.living_room |
| Climate (Outdoor) | `mushroom-template-card` | sensor.boschcom_*_outdoor_temp |
| Water Heater | `mushroom-entity-card` | water_heater.boschcom_* |
| Media | `mushroom-media-player-card` | media_player.living_room_tv, bedroom_tv |
| Covers | `mushroom-cover-card` | cover.* |
| Camera | `picture-entity` (native) | camera.porch |
| Modes | `mushroom-chips-card` with toggles | input_boolean.* |
| Vacuum | `mushroom-vacuum-card` | vacuum.sucker |

### 4. Additional Custom Cards (Optional Enhancements)

**Recommended**:
- `card-mod` (v3.4.5+): CSS styling for customization (font sizes for 2m visibility)
- `browser-mod`: Tablet-specific features (prevent screen dimming, fullscreen)

**Not Required** (Mushroom covers these):
- Mini Media Player: Mushroom media-player-card is sufficient
- Mini Graph Card: Not needed for this dashboard scope
- Thermostat Card: Mushroom climate-card is sufficient

### 5. Theme Considerations

**Decision**: Use default Home Assistant dark theme with increased font sizes

**Rationale**:
- Dark theme reduces eye strain and power consumption on OLED tablets
- Increased font sizes (via card-mod) ensure readability from 2m
- Consistent with typical "always-on" wall display best practices

**Implementation**:
- Create tablet-specific theme or use card-mod for per-card styling
- Target minimum 24px font size for key status text

### 6. Camera Display Options

**Decision**: Use native `picture-entity` card with live stream

**Rationale**:
- Native card, no additional dependencies
- Supports live view or snapshot based on performance needs
- Can tap to view fullscreen

**Configuration**:
```yaml
type: picture-entity
entity: camera.porch
camera_view: live  # or 'auto' for snapshot until tap
```

## Dependencies Summary

| Dependency | Required | Installation |
|------------|----------|--------------|
| Mushroom Cards | Yes | HACS |
| card-mod | Recommended | HACS |
| browser-mod | Optional | HACS |
| Layout Card | No | - |

## Sources

- [Home Assistant Cards Documentation](https://www.home-assistant.io/dashboards/cards/)
- [Home Assistant Sections Layout](https://www.home-assistant.io/blog/2024/03/04/dashboard-chapter-1/)
- [5 Must-Have Custom Cards - XDA](https://www.xda-developers.com/new-custom-cards-for-home-assistant-dashboard/)
- [Best Dashboard Themes 2025 - SmartHomeScene](https://smarthomescene.com/blog/best-home-assistant-dashboard-themes-in-2023/)
- [Dashboard Tour 2025 - Medium](https://medium.com/@rorygallagher2010/home-assistant-smart-home-dashboard-tour-2025-2aecfb0bc6ee)
