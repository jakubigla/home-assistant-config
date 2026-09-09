---
summary: flight-tracker add-on installs from the GitHub store, not /config — only main deploys; test locally with box CSV.
before_action:
  - About to change flight-tracker add-on code (run.py, Dockerfile, static/dashboard.html, analytics.js)
  - About to test a flight-tracker feature branch on the HA box
  - About to read or download the live flights.csv / coverage.csv from the add-on
on_symptom:
  - "flight-tracker add-on still runs old code after pointing the box at a branch"
  - "ha addons info 14caed58_flight-tracker shows update_available false after a push"
  - "find / -name flights.csv on the box returns nothing"
  - "/addons/flight-tracker symlink points to a missing /root/homeassistant/addons/flight-tracker"
---

# flight-tracker add-on: deploy + live data

- **Box installs the add-on from the GitHub store repo, not from /config.** Slug is
  `14caed58_flight-tracker` (repo `14caed58` = this GitHub repo via root `repository.yaml`).
  Checking out a feature branch on the box changes nothing for the add-on. Only `main` deploys:
  bump `flight-tracker/config.yaml` `version`, merge, then `ha store reload` + `ha addons update
  14caed58_flight-tracker`. Update = image rebuild on the Yellow (apk + pip pandas) — RAM heavy,
  schedule around the OOM history (see addons-error-after-oom). Confirm with the user first.
- **`/addons/flight-tracker` symlink dangles** (`/root/homeassistant/addons/...` does not exist).
  Ignore it; it is not what runs.
- **Add-on `/data` is a private volume — not under /config, not found by `find`.** Read live
  files from the SSH add-on via the internal hostname:
  `ssh root@homeassistant.local 'curl -s http://14caed58-flight-tracker:8099/flights.csv'`
  (same for `coverage.csv`, `dashboard.html`). `just ft-download-data` does the same via ingress.
- **Local test loop beats the box.** Copy the live CSV into `flight-tracker/data/` (gitignored),
  run `FLIGHT_TRACKER_DATA_DIR=flight-tracker/data FLIGHT_TRACKER_STATIC_DIR=flight-tracker/static
  uv run --with-requirements requirements.txt --directory flight-tracker python run.py` in the
  background, Playwright `http://localhost:8099/`. Static files are copied to `data/` once at
  startup — re-`cp` after editing `dashboard.html`/`analytics.js` or restart.
- **`just ft-test`** = pytest (coverage tracker) + `node --test` (analytics). Run before pushing.
- **Add-on log via `ha addons logs 14caed58_flight-tracker`** — only the last ~100 lines survive;
  outages are invisible there. `coverage.csv` (date,hour,seconds) is the durable record of when
  the tracker was polling; days before it existed use the dashboard's flight-gap heuristic.
