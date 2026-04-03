# Flight Tracker HA Add-on Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Package the FR24 flight tracker as a local HA add-on that polls FlightRadar24 every N seconds and serves the analysis dashboard via Ingress.

**Architecture:** Single Docker container running an async Python entry point with two concurrent tasks — a polling loop that calls the FR24 pipeline and appends to CSV, and an aiohttp web server that serves the dashboard and data files through HA Ingress.

**Tech Stack:** Python 3.11, aiohttp, pandas, FlightRadarAPI, Docker (Alpine-based)

**Spec:** `docs/superpowers/specs/2026-04-03-flight-tracker-addon-design.md`

---

## File Structure

```
addons/flight-tracker/
├── Dockerfile              # Python 3.11 Alpine image with pip deps
├── config.yaml             # HA add-on metadata (ingress, options, arch)
├── run.py                  # Entry point: async poller + aiohttp web server
├── flight_tracker.py       # FR24 pipeline + CSV append (adapted from scripts/)
├── fr24_client.py          # FR24 live fetcher (copy from scripts/)
├── processing.py           # Distance calc + collapse (copy from scripts/)
├── static/                 # Static assets served by the web server
│   ├── dashboard.html      # Copy from scripts/flight_tracker/data/
│   ├── airports.json       # Copy from scripts/flight_tracker/data/
│   ├── airlines.json       # Copy from scripts/flight_tracker/data/
│   └── aircraft.json       # Copy from scripts/flight_tracker/data/
```

---

### Task 1: Create add-on skeleton (config.yaml + Dockerfile)

**Files:**

- Create: `addons/flight-tracker/config.yaml`
- Create: `addons/flight-tracker/Dockerfile`

- [ ] **Step 1: Create the addons directory**

```bash
mkdir -p addons/flight-tracker
```

- [ ] **Step 2: Create config.yaml**

Create `addons/flight-tracker/config.yaml`:

```yaml
name: Flight Tracker
version: "0.1.0"
slug: flight-tracker
description: Track overhead flights from FlightRadar24 and analyze noise patterns
url: "https://github.com/jakubigla/home-assistant-config"
arch:
  - aarch64
  - amd64
init: false
startup: application
ingress: true
ingress_port: 8099
panel_icon: "mdi:airplane"
panel_title: Flight Tracker
options:
  poll_interval_seconds: 10
schema:
  poll_interval_seconds: "int(1,300)"
```

- [ ] **Step 3: Create Dockerfile**

Create `addons/flight-tracker/Dockerfile`:

```dockerfile
ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base-python:3.11-alpine3.18
FROM ${BUILD_FROM}

WORKDIR /app

# Install build dependencies for pandas, then clean up
RUN apk add --no-cache --virtual .build-deps \
        gcc musl-dev python3-dev && \
    pip install --no-cache-dir \
        pandas==2.2.3 \
        FlightRadarAPI==1.3.48 \
        aiohttp==3.11.18 && \
    apk del .build-deps

COPY run.py flight_tracker.py fr24_client.py processing.py ./
COPY static/ ./static/

CMD ["python", "-u", "run.py"]
```

- [ ] **Step 4: Commit**

```bash
git add addons/flight-tracker/config.yaml addons/flight-tracker/Dockerfile
git commit -m "feat(flight-tracker): add-on skeleton with config.yaml and Dockerfile"
```

---

### Task 2: Copy and adapt the Python source files

**Files:**

- Create: `addons/flight-tracker/processing.py`
- Create: `addons/flight-tracker/fr24_client.py`
- Create: `addons/flight-tracker/flight_tracker.py`

- [ ] **Step 1: Copy processing.py as-is**

Copy `scripts/flight_tracker/processing.py` to `addons/flight-tracker/processing.py` — no changes needed.

- [ ] **Step 2: Copy fr24_client.py as-is**

Copy `scripts/flight_tracker/fr24_client.py` to `addons/flight-tracker/fr24_client.py` — no changes needed.

- [ ] **Step 3: Create the adapted flight_tracker.py**

