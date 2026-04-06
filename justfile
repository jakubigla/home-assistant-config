set dotenv-load

# Home Assistant Configuration Tasks

# Push all changes with a standard commit message
push:
    git add .
    git commit -m "chore: changes"
    git push

# Validate YAML files
lint:
    yamllint .

# Check Home Assistant configuration (requires HA installed)
check:
    hass --config . --check-config

# Snapshot current flights over Babice Nowe (FR24 live)
flights:
    cd scripts/flight_tracker && uv run python flight_tracker.py

# Fetch flights for a specific date range (OpenSky historical, requires Trino access)
flights-range from to:
    cd scripts/flight_tracker && uv run python flight_tracker.py --source opensky --from {{from}} --to {{to}}

# Backfill last 30 days of flight data (OpenSky historical)
flights-backfill:
    cd scripts/flight_tracker && uv run python flight_tracker.py --source opensky --from $(date -v-30d +%Y-%m-%d) --to $(date -v-1d +%Y-%m-%d)

# Open flight tracker dashboard
flights-dashboard:
    cd scripts/flight_tracker/data && open http://localhost:8787/dashboard.html && python3 -m http.server 8787

# Run flight tracker locally (poll + web server on http://localhost:8099)
ft-run:
    @echo "Starting flight tracker locally — dashboard at http://localhost:8099"
    cd flight-tracker && FLIGHT_TRACKER_DATA_DIR=./data FLIGHT_TRACKER_STATIC_DIR=./static uv run --with-requirements requirements.txt watchfiles "python run.py" . --filter python

# Run a single flight tracker poll locally
ft-poll:
    cd flight-tracker && FLIGHT_TRACKER_DATA_DIR=./data uv run --with-requirements requirements.txt python -c "import logging; logging.basicConfig(level=logging.INFO); from flight_tracker import run_fr24_pipeline; run_fr24_pipeline()"

# Download flights.csv from the HA flight-tracker add-on via ingress proxy
ft-download-data:
    #!/usr/bin/env python3
    import asyncio, json, os, urllib.request, websockets
    async def main():
        ws_url, token, ha_url = os.environ["HA_WS"], os.environ["HA_TOKEN"], os.environ["HA_URL"]
        async with websockets.connect(ws_url) as ws:
            await ws.recv()
            await ws.send(json.dumps({"type": "auth", "access_token": token}))
            await ws.recv()
            await ws.send(json.dumps({"id": 1, "type": "supervisor/api", "endpoint": "/ingress/session", "method": "post"}))
            session = json.loads(await ws.recv())["result"]["session"]
            await ws.send(json.dumps({"id": 2, "type": "supervisor/api", "endpoint": "/addons/14caed58_flight-tracker/info", "method": "get"}))
            ingress = json.loads(await ws.recv())["result"]["ingress_entry"]
            req = urllib.request.Request(f"{ha_url}{ingress}/flights.csv")
            req.add_header("Cookie", f"ingress_session={session}")
            data = urllib.request.urlopen(req).read()
            os.makedirs("flight-tracker/data", exist_ok=True)
            with open("flight-tracker/data/flights.csv", "wb") as f:
                f.write(data)
            print(f"Downloaded to flight-tracker/data/flights.csv ({data.decode().count(chr(10))} lines)")
    asyncio.run(main())
