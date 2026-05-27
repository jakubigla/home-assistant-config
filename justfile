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

# Run flight tracker locally (poll + web server on http://localhost:8099)
ft-run:
    @echo "Starting flight tracker locally — dashboard at http://localhost:8099"
    cd flight-tracker && FLIGHT_TRACKER_DATA_DIR=./data FLIGHT_TRACKER_STATIC_DIR=./static uv run --with-requirements requirements.txt watchfiles "python run.py" . --filter python

# Run a single flight tracker poll locally
ft-poll:
    cd flight-tracker && FLIGHT_TRACKER_DATA_DIR=./data uv run --with-requirements requirements.txt python -c "import logging; logging.basicConfig(level=logging.INFO); from flight_tracker import run_fr24_pipeline; run_fr24_pipeline()"

# Download flights.csv from the HA flight-tracker add-on via ingress proxy
ft-download-data:
    uv run flight-tracker/scripts/download_data.py

# Regenerate the knowledge INDEX.md leaf table from frontmatter
knowledge-index:
    uv run scripts/knowledge/build_index.py

# Validate knowledge frontmatter, INDEX table freshness + skill pointer integrity
knowledge-check:
    uv run scripts/knowledge/check_index.py