Create `addons/flight-tracker/flight_tracker.py` — adapted from `scripts/flight_tracker/flight_tracker.py` with these changes:

- Remove: `argparse`, `main()`, `run_opensky_pipeline()`, `opensky_client` import
- Change: `DATA_DIR` points to `/data` (HA persistent storage)
- Change: `CACHE_PATH` points to `/data/route_cache.json`
- Keep: `run_fr24_pipeline()`, `_format_and_append()`, `meters_to_feet()`, all constants

```python
#!/usr/bin/env python3
"""Flight tracker: fetch live flights over Babice Nowe and append to CSV."""

import logging
from pathlib import Path

import pandas as pd
from FlightRadar24 import FlightRadar24API

from fr24_client import RouteCache, fetch_live_flights
from processing import _approx_distance_km, collapse_to_flights

# --- Configuration ---
HOME_LAT = 52.2474
HOME_LON = 20.8363
RADIUS_KM = 1

# Approximate bounding box from radius (1 deg lat ~ 111 km, 1 deg lon ~ 70 km at this latitude)
LAT_DELTA = RADIUS_KM / 111.0
LON_DELTA = RADIUS_KM / 70.0

LAT_MIN = HOME_LAT - LAT_DELTA
LAT_MAX = HOME_LAT + LAT_DELTA
LON_MIN = HOME_LON - LON_DELTA
LON_MAX = HOME_LON + LON_DELTA

DATA_DIR = Path("/data")
CSV_PATH = DATA_DIR / "flights.csv"
CACHE_PATH = DATA_DIR / "route_cache.json"

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

logger = logging.getLogger(__name__)


def meters_to_feet(m: float | None) -> float | None:
    return round(m * 3.28084) if m is not None else None


def _format_and_append(flights: pd.DataFrame) -> int:
    """Format flights DataFrame and append new entries to CSV. Returns count appended."""
    output = pd.DataFrame()
    output["date"] = pd.to_datetime(flights["time"], unit="s", utc=True).dt.strftime("%Y-%m-%d")
    output["time_utc"] = pd.to_datetime(flights["time"], unit="s", utc=True).dt.strftime("%H:%M:%S")
    output["time_local"] = (
        pd.to_datetime(flights["time"], unit="s", utc=True)
        .dt.tz_convert("Europe/Warsaw")
        .dt.strftime("%H:%M:%S")
    )
    output["callsign"] = flights["callsign"].str.strip()
    output["altitude_ft"] = flights["baroaltitude"].apply(meters_to_feet)
    output["heading_deg"] = flights["heading"].round(0)
    output["origin"] = flights["origin"]
    output["destination"] = flights["destination"]
    output["distance_from_home_km"] = flights.apply(
        lambda r: round(_approx_distance_km(r["lat"], r["lon"], HOME_LAT, HOME_LON), 1),
        axis=1,
    )
    output["aircraft_type"] = flights["aircraft_type"] if "aircraft_type" in flights.columns else ""
    output["airline_icao"] = flights["airline_icao"] if "airline_icao" in flights.columns else ""
    output["airline_iata"] = flights["airline_iata"] if "airline_iata" in flights.columns else ""
    output["registration"] = flights["registration"] if "registration" in flights.columns else ""
    output["flight_number"] = flights["flight_number"] if "flight_number" in flights.columns else ""
    output["velocity_kts"] = flights["velocity_kts"].round(0).astype("Int64") if "velocity_kts" in flights.columns else pd.NA
    output["vertical_speed_fpm"] = flights["vertical_speed_fpm"].round(0).astype("Int64") if "vertical_speed_fpm" in flights.columns else pd.NA

    # Merge with existing CSV: update if closer, insert if new
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if CSV_PATH.exists():
        existing = pd.read_csv(CSV_PATH)
        combined = pd.concat([existing, output], ignore_index=True)
        combined["distance_from_home_km"] = pd.to_numeric(combined["distance_from_home_km"], errors="coerce")
        combined = combined.sort_values("distance_from_home_km").drop_duplicates(
            subset=["callsign", "date"], keep="first"
        ).sort_values(["date", "time_local"]).reset_index(drop=True)
        updated = len(combined)
        previous = len(existing)
    else:
        combined = output
        updated = len(combined)
        previous = 0

    combined.to_csv(CSV_PATH, index=False, columns=CSV_COLUMNS)
    new_count = updated - previous
    if new_count > 0:
        logger.info("Appended %d new flights to %s.", new_count, CSV_PATH)
    elif updated < previous:
        logger.info("Updated %d flights with closer passes.", previous - updated)
    else:
        logger.info("Updated existing flights (no new flights).")
    return max(new_count, 0)


def run_fr24_pipeline() -> int:
    """Fetch live flights from FlightRadar24 and append to CSV."""
    logger.info("Fetching live flights from FlightRadar24...")
    raw = fetch_live_flights(
        lat_min=LAT_MIN,
        lat_max=LAT_MAX,
        lon_min=LON_MIN,
        lon_max=LON_MAX,
    )
    if raw.empty:
        logger.info("No flights found.")
        return 0

    flights = collapse_to_flights(raw, HOME_LAT, HOME_LON)
    logger.info("Found %d flights.", len(flights))

    return _format_and_append(flights)
```

