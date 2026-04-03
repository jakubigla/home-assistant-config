#!/usr/bin/env python3
"""Flight tracker: fetch live flights over Babice Nowe and append to CSV."""

import logging
from pathlib import Path

import pandas as pd

from fr24_client import fetch_live_flights
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
