# Flight Tracker Dashboard — Flights Viewer Redesign

## Overview

Redesign the standalone flight tracker dashboard (`scripts/flight_tracker/data/dashboard.html`) from a single-page layout into a two-tab application. The existing analytics sections remain on an "Analytics" tab. A new "Flights" tab replaces the current basic "Recent Flights" table with a comprehensive, richly featured flight viewer.

The data pipeline (`flight_tracker.py`, `fr24_client.py`) is enriched to capture additional fields from FR24. Three static JSON lookup files provide human-readable names for airlines, aircraft, and airports.

## Architecture

### Tab Structure

Single-page app with two tabs:

- **Analytics** (default) — all existing content: stats cards, noise-by-hour bar chart, weekly noise heatmap, quietest garden windows, top routes, noisiest time
- **Flights** — new rich flight viewer (replaces the removed "Recent Flights" table)

Tab behavior:

- URL hash routing (`#analytics`, `#flights`) — tab state survives page refresh
- Last-selected tab persisted in `localStorage`
- Each tab has its own independent filter bar immediately below the tab strip
- No shared global filters — tabs are fully self-contained

### File Structure

```text
scripts/flight_tracker/
├── data/
│   ├── flights.csv              # enriched with new columns
│   ├── dashboard.html           # redesigned two-tab app
│   ├── airlines.json            # ICAO → airline name + IATA
│   ├── aircraft.json            # ICAO type → full aircraft name
│   └── airports.json            # IATA → airport name + city + country
├── flight_tracker.py            # updated CSV_COLUMNS
├── fr24_client.py               # updated to capture new fields
└── ...
```

## Pipeline Enrichment

### New CSV Columns

Added to the existing columns (`date`, `time_utc`, `time_local`, `callsign`, `altitude_ft`, `heading_deg`, `origin`, `destination`, `distance_from_home_km`):

| Column | FR24 Source | Example | Notes |
|---|---|---|---|
| `aircraft_type` | `f.aircraft_code` | `A320`, `B738` | ICAO type designator |
| `airline_icao` | `f.airline_icao` | `LOT`, `RYR`, `SAS` | ICAO airline code |
| `airline_iata` | `f.airline_iata` | `LO`, `FR`, `SK` | IATA airline code |
| `registration` | `f.registration` | `SP-LWG`, `9H-LMG` | Aircraft registration |
| `flight_number` | `f.number` | `LO3825`, `FR6065` | Commercial flight number |
| `velocity_kts` | `f.ground_speed` | `280` | Ground speed in knots (raw from FR24, no conversion needed) |
| `vertical_speed_fpm` | `f.vertical_speed` | `1472`, `-640` | Feet per minute, positive=climbing |

### Changes to `fr24_client.py`

`fetch_live_flights()` adds the new fields to each row:

```python
rows.append({
    # ... existing fields ...
    "aircraft_type": f.aircraft_code or "",
    "airline_icao": f.airline_icao or "",
    "airline_iata": f.airline_iata or "",
    "registration": f.registration or "",
    "flight_number": f.number or "",
    "velocity_kts": f.ground_speed if f.ground_speed else None,
    "vertical_speed_fpm": f.vertical_speed if f.vertical_speed else None,
})
```

### Changes to `flight_tracker.py`

- `CSV_COLUMNS` extended with the 7 new column names
- `_format_and_append()` passes through the new fields from the flights DataFrame
- `velocity_kts` stored as integer (already in knots from FR24 — no conversion)
- `vertical_speed_fpm` stored as integer (already in fpm from FR24)

### Backward Compatibility

