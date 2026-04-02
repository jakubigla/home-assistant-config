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
