import pandas as pd
from pathlib import Path
from flight_tracker import _format_and_append, CSV_COLUMNS, CSV_PATH


def test_csv_columns_include_enrichment_fields():
    """CSV_COLUMNS list includes all 7 new enrichment columns."""
    expected_new = [
        "aircraft_type", "airline_icao", "airline_iata",
        "registration", "flight_number", "velocity_kts",
        "vertical_speed_fpm",
    ]
    for col in expected_new:
        assert col in CSV_COLUMNS, f"Missing column: {col}"


def test_format_and_append_writes_enrichment_columns(tmp_path, monkeypatch):
    """_format_and_append includes enrichment columns in output CSV."""
    csv_path = tmp_path / "flights.csv"
    monkeypatch.setattr("flight_tracker.CSV_PATH", csv_path)
    monkeypatch.setattr("flight_tracker.DATA_DIR", tmp_path)

    flights = pd.DataFrame([{
        "icao24": "4B1812",
        "callsign": "LOT3825",
        "time": 1712170000,
        "lat": 52.247,
        "lon": 20.836,
        "baroaltitude": 1485.9,  # ~4875 ft
        "heading": 318.0,
        "velocity": 143.0,
        "origin": "WAW",
        "destination": "GDN",
        "aircraft_type": "B738",
        "airline_icao": "LOT",
        "airline_iata": "LO",
        "registration": "SP-LWG",
        "flight_number": "LO3825",
        "velocity_kts": 280,
        "vertical_speed_fpm": 1472,
    }])

    count = _format_and_append(flights)
    assert count == 1

    result = pd.read_csv(csv_path)
    assert result.iloc[0]["aircraft_type"] == "B738"
    assert result.iloc[0]["airline_icao"] == "LOT"
    assert result.iloc[0]["airline_iata"] == "LO"
    assert result.iloc[0]["registration"] == "SP-LWG"
    assert result.iloc[0]["flight_number"] == "LO3825"
    assert result.iloc[0]["velocity_kts"] == 280
    assert result.iloc[0]["vertical_speed_fpm"] == 1472


def test_format_and_append_handles_missing_enrichment(tmp_path, monkeypatch):
    """Old-style flights without enrichment columns get NaN/empty values."""
    csv_path = tmp_path / "flights.csv"
    monkeypatch.setattr("flight_tracker.CSV_PATH", csv_path)
    monkeypatch.setattr("flight_tracker.DATA_DIR", tmp_path)

    flights = pd.DataFrame([{
        "icao24": "4B1812",
        "callsign": "LOT3825",
        "time": 1712170000,
        "lat": 52.247,
        "lon": 20.836,
        "baroaltitude": 1485.9,
        "heading": 318.0,
        "velocity": 143.0,
        "origin": "WAW",
        "destination": "GDN",
        # No enrichment fields — simulates OpenSky source
    }])

    count = _format_and_append(flights)
    assert count == 1

    result = pd.read_csv(csv_path)
    assert len(result) == 1
    # Enrichment columns should exist but be empty/NaN
    assert pd.isna(result.iloc[0]["aircraft_type"]) or result.iloc[0]["aircraft_type"] == ""
