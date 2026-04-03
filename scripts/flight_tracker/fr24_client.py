import json
import logging
import time
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def fetch_live_flights(
    lat_min: float,
    lat_max: float,
    lon_min: float,
    lon_max: float,
) -> pd.DataFrame:
    """Fetch currently visible flights from FlightRadar24 within a bounding box.

    Returns a DataFrame with columns matching the OpenSky format:
    icao24, callsign, time, lat, lon, baroaltitude, heading, velocity,
    plus origin and destination (IATA codes) already included.
    Also includes enrichment fields: aircraft_type, airline_icao, airline_iata,
    registration, flight_number, velocity_kts, vertical_speed_fpm.
    """
    from FlightRadar24 import FlightRadar24API

    api = FlightRadar24API()
    bounds = f"{lat_max},{lat_min},{lon_min},{lon_max}"

    logger.info("Querying FR24 for flights in bounds: %s", bounds)
    flights = api.get_flights(bounds=bounds)

    if not flights:
        logger.info("No flights found in bounding box.")
        return pd.DataFrame(
            columns=[
                "icao24", "callsign", "time", "lat", "lon",
                "baroaltitude", "heading", "velocity", "origin", "destination",
                "aircraft_type", "airline_icao", "airline_iata",
                "registration", "flight_number", "velocity_kts",
                "vertical_speed_fpm",
            ]
        )

    rows = []
    now = int(time.time())
    for f in flights:
        # Skip ground vehicles and flights on the ground
        if f.on_ground:
            continue
        rows.append({
            "icao24": f.icao_24bit or "",
            "callsign": f.callsign or "",
            "time": now,
            "lat": f.latitude,
            "lon": f.longitude,
            "baroaltitude": f.altitude * 0.3048 if f.altitude else None,  # ft -> meters for consistency
            "heading": f.heading,
            "velocity": f.ground_speed * 0.514444 if f.ground_speed else None,  # knots -> m/s
            "origin": f.origin_airport_iata or "",
            "destination": f.destination_airport_iata or "",
            "aircraft_type": f.aircraft_code or "",
            "airline_icao": f.airline_icao or "",
            "airline_iata": f.airline_iata or "",
            "registration": f.registration or "",
            "flight_number": f.number or "",
            "velocity_kts": f.ground_speed if f.ground_speed else None,
            "vertical_speed_fpm": f.vertical_speed if f.vertical_speed else None,
        })

    logger.info("Found %d airborne flights in bounding box.", len(rows))
    return pd.DataFrame(rows)


class RouteCache:
    """Persistent callsign-to-route cache backed by a JSON file."""

    def __init__(self, cache_path: Path, fr24_api: Any) -> None:
        self._path = cache_path
        self._api = fr24_api
        self._cache: dict[str, dict[str, str]] = {}
        if self._path.exists():
            self._cache = json.loads(self._path.read_text())

    def lookup(self, callsign: str) -> dict[str, str] | None:
        """Look up origin/destination for a callsign. Returns dict or None."""
        if callsign in self._cache:
            return self._cache[callsign]
        return self._fetch_and_cache(callsign)

    def enrich_dataframe(self, df: "pd.DataFrame") -> "pd.DataFrame":
        """Add origin/destination columns to a flights DataFrame."""
        import pandas as pd

        origins = []
        destinations = []
        for callsign in df["callsign"]:
            route = self.lookup(callsign.strip()) if pd.notna(callsign) else None
            if route:
                origins.append(route.get("origin", ""))
                destinations.append(route.get("destination", ""))
            else:
                origins.append("")
                destinations.append("")
        df = df.copy()
        df["origin"] = origins
        df["destination"] = destinations
        return df

    def _fetch_and_cache(self, callsign: str) -> dict[str, str] | None:
        try:
            results = self._api.search(callsign)
            flights = results.get("live", [])
            if not flights:
                logger.debug("No FR24 results for callsign %s", callsign)
                return None

            flight = flights[0]
            flight_id = flight.get("id")
            if not flight_id:
                return None

            details = self._api.get_flight_details(flight_id)
            airport = details.get("airport", {})
            origin_code = airport.get("origin", {}).get("code", {}).get("iata", "")
            dest_code = airport.get("destination", {}).get("code", {}).get("iata", "")

            if not origin_code and not dest_code:
                return None

            route = {"origin": origin_code, "destination": dest_code}
            self._cache[callsign] = route
            self._save()
            return route
        except Exception:
            logger.warning("FR24 lookup failed for %s", callsign, exc_info=True)
            return None

    def _save(self) -> None:
        self._path.write_text(json.dumps(self._cache, indent=2))