- [ ] **Step 4: Commit**

```bash
git add addons/flight-tracker/processing.py addons/flight-tracker/fr24_client.py addons/flight-tracker/flight_tracker.py
git commit -m "feat(flight-tracker): add Python source files for add-on"
```

---

### Task 3: Copy static assets (dashboard + lookup JSONs)

**Files:**

- Create: `addons/flight-tracker/static/dashboard.html`
- Create: `addons/flight-tracker/static/airports.json`
- Create: `addons/flight-tracker/static/airlines.json`
- Create: `addons/flight-tracker/static/aircraft.json`

- [ ] **Step 1: Create the static directory and copy files**

```bash
mkdir -p addons/flight-tracker/static
cp scripts/flight_tracker/data/dashboard.html addons/flight-tracker/static/
cp scripts/flight_tracker/data/airports.json addons/flight-tracker/static/
cp scripts/flight_tracker/data/airlines.json addons/flight-tracker/static/
cp scripts/flight_tracker/data/aircraft.json addons/flight-tracker/static/
```

- [ ] **Step 2: Commit**

```bash
git add addons/flight-tracker/static/
git commit -m "feat(flight-tracker): add dashboard and lookup assets"
```

---

### Task 4: Create the entry point (run.py)

**Files:**

- Create: `addons/flight-tracker/run.py`

- [ ] **Step 1: Create run.py**

Create `addons/flight-tracker/run.py`:

