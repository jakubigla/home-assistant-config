import pandas as pd
from processing import collapse_to_flights

HOME_LAT = 52.176
HOME_LON = 20.842


def test_collapse_picks_closest_point():
    """Given multiple state vectors for one flight, pick the one closest to home."""
    df = pd.DataFrame(
        {
            "icao24": ["abc123", "abc123", "abc123"],
            "callsign": ["LOT123", "LOT123", "LOT123"],
            "time": [1000, 1010, 1020],
            "lat": [52.170, 52.176, 52.180],
            "lon": [20.830, 20.842, 20.860],
            "baroaltitude": [3000.0, 2800.0, 2600.0],
            "heading": [270.0, 270.0, 270.0],
            "velocity": [80.0, 80.0, 80.0],
        }
    )
    result = collapse_to_flights(df, HOME_LAT, HOME_LON)
    assert len(result) == 1
    row = result.iloc[0]
    assert row["callsign"] == "LOT123"
    # Should pick the middle point (closest to home)
    assert row["time"] == 1010
    assert row["baroaltitude"] == 2800.0


def test_collapse_multiple_flights():
    """Two different flights produce two rows."""
    df = pd.DataFrame(
        {
            "icao24": ["abc123", "def456"],
            "callsign": ["LOT123", "RYR456"],
            "time": [1000, 1000],
            "lat": [52.176, 52.176],
            "lon": [20.842, 20.842],
            "baroaltitude": [3000.0, 10000.0],
            "heading": [270.0, 90.0],
            "velocity": [80.0, 230.0],
        }
    )
    result = collapse_to_flights(df, HOME_LAT, HOME_LON)
    assert len(result) == 2
    callsigns = set(result["callsign"])
    assert callsigns == {"LOT123", "RYR456"}


def test_collapse_empty_dataframe():
    """Empty input produces empty output."""
    df = pd.DataFrame(
        columns=["icao24", "callsign", "time", "lat", "lon", "baroaltitude", "heading", "velocity"]
    )
    result = collapse_to_flights(df, HOME_LAT, HOME_LON)
    assert len(result) == 0
