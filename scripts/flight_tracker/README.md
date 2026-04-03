# Flight Tracker - Babice Nowe

Tracks flights passing over Babice Nowe (Wieruchowska 7A/1, Garden Park) to find the quietest times for garden use.

## How It Works

A Python script polls FlightRadar24 every 10 seconds for aircraft within a 1 km radius of home. Each unique flight per day is recorded in a CSV with its closest pass. A browser dashboard visualizes the data using a noise scoring system that weights low-altitude flights as more disruptive.

## Quick Start

```bash
# Install dependencies
cd scripts/flight_tracker && uv sync

# Single snapshot
just flights

# Open the dashboard
just flights-dashboard

# Install background polling (every 10s via launchd)
./scripts/flight_tracker/install_cron.sh install
```

## Data Collection

### CLI Usage

```bash
# FR24 live snapshot (default) - captures current flights overhead
uv run python flight_tracker.py

# OpenSky historical (requires Trino access)
uv run python flight_tracker.py --source opensky --from 2026-03-01 --to 2026-03-31
```

### Justfile Recipes

| Command | Description |
|---------|-------------|
| `just flights` | FR24 live snapshot |
| `just flights-range 2026-03-01 2026-03-31` | OpenSky historical date range |
| `just flights-backfill` | OpenSky last 30 days |
| `just flights-dashboard` | Open dashboard in browser |

### Background Polling

```bash
# Install launchd job (polls every 10 seconds)
./install_cron.sh install

# Stop and remove
./install_cron.sh uninstall
```

Requires macOS. The job runs while the Mac is awake and pauses during sleep. Log output goes to `data/cron.log`.

### Data Sources

**FlightRadar24 (default)** - Queries live flights via the unofficial `FlightRadarAPI` Python package. No account needed. Returns aircraft position, altitude, heading, and origin/destination airports. Best for continuous polling.

**OpenSky Network** - Queries historical state vectors via `pyopensky` Trino interface. Requires a free account at opensky-network.org with Trino access enabled. Best for backfilling historical data. Credentials are read from env vars `OPENSKY_TRINO_USERNAME` / `OPENSKY_TRINO_PASSWORD`.

## Configuration

Constants at the top of `flight_tracker.py`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `HOME_LAT` | 52.2474 | Home latitude |
| `HOME_LON` | 20.8363 | Home longitude |
| `RADIUS_KM` | 1 | Bounding box radius in km |

Polling interval is set in `install_cron.sh` (default: 10 seconds).

## CSV Format

Output file: `data/flights.csv`

| Column | Description |
|--------|-------------|
| `date` | Date (YYYY-MM-DD) |
| `time_utc` | Time in UTC (HH:MM:SS) |
| `time_local` | Time in Europe/Warsaw (HH:MM:SS) |
| `callsign` | Aircraft callsign (e.g., LOT3825) |
| `altitude_ft` | Barometric altitude in feet |
| `heading_deg` | Heading in degrees (0-360) |
| `origin` | Origin airport IATA code |
| `destination` | Destination airport IATA code |
| `distance_from_home_km` | Distance from home at closest pass |

### Deduplication

When the same flight (callsign + date) is seen multiple times, only the record with the **smallest distance from home** is kept. Time and altitude update to reflect that closest pass.

## Dashboard

A single-page HTML dashboard at `data/dashboard.html`. Serve it locally:

```bash
just flights-dashboard
# Opens http://localhost:8787/dashboard.html
```

### Features

- **Noise score per hour** - Bar chart showing cumulative noise by hour of day
- **Weekly noise heatmap** - Flight count per hour/day with noise-based coloring
- **Quietest garden windows** - Per day-of-week, consecutive 2h+ blocks with lowest noise
- **Top routes** - Most frequent flight paths overhead
- **Noisiest time** - Hour with highest cumulative noise score
- **Recent flights table** - Last 50 flights with per-flight noise score

### Noise Scoring

Noise is estimated from altitude using an inverse power law:

```text
noise_score = 1 / (altitude_ft / 1000) ^ exponent
```

| Altitude | Exponent 1.0 | Exponent 1.5 (default) | Exponent 2.0 |
|----------|-------------|----------------------|-------------|
| 3,750 ft | 0.267 | 0.138 | 0.071 |
| 5,000 ft | 0.200 | 0.089 | 0.040 |
| 7,000 ft | 0.143 | 0.054 | 0.020 |

The exponent controls how much altitude matters relative to flight count:

- **0.5** - Altitude barely matters, nearly raw flight count
- **1.5** (default) - Balanced; two high planes ~ one low plane
- **3.0** - Altitude dominates; one low plane far outweighs several high ones

The exponent is adjustable via a slider in the dashboard filter bar. All charts, heatmaps, and quiet windows recalculate live when adjusted.

### Filters

- **Period** - All time, last 7/14/30 days
- **Day type** - All, weekdays, weekends
- **Altitude weight** - Slider from 0.5 to 3.0

## File Structure

```text
scripts/flight_tracker/
├── flight_tracker.py      # Main CLI script and pipeline
├── fr24_client.py         # FlightRadar24 live fetcher + route cache
├── opensky_client.py      # OpenSky Trino historical fetcher
├── processing.py          # State vector collapse (closest point per flight)
├── install_cron.sh        # macOS launchd install/uninstall
├── pyproject.toml         # Python dependencies
├── tests/                 # Unit tests
│   ├── test_processing.py
│   └── test_fr24_cache.py
└── data/                  # Output (gitignored except dashboard/map)
    ├── flights.csv        # Growing flight log
    ├── route_cache.json   # Callsign-to-route cache
    ├── dashboard.html     # Analysis dashboard
    ├── map.html           # Bounding box visualization
    └── cron.log           # Background polling log
```

## Observations

Based on initial data collection, the location is directly under the **northbound departure corridor from Warsaw Chopin Airport (EPWA)**. Nearly all tracked flights are WAW departures heading 312-337 degrees to destinations like CPH, GDN, HEL, ARN, VNO, TLL, RIX, and GOT. Altitude overhead ranges from ~3,750 ft (short hops to Gdansk/Vilnius) to ~7,300 ft (longer routes to Helsinki). Shorter routes produce significantly more noise as aircraft are still in the initial climb phase.
