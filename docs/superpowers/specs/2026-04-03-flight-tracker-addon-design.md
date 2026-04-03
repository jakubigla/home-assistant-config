# Flight Tracker HA Add-on Design

## Overview

Package the existing FR24 live flight tracker as a Home Assistant add-on that runs on HA Yellow (aarch64). The add-on polls FlightRadar24 every N seconds for aircraft within 1 km of home, logs each unique flight to a CSV, and serves the existing analysis dashboard via HA Ingress.

## Scope

**In scope:**

- FR24 live polling loop
- CSV data collection with deduplication (closest pass per callsign+date)
- Route cache (callsign-to-route JSON)
- Dashboard served via Ingress (accessible from HA sidebar)
- Configurable polling interval via add-on options

**Out of scope:**

- OpenSky/Trino historical data
- HA sensor entities
- External port exposure

## Architecture

Single Docker container running one Python async process with two tasks:

1. **Poller task** — calls `run_fr24_pipeline()` every `poll_interval_seconds` (default: 10), writes to `/data/flights.csv` and `/data/route_cache.json`
2. **Web server task** — serves files from `/data/` on the Ingress port for the dashboard

### Data flow

```
FR24 API → fr24_client.py → processing.py → flight_tracker.py → /data/flights.csv
                                                                        ↓
                                              dashboard.html (JS) ← reads CSV via fetch()
                                                                        ↓
                                              HA Ingress ← serves dashboard + CSV
```

## File Structure

```
addons/flight-tracker/
├── Dockerfile           # Python 3.11 on Alpine, pip install deps
├── config.yaml          # HA add-on metadata
├── run.py               # Entry point: async poller + web server
├── flight_tracker.py    # FR24 pipeline + CSV append (adapted)
├── fr24_client.py       # FR24 live fetcher (copied as-is)
├── processing.py        # Distance calc + collapse (copied as-is)
└── dashboard.html       # Static dashboard (copied from scripts/data/)
```

### Persistent storage (`/data/`)

HA mounts a persistent `/data/` volume for the add-on. Contents:

- `flights.csv` — growing flight log
- `route_cache.json` — callsign-to-route cache
- `dashboard.html` — copied from add-on on startup (updated on add-on updates)

## Add-on Configuration

### `config.yaml`

```yaml
name: Flight Tracker
version: "0.1.0"
slug: flight-tracker
description: Track overhead flights and analyze noise patterns
url: "https://github.com/jakubigla/home-assistant-config"
arch:
  - aarch64
  - amd64
ingress: true
ingress_port: 8099
panel_icon: mdi:airplane
panel_title: Flight Tracker
options:
  poll_interval_seconds: 10
schema:
  poll_interval_seconds: int(1,300)
startup: application
init: false
```

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `poll_interval_seconds` | int | 10 | Seconds between FR24 polls (1-300) |

## Dockerfile

Base: `python:3.11-alpine`

Install:

- `pandas`
- `FlightRadarAPI`

No need for `pyopensky` or Trino libraries.

The image copies all Python source files and `dashboard.html` into `/app/`.

## Entry Point (`run.py`)

```python
# Pseudocode
async def main():
    # Read options from /data/options.json
    interval = options["poll_interval_seconds"]

    # Copy dashboard.html to /data/ on every start
    shutil.copy("/app/dashboard.html", "/data/dashboard.html")

    # Start web server on ingress port
    server = start_file_server("/data/", port=8099)

    # Polling loop
    while True:
        try:
            run_fr24_pipeline()
        except Exception:
            logger.exception("Polling failed")
        await asyncio.sleep(interval)
```

## Changes to Existing Code

### `flight_tracker.py` (adapted)

- Remove: `argparse`, `main()`, `run_opensky_pipeline()`, OpenSky imports
- Keep: `run_fr24_pipeline()`, `_format_and_append()`, `meters_to_feet()`, constants
- Change: `DATA_DIR` and `CSV_PATH` point to `/data/` instead of `Path(__file__).parent / "data"`
- Change: `CACHE_PATH` points to `/data/route_cache.json`

### `fr24_client.py` — copied as-is

### `processing.py` — copied as-is

### `dashboard.html` — copied as-is from `scripts/flight_tracker/data/dashboard.html`

## Ingress Integration

The web server must handle HA's Ingress proxy headers. HA proxies requests to `http://localhost:8099` and rewrites paths. The dashboard's `fetch()` calls for `flights.csv` use relative paths, which work correctly through Ingress without modification.

The web server sets CORS headers to allow HA's frontend to load the iframe content.

## Installation

The add-on is a "local add-on". It needs to be built on the HA Yellow:

1. The `addons/flight-tracker/` directory is part of the HA config repo
2. HA auto-discovers local add-ons in the `addons/` directory at the config root
3. User installs via Settings > Add-ons > Local add-ons > Flight Tracker > Install
4. First install triggers a Docker build on the Yellow (may take a few minutes on ARM)

## Testing

- Run `Dockerfile` build locally on amd64 to verify image builds
- Run the container locally with a mounted `/data/` to verify polling and web server
- Verify dashboard loads and reads CSV through the local web server
