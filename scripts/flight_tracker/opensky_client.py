import logging
from datetime import datetime

import pandas as pd

logger = logging.getLogger(__name__)


def fetch_state_vectors(
    start: datetime,
    stop: datetime,
    lat_min: float,
    lat_max: float,
    lon_min: float,
    lon_max: float,
    username: str,
    password: str,
) -> pd.DataFrame:
    """Fetch historical state vectors from OpenSky Trino for a bounding box and time range.

    Returns a DataFrame with columns: icao24, callsign, time, lat, lon,
    baroaltitude, heading, velocity.
    """
    from pyopensky.trino import Trino

    trino = Trino(username=username, password=password)

    logger.info(
        "Querying OpenSky: %s to %s, bounds=[%.3f, %.3f, %.3f, %.3f]",
        start.isoformat(),
        stop.isoformat(),
        lat_min,
        lat_max,
        lon_min,
        lon_max,
    )

    df = trino.history(
        start=start,
        stop=stop,
        bounds=(lat_min, lat_max, lon_min, lon_max),
    )

    if df is None or df.empty:
        logger.info("No state vectors found for the given time range and bounds.")
        return pd.DataFrame(
            columns=["icao24", "callsign", "time", "lat", "lon", "baroaltitude", "heading", "velocity"]
        )

    # Normalize column names — pyopensky returns lowercase columns but names may vary
    col_map = {
        "lat": "lat",
        "latitude": "lat",
        "lon": "lon",
        "longitude": "lon",
        "baroaltitude": "baroaltitude",
        "baro_altitude": "baroaltitude",
        "heading": "heading",
        "true_track": "heading",
        "velocity": "velocity",
        "groundspeed": "velocity",
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    required = ["icao24", "callsign", "time", "lat", "lon", "baroaltitude", "heading", "velocity"]
    for col in required:
        if col not in df.columns:
            df[col] = None

    # Drop rows without position data
    df = df.dropna(subset=["lat", "lon"])

    return df[required].reset_index(drop=True)
