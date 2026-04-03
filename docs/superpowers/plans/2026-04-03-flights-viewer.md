# Flights Viewer Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the flight tracker dashboard into a two-tab app with a rich flights viewer, and enrich the data pipeline with additional FR24 fields.

**Architecture:** Pipeline enrichment (7 new CSV columns from FR24) + dashboard rewrite as two-tab SPA (Analytics keeps existing charts, Flights gets rich sortable/filterable table with expandable detail rows). Three static JSON lookup files for airlines, aircraft, and airports.

**Tech Stack:** Python/pandas (pipeline), vanilla HTML/CSS/JS (dashboard), Chart.js (existing charts)

**Spec:** `docs/superpowers/specs/2026-04-03-flights-viewer-design.md`

---

## Tasks

### Task 1: Enrich FR24 Client with New Fields

**Files:**

- Modify: `scripts/flight_tracker/fr24_client.py:41-58`
- Test: `scripts/flight_tracker/tests/test_fr24_live.py` (create)

- [ ] **Step 1: Write the failing test**

Create `scripts/flight_tracker/tests/test_fr24_live.py`:

```python
import pandas as pd
from unittest.mock import MagicMock, patch


def _make_mock_flight(**overrides):
    """Create a mock FR24 Flight object with default values."""
    defaults = {
        "icao_24bit": "4B1812",
        "callsign": "LOT3825",
        "latitude": 52.247,
        "longitude": 20.836,
        "altitude": 4875,
        "heading": 318,
        "ground_speed": 280,
        "on_ground": 0,
        "origin_airport_iata": "WAW",
        "destination_airport_iata": "GDN",
        "aircraft_code": "B738",
        "airline_icao": "LOT",
        "airline_iata": "LO",
        "registration": "SP-LWG",
        "number": "LO3825",
        "vertical_speed": 1472,
    }
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


def test_fetch_live_flights_includes_enrichment_fields():
    """fetch_live_flights returns new enrichment columns."""
    mock_flight = _make_mock_flight()

    with patch("fr24_client.FlightRadar24API") as MockAPI:
        MockAPI.return_value.get_flights.return_value = [mock_flight]
        from fr24_client import fetch_live_flights

        df = fetch_live_flights(52.0, 52.5, 20.5, 21.0)

    assert len(df) == 1
    row = df.iloc[0]
    assert row["aircraft_type"] == "B738"
    assert row["airline_icao"] == "LOT"
    assert row["airline_iata"] == "LO"
    assert row["registration"] == "SP-LWG"
    assert row["flight_number"] == "LO3825"
    assert row["velocity_kts"] == 280
    assert row["vertical_speed_fpm"] == 1472


def test_fetch_live_flights_handles_missing_enrichment_fields():
    """Missing enrichment fields default to empty string or None."""
    mock_flight = _make_mock_flight(
        aircraft_code="",
        airline_icao="",
        airline_iata="",
        registration="",
        number="",
        ground_speed=0,
        vertical_speed=0,
    )

    with patch("fr24_client.FlightRadar24API") as MockAPI:
        MockAPI.return_value.get_flights.return_value = [mock_flight]
        from fr24_client import fetch_live_flights

        df = fetch_live_flights(52.0, 52.5, 20.5, 21.0)

    assert len(df) == 1
    row = df.iloc[0]
    assert row["aircraft_type"] == ""
    assert row["airline_icao"] == ""
    assert row["registration"] == ""
    assert row["flight_number"] == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd scripts/flight_tracker && uv run pytest tests/test_fr24_live.py -v`