- Old CSV rows will have empty/NaN values for the new columns when the updated code first reads the existing file
- `pd.concat` handles missing columns by filling with NaN
- Dashboard treats missing values as absent — displays "—" or hides the field
- OpenSky-sourced flights will also have empty values for enrichment fields (OpenSky doesn't provide them)

## Analytics Tab

Unchanged from current dashboard. Retains its own filter bar:

- **Period:** All time, last 7/14/30 days
- **Day type:** All days, weekdays only, weekends only
- **Altitude weight slider:** Exponent 0.5–3.0 for noise calculation

All existing chart sections remain as-is: stats cards, noise by hour, weekly heatmap, quiet windows, top routes, noisiest time.

## Flights Tab

### Filter Bar

Positioned directly below the tab strip. All filters combine with AND logic. Table updates in real-time as filters change.

| Filter | Control | Details |
|---|---|---|
| Search | Text input | Full-text search across callsign, flight number, route, registration, aircraft type, airline |
| Route | Dropdown with autocomplete | Populated from data. Shows "WAW → CPH (Copenhagen)" format using airport lookup. Can filter by origin, destination, or pair |
| Airline | Dropdown | Populated from `airline_icao` values in data, shows airline name from lookup |
| Altitude range | Dual-handle slider | Min/max altitude in feet |
| Time of day | Dual-handle slider | Hour range (e.g., 06:00–22:00) |
| Date range | Date pickers | From/to date |
| Day type | Toggle buttons | All / Weekdays / Weekends |

Layout: Single row, compact. Search field on the left (widest), dropdowns and sliders inline. Collapses to a "Filters" toggle button on narrow viewports.

Active filter indicators: Small pills/badges showing each active filter with × to clear. "Clear all" link when any filter is active.

Result count: "Showing X of Y flights" displayed at the right end of the filter bar.

### Table Columns

| Column | Content | Sortable | Visual Treatment |
|---|---|---|---|
| Date | `date` | Yes | Muted text (#94a3b8) |
| Time | `time_local` | Yes | White text |
| Flight | `flight_number` + `callsign` | Yes (by callsign) | Airline ICAO badge (colored pill) + flight number bold + callsign as secondary small text |
| Route | `origin` → `destination` | Yes | IATA codes with tooltip showing full airport name on hover |
| Aircraft | `aircraft_type` + `registration` | Yes (by type) | Type code on top, registration as secondary small text |
| Alt | `altitude_ft` | Yes | Color-coded badge: red (<4,000 ft), yellow (4,000–6,000 ft), green (>6,000 ft) |
| Dir | `heading_deg` | No | Arrow (↑) rotated by heading degrees, blue color |
| Dist | `distance_from_home_km` | Yes | Plain text with "km" unit |
| Noise | calculated | Yes | Mini progress bar (colored red/yellow/green) + numeric score |

### Sorting

- Click any sortable column header to sort ascending; click again for descending
- Sort indicator (↑/↓) shown on active sort column
- Default sort: Date descending, then Time descending (newest first)

### Pagination

- 25 flights per page
- Prev/Next buttons + page number indicators
- "Showing X–Y of Z flights" counter

### Row Expansion

Click any row to expand a detail panel below it. Click again to collapse. Only one row expanded at a time.

#### Expanded Detail — Left Side: Metadata Grid

Two-column grid with all available fields:

- Callsign, Flight Number
- Airline (full name from lookup + IATA/ICAO codes)
- Aircraft (full name from lookup + type code)
- Registration, ICAO24
- Speed (velocity in knots), Vertical Speed (fpm, colored: green ↑ climbing, red ↓ descending, gray — level)
- Time UTC, Time Local

#### Expanded Detail — Right Side: Mini Visualizations

Two small visualizations side by side:

1. **Position map** (160×120px): Schematic view showing home position (amber dot) with 1km radius circle (dashed), flight position (blue plane icon) relative to home. Distance label in corner.

2. **Altitude gauge** (80×120px): Vertical bar gauge with 0–40,000 ft scale. Filled portion colored by altitude threshold (red/yellow/green). Current altitude value labeled.

## Static Lookup Files

Three JSON files loaded once at dashboard startup, used for display enrichment only.

### `airlines.json`

~500 entries covering airlines operating in European airspace.

```json
{
  "LOT": { "name": "LOT Polish Airlines", "iata": "LO" },
  "RYR": { "name": "Ryanair", "iata": "FR" },
  "SAS": { "name": "Scandinavian Airlines", "iata": "SK" }
}
```

Keyed by ICAO airline code. Fallback: display raw ICAO code if not found.

### `aircraft.json`

~200 entries covering common commercial and general aviation types.

```json
{
  "A320": "Airbus A320",
  "B738": "Boeing 737-800",
  "E195": "Embraer E195",
  "C172": "Cessna 172 Skyhawk"
}
```

Keyed by ICAO type designator. Fallback: display raw type code.

### `airports.json`

~500 entries covering airports with European traffic.

```json
{
  "WAW": { "name": "Warsaw Chopin Airport", "city": "Warsaw", "country": "Poland" },
  "CPH": { "name": "Copenhagen Airport", "city": "Copenhagen", "country": "Denmark" },
  "GDN": { "name": "Gdańsk Lech Wałęsa Airport", "city": "Gdańsk", "country": "Poland" }
}
```

Keyed by IATA code. Used in:

- Table route column: tooltip on hover
- Expanded detail: full route display "Warsaw Chopin (WAW) → Copenhagen (CPH)"
- Route filter dropdown: "WAW → CPH (Copenhagen)" format

Fallback: display raw IATA code.

### Data Sources

These are curated subsets of well-known public datasets:

- Airlines: ICAO airline designator list
- Aircraft: ICAO Doc 8643 type designators
- Airports: IATA airport code directory

Generated once as static files, committed to the repo, updated manually as needed.

## Visual Design System

### Color Palette

Matches existing dashboard dark theme:

- Background: `#0f172a` (deepest), `#1e293b` (cards/panels), `#334155` (borders)
- Text: `#e2e8f0` (primary), `#94a3b8` (secondary), `#64748b` (muted)
- Accent: `#3b82f6` (blue, interactive elements)

### Altitude/Noise Color Scale

| Range | Background | Text | Use |
|---|---|---|---|
| < 4,000 ft (loud) | `#7f1d1d` | `#fca5a5` | Altitude badge, noise bar |
| 4,000–6,000 ft (moderate) | `#713f12` | `#fde68a` | Altitude badge, noise bar |
| > 6,000 ft (quiet) | `#14532d` | `#86efac` | Altitude badge, noise bar |

### Airline Badge Colors

Assigned per airline using a deterministic hash of the ICAO code mapped to a fixed palette. Same airline always gets the same color across sessions.

### Direction Arrow

Up arrow (↑) character rotated by CSS `transform: rotate(Xdeg)` using `heading_deg`. Fixed blue color (`#60a5fa`) for visibility.

### Vertical Speed Indicators

- Climbing (positive): green `#22c55e` with ↑
- Descending (negative): red `#ef4444` with ↓
- Level (zero/near-zero): gray `#64748b` with —

## Noise Score Formula

Unchanged from current dashboard:

```text
noise_score = 1 / (altitude_ft / 1000) ^ exponent
```

Default exponent: 1.5. On the Flights tab, the exponent is fixed at the default (no slider — that's an Analytics concern). The noise score is calculated client-side from `altitude_ft`.

## Responsive Behavior

- Filter bar collapses to a "Filters" toggle button on viewports narrower than 768px
- Table horizontally scrolls on narrow viewports
- Expanded detail panel stacks vertically (metadata above, visualizations below) on narrow viewports
- Pagination remains fixed at bottom of table

## Out of Scope

- Real-time/live updates (data refreshes on page reload, same as current)
- Map view of all flights (only mini position map in expanded rows)
- Integration with Home Assistant (remains standalone dashboard)
- Changes to the data collection schedule or cron setup
- Changes to the OpenSky pipeline (enrichment is FR24-only)