```python
#!/usr/bin/env python3
"""Flight tracker add-on entry point: polling loop + Ingress web server."""

import asyncio
import json
import logging
import shutil
from pathlib import Path

from aiohttp import web

from flight_tracker import run_fr24_pipeline

OPTIONS_PATH = Path("/data/options.json")
STATIC_DIR = Path("/app/static")
DATA_DIR = Path("/data")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("flight-tracker")


def load_options() -> dict:
    """Load add-on options from /data/options.json."""
    if OPTIONS_PATH.exists():
        return json.loads(OPTIONS_PATH.read_text())
    return {"poll_interval_seconds": 10}


def setup_static_files() -> None:
    """Copy static assets to /data/ so the web server can serve them alongside CSV."""
    for filename in ("dashboard.html", "airports.json", "airlines.json", "aircraft.json"):
        src = STATIC_DIR / filename
        dst = DATA_DIR / filename
        if src.exists():
            shutil.copy2(src, dst)
            logger.info("Copied %s to %s", src, dst)


async def poll_loop(interval: int) -> None:
    """Run the FR24 pipeline on a fixed interval."""
    logger.info("Starting polling loop (interval=%ds)", interval)
    while True:
        try:
            count = run_fr24_pipeline()
            logger.info("Poll complete. New flights: %d", count)
        except Exception:
            logger.exception("Polling failed")
        await asyncio.sleep(interval)


async def start_web_server() -> web.AppRunner:
    """Start an aiohttp static file server for /data/ on the Ingress port."""
    app = web.Application()

    async def index_handler(request: web.Request) -> web.FileResponse:
        return web.FileResponse(DATA_DIR / "dashboard.html")

    app.router.add_get("/", index_handler)
    app.router.add_static("/", DATA_DIR, show_index=False)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8099)
    await site.start()
    logger.info("Web server started on port 8099")
    return runner


async def main() -> None:
    options = load_options()
    interval = options.get("poll_interval_seconds", 10)

    # Ensure /data exists and copy static assets
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    setup_static_files()

    # Start web server and polling loop concurrently
    runner = await start_web_server()
    try:
        await poll_loop(interval)
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Commit**

```bash
git add addons/flight-tracker/run.py
git commit -m "feat(flight-tracker): add entry point with polling loop and Ingress web server"
```

---

### Task 5: Build and test the Docker image locally

- [ ] **Step 1: Build the Docker image for amd64**

```bash
cd addons/flight-tracker
docker build --build-arg BUILD_FROM=ghcr.io/home-assistant/amd64-base-python:3.11-alpine3.18 -t flight-tracker-test .
```

Expected: Image builds successfully. If pandas build fails on Alpine, may need to add `numpy` or use a pre-built wheel. Diagnose and fix the Dockerfile.

- [ ] **Step 2: Run the container with a test /data volume**

```bash
mkdir -p /tmp/flight-tracker-data
docker run --rm -p 8099:8099 \
  -v /tmp/flight-tracker-data:/data \
  -e SUPERVISOR_TOKEN=test \
  flight-tracker-test &

# Wait for startup
sleep 5

# Check web server responds
curl -s http://localhost:8099/ | head -5

# Check CSV was created after a poll
sleep 15
ls -la /tmp/flight-tracker-data/

# Stop the container
docker stop $(docker ps -q --filter ancestor=flight-tracker-test)
```

Expected: Web server returns the dashboard HTML. After ~10s a `flights.csv` appears in the data directory (may be empty if no flights overhead at test time).

- [ ] **Step 3: Commit any fixes from testing**

If the Dockerfile or run.py needed adjustments, commit them:

```bash
git add addons/flight-tracker/
git commit -m "fix(flight-tracker): adjustments from local Docker testing"
```

---

### Task 6: Push and install on HA Yellow

- [ ] **Step 1: Create a branch and push**

```bash
git checkout -b feature/flight-tracker-addon
git push -u origin feature/flight-tracker-addon
```

- [ ] **Step 2: Install on HA Yellow**

On the HA Yellow, the `addons/` directory is auto-discovered:

1. Go to **Settings > Add-ons > Add-on Store**
2. Click the **⋮** menu (top right) > **Check for updates** or **Reload**
3. Under **Local add-ons**, find **Flight Tracker**
4. Click **Install** — this triggers a Docker build on the Yellow (ARM64, may take several minutes)
5. After install, toggle **Show in sidebar** on
6. Click **Start**
7. Verify the **Flight Tracker** panel appears in the sidebar and loads the dashboard

- [ ] **Step 3: Verify data collection**

Wait a few minutes, then check the add-on logs:

1. Go to **Settings > Add-ons > Flight Tracker > Log**
2. Look for `Poll complete. New flights: N` messages
3. Verify the dashboard shows data by clicking the sidebar panel

- [ ] **Step 4: Create PR**

```bash
gh pr create --title "feat(flight-tracker): HA add-on for overhead flight tracking" \
  --body "$(cat <<'EOF'
## Summary
- Packages the FR24 flight tracker as a local HA add-on
- Polls FlightRadar24 every 10s for aircraft within 1km of home
- Serves the analysis dashboard via HA Ingress (sidebar panel)
- Configurable polling interval via add-on options

## Test plan
- [ ] Docker image builds on amd64
- [ ] Docker image builds on aarch64 (HA Yellow)
- [ ] Dashboard accessible via Ingress sidebar panel
- [ ] flights.csv populated after polling
- [ ] Polling interval configurable via add-on options
EOF
)"
```
