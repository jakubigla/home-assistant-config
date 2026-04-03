import pandas as pd
from unittest.mock import MagicMock, patch


def _make_mock_flight(**overrides):
    """Create a mock FR24 Flight object with default values."""
    defaults = {
        "icao_24bit": "4B1812",
        "callsign": "LOT3825",
        "latitude": 52.247,
        "longitude": 20.836,
        "altitude": 4875,
        "heading": 318,
        "ground_speed": 280,
        "on_ground": 0,
        "origin_airport_iata": "WAW",
        "destination_airport_iata": "GDN",
        "aircraft_code": "B738",
        "airline_icao": "LOT",
        "airline_iata": "LO",
        "registration": "SP-LWG",
        "number": "LO3825",
        "vertical_speed": 1472,
    }
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


def test_fetch_live_flights_includes_enrichment_fields():
    """fetch_live_flights returns new enrichment columns."""
    mock_flight = _make_mock_flight()

    with patch("FlightRadar24.FlightRadar24API") as MockAPI:
        MockAPI.return_value.get_flights.return_value = [mock_flight]
        from fr24_client import fetch_live_flights

        df = fetch_live_flights(52.0, 52.5, 20.5, 21.0)

    assert len(df) == 1
    row = df.iloc[0]
    assert row["aircraft_type"] == "B738"
    assert row["airline_icao"] == "LOT"
    assert row["airline_iata"] == "LO"
    assert row["registration"] == "SP-LWG"
    assert row["flight_number"] == "LO3825"
    assert row["velocity_kts"] == 280
    assert row["vertical_speed_fpm"] == 1472


def test_fetch_live_flights_handles_missing_enrichment_fields():
    """Missing enrichment fields default to empty string or None."""
    mock_flight = _make_mock_flight(
        aircraft_code="",
        airline_icao="",
        airline_iata="",
        registration="",
        number="",
        ground_speed=0,
        vertical_speed=0,
    )

    with patch("FlightRadar24.FlightRadar24API") as MockAPI:
        MockAPI.return_value.get_flights.return_value = [mock_flight]
        from fr24_client import fetch_live_flights

        df = fetch_live_flights(52.0, 52.5, 20.5, 21.0)

    assert len(df) == 1
    row = df.iloc[0]
    assert row["aircraft_type"] == ""
    assert row["airline_icao"] == ""
    assert row["registration"] == ""
    assert row["flight_number"] == ""
    assert row["airline_iata"] == ""
    assert row["velocity_kts"] is None
    assert row["vertical_speed_fpm"] is None
