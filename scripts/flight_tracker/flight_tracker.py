#!/usr/bin/env python3
"""Flight tracker: fetch flights over Babice Nowe and append to CSV."""

import argparse
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
from FlightRadar24 import FlightRadar24API

from fr24_client import RouteCache, fetch_live_flights
from opensky_client import fetch_state_vectors
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

DATA_DIR = Path(__file__).parent / "data"
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
]

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
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

    # Dedup and append to CSV
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if CSV_PATH.exists():
        existing = pd.read_csv(CSV_PATH, dtype=str)
        existing_keys = set(zip(existing["callsign"], existing["date"]))
        mask = output.apply(lambda r: (r["callsign"], r["date"]) not in existing_keys, axis=1)
        new_flights = output[mask]
    else:
        new_flights = output

    if new_flights.empty:
        logger.info("No new flights to append (all duplicates).")
        return 0

    new_flights.to_csv(
        CSV_PATH,
        mode="a",
        header=not CSV_PATH.exists(),
        index=False,
        columns=CSV_COLUMNS,
    )
    logger.info("Appended %d new flights to %s.", len(new_flights), CSV_PATH)
    return len(new_flights)


def run_opensky_pipeline(start: datetime, stop: datetime) -> int:
    """Fetch historical data from OpenSky Trino and append to CSV."""
    logger.info("Stage 1: Fetching state vectors from OpenSky...")
    raw = fetch_state_vectors(
        start=start,
        stop=stop,
        lat_min=LAT_MIN,
        lat_max=LAT_MAX,
        lon_min=LON_MIN,
        lon_max=LON_MAX,
    )
    if raw.empty:
        logger.info("No flights found.")
        return 0

    logger.info("Fetched %d state vectors.", len(raw))

    logger.info("Stage 2: Collapsing to unique flights...")
    flights = collapse_to_flights(raw, HOME_LAT, HOME_LON)
    logger.info("Found %d unique flights.", len(flights))

    logger.info("Stage 3: Enriching with FR24 route data...")
    fr24_api = FlightRadar24API()
    cache = RouteCache(CACHE_PATH, fr24_api)
    flights = cache.enrich_dataframe(flights)

    return _format_and_append(flights)


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

    # FR24 already returns one row per flight with origin/destination
    # No need to collapse or enrich
    flights = collapse_to_flights(raw, HOME_LAT, HOME_LON)
    logger.info("Found %d flights.", len(flights))

    return _format_and_append(flights)


def main() -> None:
    parser = argparse.ArgumentParser(description="Track flights over Babice Nowe.")
    parser.add_argument(
        "--source",
        choices=["fr24", "opensky"],
        default="fr24",
        help="Data source: fr24 (live snapshot, default) or opensky (historical, requires Trino access).",
    )
    parser.add_argument(
        "--from",
        dest="start_date",
        type=str,
        help="Start date (YYYY-MM-DD). OpenSky only. Default: yesterday.",
    )
    parser.add_argument(
        "--to",
        dest="end_date",
        type=str,
        help="End date (YYYY-MM-DD). OpenSky only. Default: same as start date.",
    )
    args = parser.parse_args()

    if args.source == "fr24":
        if args.start_date or args.end_date:
            logger.warning("--from/--to are ignored with --source=fr24 (live data only).")
        count = run_fr24_pipeline()
        logger.info("Done. New flights: %d", count)
    else:
        if args.start_date:
            start = datetime.strptime(args.start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        else:
            start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)

        if args.end_date:
            stop = datetime.strptime(args.end_date, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59, tzinfo=timezone.utc
            )
        else:
            stop = start.replace(hour=23, minute=59, second=59)

        logger.info("Running OpenSky pipeline for %s to %s", start.date(), stop.date())
        total = 0
        current = start
        while current <= stop:
            day_start = current
            day_stop = current.replace(hour=23, minute=59, second=59)
            count = run_opensky_pipeline(day_start, day_stop)
            total += count
            current += timedelta(days=1)

        logger.info("Done. Total new flights: %d", total)


if __name__ == "__main__":
    main()
