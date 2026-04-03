from math import radians, cos, sqrt

import pandas as pd


def _approx_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Fast approximate distance using equirectangular projection. Good enough for <50 km."""
    lat1_r, lat2_r = radians(lat1), radians(lat2)
    x = (radians(lon2) - radians(lon1)) * cos((lat1_r + lat2_r) / 2)
    y = lat2_r - lat1_r
    return sqrt(x * x + y * y) * 6371


def collapse_to_flights(
    df: pd.DataFrame, home_lat: float, home_lon: float
) -> pd.DataFrame:
    """Collapse state vectors to one row per flight, picking the closest point to home.

    Groups by icao24 (unique aircraft address). For each group, selects the
    state vector with the smallest distance to home coordinates.
    """
    if df.empty:
        return df.copy()

    df = df.copy()
    df["_dist"] = df.apply(
        lambda r: _approx_distance_km(r["lat"], r["lon"], home_lat, home_lon), axis=1
    )
    idx = df.groupby("icao24")["_dist"].idxmin()
    result = df.loc[idx].drop(columns=["_dist"]).reset_index(drop=True)
    return result
