import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


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
