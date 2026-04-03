import pandas as pd
from pathlib import Path
from flight_tracker import _format_and_append, CSV_COLUMNS


def test_enriched_csv_round_trip(tmp_path, monkeypatch):
    """Full round-trip: enriched DataFrame → CSV → read back with all columns."""
    csv_path = tmp_path / "flights.csv"
    monkeypatch.setattr("flight_tracker.CSV_PATH", csv_path)
    monkeypatch.setattr("flight_tracker.DATA_DIR", tmp_path)

    flights = pd.DataFrame([
        {
            "icao24": "4B1812", "callsign": "LOT3825", "time": 1712170000,
            "lat": 52.247, "lon": 20.836, "baroaltitude": 1485.9,
            "heading": 318.0, "velocity": 143.0,
            "origin": "WAW", "destination": "GDN",
            "aircraft_type": "B738", "airline_icao": "LOT", "airline_iata": "LO",
            "registration": "SP-LWG", "flight_number": "LO3825",
            "velocity_kts": 280, "vertical_speed_fpm": 1472,
        },
        {
            "icao24": "AABBCC", "callsign": "RYR8HU", "time": 1712173600,
            "lat": 52.250, "lon": 20.840, "baroaltitude": 2232.6,
            "heading": 312.0, "velocity": 220.0,
            "origin": "WAW", "destination": "VIE",
            "aircraft_type": "A320", "airline_icao": "LDA", "airline_iata": "FR",
            "registration": "9H-LMG", "flight_number": "FR6065",
            "velocity_kts": 428, "vertical_speed_fpm": -640,
        },
    ])

    count = _format_and_append(flights)
    assert count == 2

    result = pd.read_csv(csv_path)
    assert list(result.columns) == CSV_COLUMNS
    assert len(result) == 2

    # Verify enrichment data persisted
    lot = result[result["callsign"] == "LOT3825"].iloc[0]
    assert lot["aircraft_type"] == "B738"
    assert lot["airline_icao"] == "LOT"
    assert lot["registration"] == "SP-LWG"
    assert lot["velocity_kts"] == 280
    assert lot["vertical_speed_fpm"] == 1472

    ryr = result[result["callsign"] == "RYR8HU"].iloc[0]
    assert ryr["aircraft_type"] == "A320"
    assert ryr["airline_icao"] == "LDA"
    assert ryr["vertical_speed_fpm"] == -640


def test_mixed_enriched_and_legacy_csv(tmp_path, monkeypatch):
    """Appending enriched flights to a legacy CSV (without new columns) works."""
    csv_path = tmp_path / "flights.csv"
    monkeypatch.setattr("flight_tracker.CSV_PATH", csv_path)
    monkeypatch.setattr("flight_tracker.DATA_DIR", tmp_path)

    # Write a legacy-format CSV first (missing enrichment columns)
    legacy = pd.DataFrame([{
        "date": "2026-04-01", "time_utc": "10:00:00", "time_local": "12:00:00",
        "callsign": "OLD123", "altitude_ft": 5000, "heading_deg": 270,
        "origin": "WAW", "destination": "LHR", "distance_from_home_km": 0.5,
    }])
    legacy.to_csv(csv_path, index=False)

    # Now append an enriched flight
    flights = pd.DataFrame([{
        "icao24": "NEWONE", "callsign": "NEW456", "time": 1712170000,
        "lat": 52.247, "lon": 20.836, "baroaltitude": 1829.0,
        "heading": 300.0, "velocity": 150.0,
        "origin": "WAW", "destination": "CDG",
        "aircraft_type": "A321", "airline_icao": "AFR", "airline_iata": "AF",
        "registration": "F-GKXS", "flight_number": "AF1145",
        "velocity_kts": 292, "vertical_speed_fpm": 800,
    }])

    _format_and_append(flights)
    result = pd.read_csv(csv_path)
    assert len(result) == 2

    # Legacy row should have NaN/empty enrichment fields
    old = result[result["callsign"] == "OLD123"].iloc[0]
    assert pd.isna(old["aircraft_type"]) or old["aircraft_type"] == ""

    # New row should have enrichment fields
    new = result[result["callsign"] == "NEW456"].iloc[0]
    assert new["aircraft_type"] == "A321"
    assert new["registration"] == "F-GKXS"
