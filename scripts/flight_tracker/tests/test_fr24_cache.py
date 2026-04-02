import json
from pathlib import Path
from unittest.mock import MagicMock

from fr24_client import RouteCache


def test_cache_hit(tmp_path: Path):
    """Known callsign returns cached route without API call."""
    cache_file = tmp_path / "route_cache.json"
    cache_file.write_text(json.dumps({"LOT123": {"origin": "WAW", "destination": "LHR"}}))

    mock_api = MagicMock()
    cache = RouteCache(cache_file, mock_api)

    result = cache.lookup("LOT123")
    assert result == {"origin": "WAW", "destination": "LHR"}
    mock_api.search.assert_not_called()


def test_cache_miss_calls_api(tmp_path: Path):
    """Unknown callsign queries FR24 and caches the result."""
    cache_file = tmp_path / "route_cache.json"
    cache_file.write_text(json.dumps({}))

    mock_api = MagicMock()
    mock_api.search.return_value = {
        "live": [
            {
                "id": "12345",
                "detail": {
                    "route": "WAW-CDG",
                    "airport": {
                        "origin": {"code": {"iata": "WAW"}},
                        "destination": {"code": {"iata": "CDG"}},
                    },
                },
            }
        ]
    }
    mock_api.get_flight_details.return_value = {
        "airport": {
            "origin": {"code": {"iata": "WAW"}},
            "destination": {"code": {"iata": "CDG"}},
        }
    }

    cache = RouteCache(cache_file, mock_api)
    result = cache.lookup("RYR456")

    assert result["origin"] == "WAW"
    assert result["destination"] == "CDG"
    # Verify cache was persisted
    saved = json.loads(cache_file.read_text())
    assert "RYR456" in saved


def test_cache_miss_api_fails_returns_none(tmp_path: Path):
    """When FR24 lookup fails, return None and don't cache."""
    cache_file = tmp_path / "route_cache.json"
    cache_file.write_text(json.dumps({}))

    mock_api = MagicMock()
    mock_api.search.return_value = {}

    cache = RouteCache(cache_file, mock_api)
    result = cache.lookup("UNKN99")

    assert result is None
    saved = json.loads(cache_file.read_text())
    assert "UNKN99" not in saved