Expected: FAIL — `KeyError: 'aircraft_type'` (columns don't exist yet)

- [ ] **Step 3: Implement the enrichment in fr24_client.py**

In `scripts/flight_tracker/fr24_client.py`, update the `rows.append()` call inside `fetch_live_flights()` and the empty DataFrame columns:

```python
def fetch_live_flights(
    lat_min: float,
    lat_max: float,
    lon_min: float,
    lon_max: float,
) -> pd.DataFrame:
    """Fetch currently visible flights from FlightRadar24 within a bounding box.

    Returns a DataFrame with columns matching the OpenSky format:
    icao24, callsign, time, lat, lon, baroaltitude, heading, velocity,
    plus origin, destination, and enrichment fields (aircraft_type,
    airline_icao, airline_iata, registration, flight_number,
    velocity_kts, vertical_speed_fpm).
    """
    from FlightRadar24 import FlightRadar24API

    api = FlightRadar24API()
    bounds = f"{lat_max},{lat_min},{lon_min},{lon_max}"

    logger.info("Querying FR24 for flights in bounds: %s", bounds)
    flights = api.get_flights(bounds=bounds)

    if not flights:
        logger.info("No flights found in bounding box.")
        return pd.DataFrame(
            columns=[
                "icao24", "callsign", "time", "lat", "lon",
                "baroaltitude", "heading", "velocity", "origin", "destination",
                "aircraft_type", "airline_icao", "airline_iata",
                "registration", "flight_number", "velocity_kts",
                "vertical_speed_fpm",
            ]
        )

    rows = []
    now = int(time.time())
    for f in flights:
        # Skip ground vehicles and flights on the ground
        if f.on_ground:
            continue
        rows.append({
            "icao24": f.icao_24bit or "",
            "callsign": f.callsign or "",
            "time": now,
            "lat": f.latitude,
            "lon": f.longitude,
            "baroaltitude": f.altitude * 0.3048 if f.altitude else None,  # ft -> meters for consistency
            "heading": f.heading,
            "velocity": f.ground_speed * 0.514444 if f.ground_speed else None,  # knots -> m/s
            "origin": f.origin_airport_iata or "",
            "destination": f.destination_airport_iata or "",
            "aircraft_type": f.aircraft_code or "",
            "airline_icao": f.airline_icao or "",
            "airline_iata": f.airline_iata or "",
            "registration": f.registration or "",
            "flight_number": f.number or "",
            "velocity_kts": f.ground_speed if f.ground_speed else None,
            "vertical_speed_fpm": f.vertical_speed if f.vertical_speed else None,
        })

    logger.info("Found %d airborne flights in bounding box.", len(rows))
    return pd.DataFrame(rows)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd scripts/flight_tracker && uv run pytest tests/test_fr24_live.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Run all existing tests to check for regressions**

Run: `cd scripts/flight_tracker && uv run pytest tests/ -v`
Expected: All 5 tests PASS (3 processing + 2 cache + 2 new fr24_live, but cache tests mock the API so the extra columns don't affect them)

- [ ] **Step 6: Commit**

```bash
git add scripts/flight_tracker/fr24_client.py scripts/flight_tracker/tests/test_fr24_live.py
git commit -m "feat(flight-tracker): enrich FR24 live flights with aircraft/airline/registration fields"
```

---

### Task 2: Update Pipeline to Write Enrichment Columns to CSV

**Files:**

- Modify: `scripts/flight_tracker/flight_tracker.py:34-44,56-74`
- Test: `scripts/flight_tracker/tests/test_pipeline.py` (create)

- [ ] **Step 1: Write the failing test**

Create `scripts/flight_tracker/tests/test_pipeline.py`:

```python
import pandas as pd
from pathlib import Path
from flight_tracker import _format_and_append, CSV_COLUMNS, CSV_PATH


def test_csv_columns_include_enrichment_fields():
    """CSV_COLUMNS list includes all 7 new enrichment columns."""
    expected_new = [
        "aircraft_type", "airline_icao", "airline_iata",
        "registration", "flight_number", "velocity_kts",
        "vertical_speed_fpm",
    ]
    for col in expected_new:
        assert col in CSV_COLUMNS, f"Missing column: {col}"


def test_format_and_append_writes_enrichment_columns(tmp_path, monkeypatch):
    """_format_and_append includes enrichment columns in output CSV."""
    csv_path = tmp_path / "flights.csv"
    monkeypatch.setattr("flight_tracker.CSV_PATH", csv_path)
    monkeypatch.setattr("flight_tracker.DATA_DIR", tmp_path)

    flights = pd.DataFrame([{
        "icao24": "4B1812",
        "callsign": "LOT3825",
        "time": 1712170000,
        "lat": 52.247,
        "lon": 20.836,
        "baroaltitude": 1485.9,  # ~4875 ft
        "heading": 318.0,
        "velocity": 143.0,
        "origin": "WAW",
        "destination": "GDN",
        "aircraft_type": "B738",
        "airline_icao": "LOT",
        "airline_iata": "LO",
        "registration": "SP-LWG",
        "flight_number": "LO3825",
        "velocity_kts": 280,
        "vertical_speed_fpm": 1472,
    }])

    count = _format_and_append(flights)
    assert count == 1

    result = pd.read_csv(csv_path)
    assert result.iloc[0]["aircraft_type"] == "B738"
    assert result.iloc[0]["airline_icao"] == "LOT"
    assert result.iloc[0]["airline_iata"] == "LO"
    assert result.iloc[0]["registration"] == "SP-LWG"
    assert result.iloc[0]["flight_number"] == "LO3825"
    assert result.iloc[0]["velocity_kts"] == 280
    assert result.iloc[0]["vertical_speed_fpm"] == 1472


def test_format_and_append_handles_missing_enrichment(tmp_path, monkeypatch):
    """Old-style flights without enrichment columns get NaN/empty values."""
    csv_path = tmp_path / "flights.csv"
    monkeypatch.setattr("flight_tracker.CSV_PATH", csv_path)
    monkeypatch.setattr("flight_tracker.DATA_DIR", tmp_path)

    flights = pd.DataFrame([{
        "icao24": "4B1812",
        "callsign": "LOT3825",
        "time": 1712170000,
        "lat": 52.247,
        "lon": 20.836,
        "baroaltitude": 1485.9,
        "heading": 318.0,
        "velocity": 143.0,
        "origin": "WAW",
        "destination": "GDN",
        # No enrichment fields — simulates OpenSky source
    }])

    count = _format_and_append(flights)
    assert count == 1

    result = pd.read_csv(csv_path)
    assert len(result) == 1
    # Enrichment columns should exist but be empty/NaN
    assert pd.isna(result.iloc[0]["aircraft_type"]) or result.iloc[0]["aircraft_type"] == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd scripts/flight_tracker && uv run pytest tests/test_pipeline.py -v`
Expected: FAIL — `aircraft_type` not in CSV_COLUMNS

- [ ] **Step 3: Update flight_tracker.py**

In `scripts/flight_tracker/flight_tracker.py`:

Update `CSV_COLUMNS`:

```python
CSV_COLUMNS = [
    "date",
    "time_utc",
    "time_local",
    "callsign",
    "altitude_ft",
    "heading_deg",
    "origin",
    "destination",
    "distance_from_home_km",
    "aircraft_type",
    "airline_icao",
    "airline_iata",
    "registration",
    "flight_number",
    "velocity_kts",
    "vertical_speed_fpm",
]
```

Update `_format_and_append()` — add the new column pass-throughs after `output["distance_from_home_km"]`:

```python
    output["aircraft_type"] = flights["aircraft_type"] if "aircraft_type" in flights.columns else ""
    output["airline_icao"] = flights["airline_icao"] if "airline_icao" in flights.columns else ""
    output["airline_iata"] = flights["airline_iata"] if "airline_iata" in flights.columns else ""
    output["registration"] = flights["registration"] if "registration" in flights.columns else ""
    output["flight_number"] = flights["flight_number"] if "flight_number" in flights.columns else ""
    output["velocity_kts"] = flights["velocity_kts"].round(0).astype("Int64") if "velocity_kts" in flights.columns else pd.NA
    output["vertical_speed_fpm"] = flights["vertical_speed_fpm"].round(0).astype("Int64") if "vertical_speed_fpm" in flights.columns else pd.NA
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd scripts/flight_tracker && uv run pytest tests/test_pipeline.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Run all tests**

Run: `cd scripts/flight_tracker && uv run pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add scripts/flight_tracker/flight_tracker.py scripts/flight_tracker/tests/test_pipeline.py
git commit -m "feat(flight-tracker): write enrichment columns to CSV"
```

---

### Task 3: Generate Static Lookup Files (Airlines, Aircraft, Airports)

**Files:**

- Create: `scripts/flight_tracker/data/airlines.json`
- Create: `scripts/flight_tracker/data/aircraft.json`
- Create: `scripts/flight_tracker/data/airports.json`

- [ ] **Step 1: Create airlines.json**

Create `scripts/flight_tracker/data/airlines.json` with ~100 airlines operating in European airspace. Key = ICAO code. Value = `{ "name": "...", "iata": "..." }`.

Must include at minimum these airlines seen in the flight data: LOT, RYR (Ryanair, IATA=FR), SAS, FIN (Finnair, IATA=AY), WZZ (Wizz Air, IATA=W6), DLH (Lufthansa, IATA=LH), BAW (British Airways, IATA=BA), AFR (Air France, IATA=AF), KLM (KLM, IATA=KL), SWR (Swiss, IATA=LX), AUA (Austrian, IATA=OS), TAP (TAP Portugal, IATA=TP), IBE (Iberia, IATA=IB), SAS (SAS, IATA=SK), EWG (Eurowings, IATA=EW), NLY (Norwegian Air Sweden, IATA=D8), NAX (Norwegian, IATA=DY), EZY (easyJet, IATA=U2), VLG (Vueling, IATA=VY), THY (Turkish Airlines, IATA=TK), UAE (Emirates, IATA=EK), ETH (Ethiopian, IATA=ET), QTR (Qatar Airways, IATA=QR), ELY (El Al, IATA=LY), BEL (Brussels Airlines, IATA=SN), AZA (ITA Airways, IATA=AZ), BMS (Blue Air, IATA=0B), TVS (Travel Service, IATA=QS), LDA (Ryanair Sun/Malta Air, IATA=FR).

Generate a comprehensive list — at least 100 entries. Use web search to get accurate ICAO→name→IATA mappings.

- [ ] **Step 2: Create aircraft.json**

Create `scripts/flight_tracker/data/aircraft.json` with ~150 common aircraft types. Key = ICAO type designator. Value = full name string.

Must include at minimum: A220, A319, A320, A321, A332, A333, A339, A343, A359, A388, AT72, AT76, B737, B738, B739, B38M, B39M, B744, B748, B752, B763, B772, B773, B77L, B77W, B788, B789, B78X, C172, C208, C25A, C25B, C500, C510, C525, C550, C560, C56X, C680, C750, CL35, CL60, CRUZ, CRJ2, CRJ7, CRJ9, CRJX, DA42, DH8D, E170, E175, E190, E195, E290, E295, E35L, E45X, E545, E550, E55P, F2TH, F900, FA7X, FA8X, G280, GL5T, GL7T, GLEX, GLF5, GLF6, GRND, H25B, H25C, LJ45, LJ60, LJ75, MD11, P180, PC12, PC24, RJ85, SF34, SR22.

- [ ] **Step 3: Create airports.json**

Create `scripts/flight_tracker/data/airports.json` with ~200 airports with European traffic. Key = IATA code. Value = `{ "name": "...", "city": "...", "country": "..." }`.

Must include at minimum airports seen in the data: WAW, CPH, GDN, GOT, HEL, ARN, TLL, VNO, RIX, BZG, NYO, BLL, VIE. Plus major European hubs: LHR, CDG, AMS, FRA, MUC, ZRH, VIE, BCN, MAD, FCO, IST, ATH, LIS, DUB, BRU, OSL, PRG, BUD, OTP, SOF, ZAG, BEG, LJU, TXL/BER, HAM, DUS, STR, CGN, KRK, WRO, KTW, POZ, GDN, LCJ, RZE.

- [ ] **Step 4: Validate JSON files are valid**

Run: `cd scripts/flight_tracker && python -c "import json; [json.load(open(f'data/{f}.json')) for f in ['airlines','aircraft','airports']]; print('All valid')"`

Expected: `All valid`

- [ ] **Step 5: Commit**

```bash
git add scripts/flight_tracker/data/airlines.json scripts/flight_tracker/data/aircraft.json scripts/flight_tracker/data/airports.json
git commit -m "feat(flight-tracker): add static lookup files for airlines, aircraft, airports"
```

---

### Task 4: Dashboard Rewrite — Tab Shell and Analytics Tab

Rewrite `dashboard.html` as a two-tab SPA. This task creates the tab navigation and moves all existing content into the Analytics tab, unchanged.

**Files:**

- Modify: `scripts/flight_tracker/data/dashboard.html` (full rewrite)

- [ ] **Step 1: Rewrite dashboard.html with tab structure**

Replace the entire contents of `scripts/flight_tracker/data/dashboard.html`. The new structure:

1. Same `<head>` with Chart.js CDN, updated `<style>` block adding tab styles
2. Tab navigation bar: two tabs — "Analytics" and "Flights"
3. `<div id="tab-analytics">` — contains the existing filter bar and `<div id="app">` (all existing analytics code)
4. `<div id="tab-flights">` — empty placeholder for now (just "Coming soon")
5. Tab switching JS: hash routing (`#analytics`, `#flights`), localStorage persistence, show/hide tab panels
6. All existing JS (loadCSV, filterData, noiseScore, computeStats, render, main) moved inside the analytics tab scope — unchanged logic

Key implementation details:

- Tab strip: `<div class="tab-bar">` with `<button class="tab active" data-tab="analytics">Analytics</button>` and `<button class="tab" data-tab="flights">Flights</button>`
- Tab panels: `<div class="tab-panel active" id="tab-analytics">` and `<div class="tab-panel" id="tab-flights">`
- CSS: `.tab-panel { display: none; }` `.tab-panel.active { display: block; }`
- Tab switching function reads `location.hash`, updates `.active` class on both tab buttons and panels, saves to `localStorage`
- On page load: check `location.hash` first, then `localStorage`, default to `#analytics`
- Analytics filter bar moves inside `#tab-analytics`
- Tab bar styles: dark background (`#1e293b`), active tab has blue bottom border (`#3b82f6`), inactive tabs are muted text

The analytics tab content (filter bar + `<div id="app">`) and all JS logic for computing stats and rendering charts must remain **exactly as-is** — same function names, same DOM IDs, same filter bar. The only change is wrapping it in the tab panel div.

- [ ] **Step 2: Verify analytics tab works**

Run: `cd scripts/flight_tracker && python -m http.server 8787 -d data &`
Open: `http://localhost:8787/dashboard.html`
Verify: Analytics tab shows all existing charts (stats, noise by hour, heatmap, quiet windows, top routes, noisiest time, filter bar works). Flights tab shows placeholder.
Kill: `kill %1`

- [ ] **Step 3: Verify tab switching**

- Click "Flights" tab → Flights panel shows, Analytics hides
- Click "Analytics" tab → Analytics panel shows, Flights hides
- Navigate to `#flights` directly → Flights tab active on load
- Refresh page → same tab remains active (localStorage)

- [ ] **Step 4: Commit**

```bash
git add scripts/flight_tracker/data/dashboard.html
git commit -m "feat(flight-tracker): two-tab dashboard shell with analytics tab"
```

---

### Task 5: Flights Tab — Filter Bar

**Files:**

- Modify: `scripts/flight_tracker/data/dashboard.html`

- [ ] **Step 1: Add the flights filter bar HTML and CSS**

Inside `<div id="tab-flights">`, add the filter bar. The filter bar markup:

```html
<div class="flights-filter-bar">
    <input type="text" id="flights-search" placeholder="Search flights..." class="flights-filter-input flights-search-input">
    <select id="flights-route" class="flights-filter-input"><option value="">All routes</option></select>
    <select id="flights-airline" class="flights-filter-input"><option value="">All airlines</option></select>
    <div class="flights-filter-group">
        <label>Alt:</label>
        <input type="range" id="flights-alt-min" min="0" max="40000" step="500" value="0">
        <span>–</span>
        <input type="range" id="flights-alt-max" min="0" max="40000" step="500" value="40000">
        <span id="flights-alt-label" class="flights-filter-label">0 – 40,000 ft</span>
    </div>
    <div class="flights-filter-group">
        <label>Time:</label>
        <input type="range" id="flights-time-min" min="0" max="23" step="1" value="0">
        <span>–</span>
        <input type="range" id="flights-time-max" min="0" max="23" step="1" value="23">
        <span id="flights-time-label" class="flights-filter-label">00:00 – 23:00</span>
    </div>
    <input type="date" id="flights-date-from" class="flights-filter-input">
    <input type="date" id="flights-date-to" class="flights-filter-input">
    <div class="flights-daytype-toggle">
        <button class="flights-daytype-btn active" data-daytype="all">All</button>
        <button class="flights-daytype-btn" data-daytype="weekday">Weekdays</button>
        <button class="flights-daytype-btn" data-daytype="weekend">Weekends</button>
    </div>
    <span id="flights-count" class="flights-filter-count"></span>
</div>
<div id="flights-active-filters"></div>
```

Add CSS for the filter bar:

- `.flights-filter-bar`: flex row, gap 8px, padding 12px 16px, background `#1e293b`, border-bottom, flex-wrap, align-items center
- `.flights-search-input`: flex 1, min-width 180px, max-width 280px
- `.flights-filter-input`: background `#0f172a`, color `#e2e8f0`, border `1px solid #334155`, border-radius 6px, padding 6px 10px, font-size 13px
- `.flights-filter-group`: display flex, align-items center, gap 4px
- `.flights-filter-label`: color `#94a3b8`, font-size 12px
- `.flights-daytype-toggle`: display flex, gap 2px
- `.flights-daytype-btn`: background `#0f172a`, color `#64748b`, border 1px solid `#334155`, border-radius 6px, padding 4px 10px, cursor pointer, font-size 13px
- `.flights-daytype-btn.active`: background `#1e40af`, color `#93c5fd`, border-color `#1e40af`
- `.flights-filter-count`: color `#64748b`, font-size 13px, margin-left auto
- `#flights-active-filters`: display flex, gap 6px, padding 6px 16px (hidden when empty)
- Active filter pill: background `#1e40af`, color `#93c5fd`, padding 2px 8px, border-radius 12px, font-size 11px, cursor pointer

- [ ] **Step 2: Add filter bar JS logic**

Add a `FlightsFilter` class/object in the script section that:

1. Loads the three JSON lookup files (`airlines.json`, `aircraft.json`, `airports.json`) via fetch at startup
2. Populates the route dropdown from unique origin→destination pairs in the data, formatted as `"WAW → CPH (Copenhagen)"` using airport lookup
3. Populates the airline dropdown from unique `airline_icao` values, formatted as `"LOT — LOT Polish Airlines"` using airline lookup
4. On any filter change: applies all filters (AND logic) to the full flights array, calls the table render function (Task 6)
5. Updates the active filter pills in `#flights-active-filters`
6. Updates the count in `#flights-count`

Filter functions:

- **Search:** lowercased includes check against concatenation of: callsign, flight_number, origin, destination, registration, aircraft_type, airline_icao
- **Route:** match on `origin`, `destination`, or `origin,destination` pair
- **Airline:** match on `airline_icao`
- **Altitude range:** `altitude_ft >= min && altitude_ft <= max`
- **Time range:** parse `time_local` hour, check `hour >= min && hour <= max`
- **Date range:** string comparison `date >= from && date <= to`
- **Day type:** same logic as analytics — check day of week from date

Responsive: filter bar gets `@media (max-width: 768px)` that hides filters behind a "Filters" toggle button.

- [ ] **Step 3: Verify filter bar renders and filters work**

Run: `cd scripts/flight_tracker && python -m http.server 8787 -d data &`
Open: `http://localhost:8787/dashboard.html#flights`
Verify: Filter bar renders with all controls. Search, route dropdown, airline dropdown populate from data. Changing filters updates count. Active filter pills appear/disappear.
Kill: `kill %1`

- [ ] **Step 4: Commit**

```bash
git add scripts/flight_tracker/data/dashboard.html
git commit -m "feat(flight-tracker): flights tab filter bar with all controls"
```

---

### Task 6: Flights Tab — Sortable Table with Visual Indicators

**Files:**

- Modify: `scripts/flight_tracker/data/dashboard.html`

- [ ] **Step 1: Add table rendering function**

Add a `renderFlightsTable(flights, lookups)` function that generates the table HTML:

Table columns: Date, Time, Flight, Route, Aircraft, Alt, Dir, Dist, Noise.

Visual indicators (all computed in the render function):

**Altitude badge color:**

```javascript
function altitudeColor(alt) {
    const a = parseFloat(alt);
    if (a < 4000) return { bg: '#7f1d1d', text: '#fca5a5' };
    if (a < 6000) return { bg: '#713f12', text: '#fde68a' };
    return { bg: '#14532d', text: '#86efac' };
}
```

**Noise score and bar:**

```javascript
function flightNoiseScore(alt) {
    const a = parseFloat(alt);
    if (!a || a <= 0) return 0;
    return 1.0 / Math.pow(a / 1000, 1.5);
}

function noiseColor(score) {
    if (score > 0.05) return '#ef4444';
    if (score > 0.03) return '#eab308';
    return '#22c55e';
}
```

**Airline badge:** Deterministic color from ICAO code:

```javascript
function airlineBadgeColor(icao) {
    const PALETTE = [
        { bg: '#1e3a5f', text: '#60a5fa' },
        { bg: '#3b2f1e', text: '#fbbf24' },
        { bg: '#1e3a2f', text: '#4ade80' },
        { bg: '#3b1e3b', text: '#c084fc' },
        { bg: '#1e2d3b', text: '#67e8f9' },
        { bg: '#3b2a1e', text: '#fb923c' },
        { bg: '#2d1e3b', text: '#a78bfa' },
        { bg: '#1e3b2a', text: '#34d399' },
    ];
    let hash = 0;
    for (let i = 0; i < icao.length; i++) hash = ((hash << 5) - hash) + icao.charCodeAt(i);
    return PALETTE[Math.abs(hash) % PALETTE.length];
}
```

**Direction arrow:** `<span style="display:inline-block; transform:rotate(${heading}deg); color:#60a5fa;">↑</span>`

**Route column:** IATA codes with `title` attribute for tooltip: `<span title="${airportName}">${code}</span>`

**Flight column:** Airline badge pill + flight number bold + callsign secondary:

```html
<span class="airline-badge" style="background:${color.bg}; color:${color.text};">${airline_icao}</span>
<div><strong>${flight_number || callsign}</strong></div>
<div class="secondary">${flight_number ? callsign : ''}</div>
```

Table container: `<div id="flights-table-container">` inside `#tab-flights`, below the filter bar.

- [ ] **Step 2: Add sorting logic**

Add a `FlightsSort` object:

```javascript
const flightsSort = {
    column: 'date',
    direction: 'desc',
    secondaryColumn: 'time_local',
    secondaryDirection: 'desc',

    toggle(col) {
        if (this.column === col) {
            this.direction = this.direction === 'asc' ? 'desc' : 'asc';
        } else {
            this.column = col;
            this.direction = 'asc';
        }
        renderCurrentFlights();
    },

    apply(flights) {
        return [...flights].sort((a, b) => {
            let va = a[this.column], vb = b[this.column];
            // Numeric columns
            if (['altitude_ft', 'distance_from_home_km', 'velocity_kts', 'vertical_speed_fpm'].includes(this.column)) {
                va = parseFloat(va) || 0;
                vb = parseFloat(vb) || 0;
            }
            // Noise column (computed)
            if (this.column === 'noise') {
                va = flightNoiseScore(a.altitude_ft);
                vb = flightNoiseScore(b.altitude_ft);
            }
            let cmp = va < vb ? -1 : va > vb ? 1 : 0;
            if (this.direction === 'desc') cmp = -cmp;
            if (cmp !== 0) return cmp;
            // Secondary sort
            let sa = a[this.secondaryColumn], sb = b[this.secondaryColumn];
            let scmp = sa < sb ? -1 : sa > sb ? 1 : 0;
            if (this.secondaryDirection === 'desc') scmp = -scmp;
            return scmp;
        });
    }
};
```

Column headers get `onclick="flightsSort.toggle('column_name')"` and show ↑/↓ indicator on active sort column.

- [ ] **Step 3: Add pagination**

Add a `FlightsPagination` object:

```javascript
const flightsPagination = {
    page: 1,
    perPage: 25,

    paginate(flights) {
        const start = (this.page - 1) * this.perPage;
        return flights.slice(start, start + this.perPage);
    },

    totalPages(totalFlights) {
        return Math.ceil(totalFlights / this.perPage);
    },

    renderControls(totalFlights) {
        const total = this.totalPages(totalFlights);
        const start = (this.page - 1) * this.perPage + 1;
        const end = Math.min(this.page * this.perPage, totalFlights);
        return `
            <div class="flights-pagination">
                <span class="flights-pagination-info">Showing ${start}–${end} of ${totalFlights} flights</span>
                <div class="flights-pagination-controls">
                    <button onclick="flightsPagination.page--; renderCurrentFlights();" ${this.page <= 1 ? 'disabled' : ''}>← Prev</button>
                    <span class="flights-pagination-page">${this.page} / ${total}</span>
                    <button onclick="flightsPagination.page++; renderCurrentFlights();" ${this.page >= total ? 'disabled' : ''}>Next →</button>
                </div>
            </div>
        `;
    }
};
```

Pagination renders below the table. Page resets to 1 when filters change.

- [ ] **Step 4: Wire it all together**

Create a `renderCurrentFlights()` function that:

1. Gets filtered flights from `FlightsFilter`
2. Sorts them via `flightsSort.apply()`
3. Paginates via `flightsPagination.paginate()`
4. Calls `renderFlightsTable()` with the page of flights
5. Appends pagination controls

- [ ] **Step 5: Verify table renders with sample data**

Run: `cd scripts/flight_tracker && python -m http.server 8787 -d data &`
Open: `http://localhost:8787/dashboard.html#flights`
Verify: Table shows flights with airline badges, altitude color badges, direction arrows, noise bars. Click headers to sort. Pagination works. Filters update the table.
Kill: `kill %1`

- [ ] **Step 6: Commit**

```bash
git add scripts/flight_tracker/data/dashboard.html
git commit -m "feat(flight-tracker): flights table with sorting, visual indicators, pagination"
```

---

### Task 7: Flights Tab — Expandable Detail Rows

**Files:**

- Modify: `scripts/flight_tracker/data/dashboard.html`

- [ ] **Step 1: Add expanded row HTML generation**

Add a `renderExpandedRow(flight, lookups)` function that returns `<tr class="expanded-row">` with a `<td colspan="9">` containing:

**Left side — metadata grid:**

```html
<div class="flight-detail-meta">
    <div class="flight-detail-label">Flight Details</div>
    <div class="flight-detail-grid">
        <div><span class="meta-label">Callsign:</span> <span>${flight.callsign}</span></div>
        <div><span class="meta-label">Flight #:</span> <span>${flight.flight_number || '—'}</span></div>
        <div><span class="meta-label">Airline:</span> <span>${airlineName} (${flight.airline_iata || '—'} / ${flight.airline_icao || '—'})</span></div>
        <div><span class="meta-label">Aircraft:</span> <span>${aircraftName} (${flight.aircraft_type || '—'})</span></div>
        <div><span class="meta-label">Registration:</span> <span>${flight.registration || '—'}</span></div>
        <div><span class="meta-label">ICAO24:</span> <span>${flight.icao24 || '—'}</span></div>
        <div><span class="meta-label">Speed:</span> <span>${flight.velocity_kts ? flight.velocity_kts + ' kts' : '—'}</span></div>
        <div><span class="meta-label">Vertical:</span> <span class="${vsClass}">${vsIcon} ${vsText}</span></div>
        <div><span class="meta-label">Time (UTC):</span> <span>${flight.time_utc}</span></div>
        <div><span class="meta-label">Time (Local):</span> <span>${flight.time_local}</span></div>
    </div>
</div>
```

Where:

- `airlineName` = `lookups.airlines[flight.airline_icao]?.name || flight.airline_icao || '—'`
- `aircraftName` = `lookups.aircraft[flight.aircraft_type] || flight.aircraft_type || '—'`
- Vertical speed: `vsClass` = green for positive, red for negative, gray for zero. `vsIcon` = ↑/↓/—. `vsText` = `|value| fpm`

**Right side — mini visualizations:**

**Position map** (160×120px SVG):

- Gray background rect
- Grid crosshair lines (center)
- Dashed circle at center = 1km radius (scaled proportionally)
- Amber dot at center = home position
- Blue plane emoji at flight's relative position (use distance_from_home_km and heading_deg to compute x,y offset from center)
- Distance label in bottom-right corner

```javascript
function renderPositionMap(flight) {
    // Scale: 1km = 30px (so map shows ~2.5km radius view)
    const scale = 30;
    const cx = 80, cy = 60; // center
    const dist = parseFloat(flight.distance_from_home_km) || 0;
    const hdg = parseFloat(flight.heading_deg) || 0;
    // heading_deg is aircraft heading, not position bearing — approximate:
    // place the flight at (dist, heading) from home
    const rad = (hdg - 90) * Math.PI / 180;
    const fx = cx + dist * scale * Math.cos(rad);
    const fy = cy + dist * scale * Math.sin(rad);

    return `
        <svg width="160" height="120" style="background:#1e293b; border-radius:8px; border:1px solid #334155;">
            <line x1="0" y1="${cy}" x2="160" y2="${cy}" stroke="#334155" stroke-width="1"/>
            <line x1="${cx}" y1="0" x2="${cx}" y2="120" stroke="#334155" stroke-width="1"/>
            <circle cx="${cx}" cy="${cy}" r="${scale}" fill="none" stroke="#475569" stroke-dasharray="4,3" stroke-width="1"/>
            <circle cx="${cx}" cy="${cy}" r="4" fill="#f59e0b"/>
            <text x="${fx}" y="${fy}" font-size="14" text-anchor="middle" dominant-baseline="central" fill="#60a5fa">✈</text>
            <text x="150" y="114" font-size="10" text-anchor="end" fill="#64748b">${dist} km</text>
        </svg>
    `;
}
```

**Altitude gauge** (80×120px SVG):

```javascript
function renderAltitudeGauge(flight) {
    const alt = parseFloat(flight.altitude_ft) || 0;
    const maxAlt = 40000;
    const pct = Math.min(alt / maxAlt, 1);
    const barHeight = 90;
    const fillHeight = pct * barHeight;
    const color = altitudeColor(alt);

    return `
        <svg width="80" height="120" style="background:#1e293b; border-radius:8px; border:1px solid #334155;">
            <rect x="15" y="10" width="20" height="${barHeight}" rx="4" fill="#0f172a"/>
            <rect x="15" y="${10 + barHeight - fillHeight}" width="20" height="${fillHeight}" rx="4" fill="${color.text}"/>
            <text x="70" y="16" font-size="9" text-anchor="end" fill="#64748b">40k</text>
            <text x="70" y="${10 + barHeight/2}" font-size="9" text-anchor="end" fill="#64748b">20k</text>
            <text x="70" y="${10 + barHeight - 2}" font-size="9" text-anchor="end" fill="#64748b">0</text>
            <text x="45" y="${10 + barHeight - fillHeight + 14}" font-size="11" text-anchor="start" fill="${color.text}" font-weight="600">${alt.toLocaleString()}</text>
        </svg>
    `;
}
```

- [ ] **Step 2: Add row click expansion logic**

Add CSS for expanded rows:

```css
.expanded-row { background: #0f172a; }
.expanded-row td { padding: 0; }
.flight-detail { display: flex; gap: 24px; padding: 16px 24px; border-left: 3px solid #3b82f6; }
.flight-detail-meta { flex: 1; }
.flight-detail-label { color: #64748b; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
.flight-detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 24px; font-size: 13px; }
.meta-label { color: #64748b; }
.flight-detail-viz { display: flex; gap: 16px; }
.flight-detail-viz-title { color: #64748b; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
@media (max-width: 768px) {
    .flight-detail { flex-direction: column; }
}
```

JS logic for expansion:

- Track `expandedFlightId` (using `callsign + date` as unique ID since we don't have a proper flight ID)
- On row click: if this row is already expanded, collapse it. Otherwise, collapse any previously expanded row, expand this one
- `renderFlightsTable()` checks each row — if it matches `expandedFlightId`, insert the expanded row `<tr>` immediately after it

- [ ] **Step 3: Verify expanded rows**

Run: `cd scripts/flight_tracker && python -m http.server 8787 -d data &`
Open: `http://localhost:8787/dashboard.html#flights`
Verify: Click a row → detail panel appears below with metadata grid + position map + altitude gauge. Click again → collapses. Click different row → old one collapses, new one expands. Data displays correctly (airline name from lookup, aircraft name from lookup, vertical speed colored).
Kill: `kill %1`

- [ ] **Step 4: Commit**

```bash
git add scripts/flight_tracker/data/dashboard.html
git commit -m "feat(flight-tracker): expandable detail rows with metadata and mini visualizations"
```

---

### Task 8: Responsive Design and Polish

**Files:**

- Modify: `scripts/flight_tracker/data/dashboard.html`

- [ ] **Step 1: Add responsive filter bar collapse**

Add a "Filters" toggle button that appears at `max-width: 768px`:

```html
<button id="flights-filter-toggle" class="flights-filter-toggle" onclick="document.querySelector('.flights-filter-bar').classList.toggle('expanded')">
    Filters <span id="flights-filter-badge"></span>
</button>
```

CSS:

```css
.flights-filter-toggle { display: none; background: #1e293b; color: #e2e8f0; border: 1px solid #334155; border-radius: 6px; padding: 8px 16px; font-size: 13px; cursor: pointer; width: 100%; text-align: left; }
.flights-filter-toggle .badge { background: #3b82f6; color: white; padding: 1px 6px; border-radius: 10px; font-size: 11px; margin-left: 8px; }
@media (max-width: 768px) {
    .flights-filter-toggle { display: block; }
    .flights-filter-bar { display: none; }
    .flights-filter-bar.expanded { display: flex; flex-direction: column; }
}
```

The badge shows the count of active filters.

- [ ] **Step 2: Add table horizontal scroll**

```css
.flights-table-wrapper { overflow-x: auto; -webkit-overflow-scrolling: touch; }
```

Wrap the `<table>` element in a `<div class="flights-table-wrapper">`.

- [ ] **Step 3: Final visual polish**

- Ensure row hover effect: `tr:hover { background: #1e293b; }` (but not on expanded row)
- Ensure table header sticky: `thead { position: sticky; top: 0; z-index: 1; background: #0f172a; }`
- Ensure expanded detail panel stacks vertically on narrow viewports (already in Task 7 CSS)
- Tab bar: ensure active tab indicator is clearly visible
- Check all font sizes and colors match the spec's design system

- [ ] **Step 4: Test on narrow viewport**

Run: `cd scripts/flight_tracker && python -m http.server 8787 -d data &`
Open: `http://localhost:8787/dashboard.html#flights`
Resize browser to ~375px width. Verify: "Filters" toggle button appears, filter bar is hidden until clicked, table scrolls horizontally, expanded detail stacks vertically.
Kill: `kill %1`

- [ ] **Step 5: Commit**

```bash
git add scripts/flight_tracker/data/dashboard.html
git commit -m "feat(flight-tracker): responsive design and visual polish"
```

---

### Task 9: Integration Test — Full Pipeline Round-Trip

**Files:**

- Test: `scripts/flight_tracker/tests/test_integration.py` (create)

- [ ] **Step 1: Write integration test**

Create `scripts/flight_tracker/tests/test_integration.py`:

```python
import pandas as pd
from pathlib import Path
from flight_tracker import _format_and_append, CSV_COLUMNS


def test_enriched_csv_round_trip(tmp_path, monkeypatch):
    """Full round-trip: enriched DataFrame → CSV → read back with all columns."""
    csv_path = tmp_path / "flights.csv"
    monkeypatch.setattr("flight_tracker.CSV_PATH", csv_path)
    monkeypatch.setattr("flight_tracker.DATA_DIR", tmp_path)

    flights = pd.DataFrame([
        {
            "icao24": "4B1812", "callsign": "LOT3825", "time": 1712170000,
            "lat": 52.247, "lon": 20.836, "baroaltitude": 1485.9,
            "heading": 318.0, "velocity": 143.0,
            "origin": "WAW", "destination": "GDN",
            "aircraft_type": "B738", "airline_icao": "LOT", "airline_iata": "LO",
            "registration": "SP-LWG", "flight_number": "LO3825",
            "velocity_kts": 280, "vertical_speed_fpm": 1472,
        },
        {
            "icao24": "AABBCC", "callsign": "RYR8HU", "time": 1712173600,
            "lat": 52.250, "lon": 20.840, "baroaltitude": 2232.6,
            "heading": 312.0, "velocity": 220.0,
            "origin": "WAW", "destination": "VIE",
            "aircraft_type": "A320", "airline_icao": "LDA", "airline_iata": "FR",
            "registration": "9H-LMG", "flight_number": "FR6065",
            "velocity_kts": 428, "vertical_speed_fpm": -640,
        },
    ])

    count = _format_and_append(flights)
    assert count == 2

    result = pd.read_csv(csv_path)
    assert list(result.columns) == CSV_COLUMNS
    assert len(result) == 2

    # Verify enrichment data persisted
    lot = result[result["callsign"] == "LOT3825"].iloc[0]
    assert lot["aircraft_type"] == "B738"
    assert lot["airline_icao"] == "LOT"
    assert lot["registration"] == "SP-LWG"
    assert lot["velocity_kts"] == 280
    assert lot["vertical_speed_fpm"] == 1472

    ryr = result[result["callsign"] == "RYR8HU"].iloc[0]
    assert ryr["aircraft_type"] == "A320"
    assert ryr["airline_icao"] == "LDA"
    assert ryr["vertical_speed_fpm"] == -640


def test_mixed_enriched_and_legacy_csv(tmp_path, monkeypatch):
    """Appending enriched flights to a legacy CSV (without new columns) works."""
    csv_path = tmp_path / "flights.csv"
    monkeypatch.setattr("flight_tracker.CSV_PATH", csv_path)
    monkeypatch.setattr("flight_tracker.DATA_DIR", tmp_path)

    # Write a legacy-format CSV first (missing enrichment columns)
    legacy = pd.DataFrame([{
        "date": "2026-04-01", "time_utc": "10:00:00", "time_local": "12:00:00",
        "callsign": "OLD123", "altitude_ft": 5000, "heading_deg": 270,
        "origin": "WAW", "destination": "LHR", "distance_from_home_km": 0.5,
    }])
    legacy.to_csv(csv_path, index=False)

    # Now append an enriched flight
    flights = pd.DataFrame([{
        "icao24": "NEWONE", "callsign": "NEW456", "time": 1712170000,
        "lat": 52.247, "lon": 20.836, "baroaltitude": 1829.0,
        "heading": 300.0, "velocity": 150.0,
        "origin": "WAW", "destination": "CDG",
        "aircraft_type": "A321", "airline_icao": "AFR", "airline_iata": "AF",
        "registration": "F-GKXS", "flight_number": "AF1145",
        "velocity_kts": 292, "vertical_speed_fpm": 800,
    }])

    _format_and_append(flights)
    result = pd.read_csv(csv_path)
    assert len(result) == 2

    # Legacy row should have NaN/empty enrichment fields
    old = result[result["callsign"] == "OLD123"].iloc[0]
    assert pd.isna(old["aircraft_type"]) or old["aircraft_type"] == ""

    # New row should have enrichment fields
    new = result[result["callsign"] == "NEW456"].iloc[0]
    assert new["aircraft_type"] == "A321"
    assert new["registration"] == "F-GKXS"
```

- [ ] **Step 2: Run integration tests**

Run: `cd scripts/flight_tracker && uv run pytest tests/test_integration.py -v`
Expected: PASS (2 tests)

- [ ] **Step 3: Run full test suite**

Run: `cd scripts/flight_tracker && uv run pytest tests/ -v`
Expected: All tests PASS (3 processing + 2 cache + 2 fr24_live + 3 pipeline + 2 integration = 12 tests)

- [ ] **Step 4: Commit**

```bash
git add scripts/flight_tracker/tests/test_integration.py
git commit -m "test(flight-tracker): integration tests for enriched CSV round-trip"
```

---

### Task 10: Run Enriched Pipeline and Verify Dashboard

**Files:** No code changes — verification only.

- [ ] **Step 1: Run the pipeline to collect enriched data**

```bash
cd scripts/flight_tracker && uv run python flight_tracker.py --source fr24
```

Expected: New flights appended with enrichment columns. Check output:

```bash
head -2 data/flights.csv
```

Verify: New rows have `aircraft_type`, `airline_icao`, etc. filled in.

- [ ] **Step 2: Verify the full dashboard**

```bash
cd scripts/flight_tracker && python -m http.server 8787 -d data &
```

Open `http://localhost:8787/dashboard.html`:

1. **Analytics tab:** All charts render correctly, filters work, no regressions
2. **Flights tab:** Table renders with enriched data (airline badges, aircraft types, registrations visible). Sort by altitude → color badges reorder. Search "LOT" → filters to LOT flights. Expand a row → metadata shows airline name from lookup, aircraft name from lookup, position map and altitude gauge render. Pagination works.
3. **Tab switching:** Both hash routing and localStorage persistence work.

Kill: `kill %1`

- [ ] **Step 3: Final commit (if any small fixes needed)**

```bash
git add -A
git commit -m "fix(flight-tracker): dashboard polish from manual verification"
```

Only commit if fixes were needed. Otherwise skip.
