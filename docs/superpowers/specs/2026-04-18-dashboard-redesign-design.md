# Dashboard Redesign — Design Spec

**Date:** 2026-04-18
**Status:** Approved pending implementation planning
**Driver:** Appliance count is growing (new attic vacuum in a few weeks); the single-tab tablet dashboard needs to scale without cluttering the awesome glanceable Home view.

## Goal

Replace the current single-dashboard layout with a **multi-dashboard, multi-tab system** that:

1. Preserves the "awesome glanceable overview" of today's Home view
2. Gives appliances, climate, outdoor, security, etc. dedicated room to grow
3. Serves both wall tablet and phone form-factors with distinct, purpose-built layouts
4. Scales cleanly — adding a new device touches one tab file

## Non-Goals

- No new HACS custom cards beyond what's already installed
- No theme or colour-palette change
- No new appliance integrations (dishwasher/oven etc.) — surface existing power-based state only
- No automatic tablet-vs-phone redirection (HA doesn't support user-agent routing natively)
- Doorbell hidden view keeps panel layout — only moves to the new file location

## Architecture

### Dashboard count

Two Lovelace dashboards registered in `configuration.yaml` under `lovelace.dashboards`:

- **`tablet`** — existing dashboard, expanded to 8 visible tabs + 1 hidden
- **`mobile-phone`** — new dashboard, 4 tabs

The standalone **`dashboards/energy.yaml`** is retired; its content moves to `dashboards/tablet/energy.yaml`.

### File structure

```
dashboards/
├── tablet.yaml                 # thin — title, views list with !include per tab
├── tablet/
│   ├── home.yaml
│   ├── climate.yaml
│   ├── media.yaml
│   ├── appliances.yaml
│   ├── outdoor.yaml
│   ├── security.yaml
│   ├── energy.yaml
│   ├── settings.yaml
│   └── doorbell.yaml           # hidden, programmatic trigger
├── phone.yaml                  # thin — views list with !include per tab
└── phone/
    ├── home.yaml
    ├── rooms.yaml
    ├── away.yaml
    └── energy.yaml
```

Each tab file stays small (~150–300 lines). The top-level `tablet.yaml` and `phone.yaml` are thin stitching files using `!include`.

### Scaling principle

Adding a device (e.g. attic vacuum) → edit one tab file (`tablet/appliances.yaml`), optionally one phone file. No sprawling edits.

## Tablet dashboard

### Tabs (order)

| # | Tab | Icon | Path | Visible |
|---|-----|------|------|---------|
| 1 | Home | `mdi:home` | `/tablet/home` | yes |
| 2 | Climate | `mdi:thermostat` | `/tablet/climate` | yes |
| 3 | Media | `mdi:music` | `/tablet/media` | yes |
| 4 | Appliances | `mdi:washing-machine` | `/tablet/appliances` | yes |
| 5 | Outdoor | `mdi:tree` | `/tablet/outdoor` | yes |
| 6 | Security | `mdi:shield` | `/tablet/security` | yes |
| 7 | Energy | `mdi:lightning-bolt` | `/tablet/energy` | yes |
| 8 | Settings | `mdi:cog` | `/tablet/settings` | yes |
| 9 | Doorbell | `mdi:doorbell` | `/tablet/doorbell` | **no** (programmatic) |

The current **Bedroom** tab is dropped. **Kitchen** is intentionally not added (too thin — its lights already live in the Home grid).

### Home tab — "Hub with favorites"

3-column `sections` layout. Column grouping is **logical**, not chronological:

**Column 1 — Status & Security**
- Persons card (Jakub, Sona) + alarm readiness template card (moved from current Home)
- Door + 1F-occupancy chips row (current Home)
- Weather card (current Home)
- Doorbell camera live (moved here from current section 2)
- **NEW: Active-scene chip** — surfaces the living-room scene-system state (Movie / Evening / Off)

**Column 2 — Lights & Actions**
- Lights grid: 9 room tiles + All-Off (current Home)
- Now-playing media card (compact, `mushroom-media-player-card`)
- 3 music quick-play buttons: Discover Weekly, Random Playlist, Last Played (current Home)
- 2 vacuum quick-scripts: Clean Mudroom, Clean Kitchen (current Home)

**Column 3 — Comfort**
- Living Room climate card (current Home — temp/humidity/humidifier stacked with humidity+climate chips)
- Bedroom climate card (current Home — same pattern)
- Compact curtains: Ground Floor group, Bedroom
- **NEW: Active-appliances strip** — washer/dryer running indicators
- **NEW: "Today" card** — active-lights count, today's kWh (balances column height)

**Moved off Home:**
- Full vacuum cards (battery, filter, cleaning history) → Appliances
- Voice music search card → Media
- Full curtains list (Living Room Main, Living Room Left, etc.) → Climate

**Navigation from Home:** each section heading gets `tap_action: navigate` to the matching specialty tab.

### Climate tab

- Full thermostats (`thermostat` card): Living Room, Bedroom, any additional zones
- Humidifier controls (`humidifier` card): Living Room, Bedroom — target RH, mode
- Per-area temperature + humidity grid for all areas (chips card)
- All curtains: Living Room Main, Living Room Left, Bedroom, Ground Floor group
- 24-hour temperature + humidity graphs per zone (history-graph or apex-charts if available)
- Boiler room status summary

### Media tab

- **Section 1: Playback** (isolated for crash resilience — see Risks)
  - `custom:mass-player-card` for Music Assistant — primary playback card
  - Width-constrained (e.g., `column_span: 1` inside a 2-col section) so it doesn't dominate
- **Section 2: Search & Quick-play**
  - `custom:voice-music-search-card` (moved from Home)
  - Full playlist quick-play grid: Discover Weekly, Random Playlist, Last Played, plus any additions
- **Section 3: Scenes**
  - Living-room scene system: current scene indicator
  - Aqara Cube reference / help text

### Appliances tab

- **Vacuums section** — 3 vacuums (Dreame L10 Ultra / X40 Master / attic when added)
  - Each: `mushroom-vacuum-card` + chips (battery %, filter %, cleaning history)
  - Per-room clean scripts grid (Mudroom, Kitchen, + future)
- **Laundry section** — washer + dryer
  - Running-state indicators from `binary_sensor.washer_power` / `binary_sensor.tumble_dryer_power`
  - Power draw, session running time
- **Humidifiers section** (secondary view — primary in Climate)
  - Compact status; tap for full control
- **Maintenance chips** — filter-left % from existing vacuum sensors (`sensor.dreamebot_l10_ultra_filter_left`, etc.). Additional "next service" reminders are out of scope unless a sensor already exists.

### Outdoor tab

- Garden irrigation: mode (auto/eco/off), zones, schedule, soil sensors
- Pergola roof: position, weather mode (from existing `input_select.pergola_weather_mode`)
- Gate: state + open/close
- Porch lights
- Terrace lights + door sensors
- Multi-day weather forecast

### Security tab

- Full Satel alarm control panel (arm modes)
- 4 door zones + 3 motion zones — status grid
- Doorbell camera (large)
- Recent activity log — last 24h of sensor events
- Garage door switchable output
- Alarm history — last armed / disarmed / triggered timestamps

### Energy tab

Content migrated from the retired `dashboards/energy.yaml`, plus additions:

- Monthly energy by device — `statistics-graph`, bar chart, period `month`, stat `change`
- Weekly energy by device — same, period `week`
- Cumulative totals — `entities` card
- **NEW: Live power strip** — top 5 consumers right now (requires live power entities — if absent, drop or use power-meter sensors that do exist)
- **NEW: Today's usage sparkline** — single-day rolling (uses existing energy sensors)

All existing entity references (`sensor.sypialnia_lazienka_energy`, etc.) preserved.

### Settings tab

- Christmas mode toggle (existing)
- Pergola weather mode select (existing)
- Manual override toggles (hall, etc.)
- Humidification schedule flags (`input_boolean.living_room_humidification_active`, etc.)
- Living-room scene-system manual override
- Diagnostic chips where entities already exist (e.g. `sensor.last_boot`). No new diagnostic integrations added as part of this redesign.

### Doorbell tab (hidden)

- Unchanged content: panel-layout `picture-entity` of `camera.doorbell_rtsp`
- File relocation only: `dashboards/tablet/doorbell.yaml`
- Still triggered programmatically when doorbell rings (existing automation path)

## Phone dashboard

4 tabs, single-column layout, finger-friendly targets (≥ 48px).

### Home tab

- Persons + alarm state (compact)
- Chip row: All Lights Off · Arm · Pause media
- Active-scene chip
- Weather (compact)
- Now-playing (compact `mushroom-media-player-card`)
- Active lights list (count + drill)
- Active appliances strip

### Rooms tab

- Tiled room picker grouped by floor:
  - Ground Floor: Living Room · Kitchen · Toilet · Vestibule
  - First Floor: Bedroom · Bathroom · Hall · Laundry
  - Outdoor: Garden · Terrace · Porch · Gate · Garage
- Each tile = room summary (temp, lights-on count, main action)
- Tap tile → drill into per-room sub-view (HA sub-view pattern inside `phone.yaml`, not separate dashboard)

### Away tab

"When you're out" focus:

- Alarm panel — arm/disarm + modes
- Doorbell camera (large)
- All door sensors status
- Motion zones status
- Gate open/close
- Presence (who's home)
- Recent alarm events

### Energy tab

- Today's total kWh (large number)
- Today's sparkline
- Top 5 live consumers right now
- This week vs last week (compact)
- Monthly trend (compact bar)

### What's intentionally absent on phone

- Settings tab — configure from the tablet or full HA UI
- Appliances full tab — present as a strip in Home; full control via tablet
- Media full tab — now-playing compact only; full media experience on tablet

## Visual conventions

- **Primary cards:** Mushroom family (`mushroom-template-card`, `mushroom-chips-card`, `mushroom-light-card`, `mushroom-media-player-card`, `mushroom-cover-card`, `mushroom-vacuum-card`, `mushroom-entity-card`)
- **Styling:** `card-mod` for inline tweaks. Stacked-card pattern (rounded-top + flat-bottom) as used in current LR/BR climate cards.
- **Section headings:** `type: heading, heading_style: subtitle` for each logical group within a tab
- **Separators:** `markdown "---"` blocks with the existing card-mod "invisible divider" pattern
- **Tap / hold actions:**
  - `tap_action: more-info` for inspect/detail
  - `hold_action: more-info` with a related entity (e.g., climate card holds → humidifier)
  - `tap_action: navigate` on Home section headings to drill into matching specialty tab
- **Colour palette:** existing Mushroom semantic colours (`green`, `red`, `blue`, `orange`, `cyan`, `purple`, `disabled`). No custom theme change.
- **Column counts:** Home = 3, specialty tabs = 2–3 based on content, phone = 1
- **Tab icons:** per the tab list above

## Shared templates

The current Home alarm card duplicates the same door/presence Jinja **5 times** (icon / icon_color / primary attributes, plus 2 chips). Extract into a single template sensor under `packages/bootstrap/templates/` (or similar):

- `binary_sensor.home_ready_to_arm` (bool)
- `sensor.home_open_doors_count` (int)
- `sensor.home_occupied_zones_count` (int)

Cards then just read these states → shorter YAML, faster render, single source of truth.

## Build sequence

Each step is one PR against `main`, small and reviewable. Branch from `chore/dashboard-redesign` or a fresh branch per PR.

1. **Scaffold** — create `dashboards/tablet/` + `dashboards/mobile-phone/` dirs; move current Home into `tablet/home.yaml` via `!include`; drop Bedroom tab; keep Settings + Doorbell as-is (relocated)
2. **Template consolidation** — extract the duplicated alarm-readiness Jinja into template sensors
3. **Tablet: Appliances tab** — highest value; future-proofs attic vacuum
4. **Tablet: Climate tab** — moves curtains + full humidifier detail off Home
5. **Tablet: Media tab** — moves voice search off Home; adds mass-player-card and scene-system help
6. **Tablet: Outdoor tab** — surfaces garden irrigation + pergola that have no dashboard home today
7. **Tablet: Security tab** — full alarm + zones
8. **Tablet: Energy tab** — migrate content from `dashboards/energy.yaml`, delete old file
9. **Tablet: Home tab rebalance** — add active-scene chip, active-appliances strip, "Today" card; verify column heights on real tablet; wire up `tap_action: navigate` on section headings
10. **Phone: registration + Home + Away** — highest-value phone tabs
11. **Phone: Rooms + sub-views**
12. **Phone: Energy**
13. **Polish pass** — card-mod tweaks, real-device verification, any needed area README updates

Each PR checks in via pre-commit (yamllint) and CI (HA config check). Deploy by pushing — HA auto-pulls the current branch (per CLAUDE.md).

## Risks & mitigations

- **`mass-player-card` crashes** — previously took down entire sections when Music Assistant Queue Actions was missing. Mitigation: keep it in its own isolated section on the Media tab so any future crash is contained; constrain width to prevent sizing issues that caused its prior removal.
- **Column height imbalance on Home** — initial mockup estimates uneven heights. Accepted: we'll fine-tune during step 9 once we can see real tablet heights. Logical grouping takes priority over pixel-perfect balance.
- **Sub-view rooms on phone** — HA's sub-view pattern works within a single dashboard; verify navigation paths work on mobile during step 11.
- **Energy dashboard migration** — any users with bookmarks to `/energy/energy` would break. Low risk (single-user household) but note the URL change to `/tablet/energy`.
- **Touch vs hold ambiguity** — hold actions not always discoverable. Keep hold actions as enhancements, not the only path to a control.

## Success criteria

- All 8 visible tablet tabs + hidden Doorbell load without errors on the wall tablet
- All 4 phone tabs load without errors on a phone device
- Pre-commit and CI pass green
- Adding a hypothetical new appliance requires editing only `tablet/appliances.yaml` (+ optionally `phone/home.yaml`)
- No regressions on existing automations triggered by dashboard state (e.g. Doorbell programmatic navigation)
- Home view remains "awesome" per the user's judgement after the rebalance step

## Open decisions deferred to implementation

- Exact card for the "Today" balance card on Home column 3 — decide between a mushroom-template with template-derived text vs a compact sparkline
- Whether to merge humidifier controls into Climate or keep dual-tab presence (Climate primary, Appliances secondary)
- Exact sub-view structure for phone Rooms tab — flat sub-views vs nested
