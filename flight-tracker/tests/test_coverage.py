"""Tests for the poll-coverage tracker."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from coverage_tracker import CoverageTracker


@pytest.fixture
def path(tmp_path: Path) -> Path:
    return tmp_path / "coverage.csv"


def test_record_buckets_by_local_date_and_hour(path: Path) -> None:
    tracker = CoverageTracker(path, tz="Europe/Warsaw", flush_interval_s=0)
    # 21:30 UTC on Sep 9 is 23:30 CEST on Sep 9; 22:30 UTC is 00:30 CEST on Sep 10
    tracker.record(10, now=datetime(2026, 9, 9, 21, 30, tzinfo=timezone.utc))
    tracker.record(10, now=datetime(2026, 9, 9, 21, 31, tzinfo=timezone.utc))
    tracker.record(10, now=datetime(2026, 9, 9, 22, 30, tzinfo=timezone.utc))

    assert tracker.seconds("2026-09-09", 23) == 20
    assert tracker.seconds("2026-09-10", 0) == 10
    assert tracker.seconds("2026-09-10", 1) == 0


def test_flush_writes_csv_sorted(path: Path) -> None:
    tracker = CoverageTracker(path, tz="Europe/Warsaw", flush_interval_s=0)
    tracker.record(10, now=datetime(2026, 9, 10, 8, 0, tzinfo=timezone.utc))
    tracker.record(5, now=datetime(2026, 9, 9, 8, 0, tzinfo=timezone.utc))
    tracker.flush(force=True)

    assert path.read_text().splitlines() == [
        "date,hour,seconds",
        "2026-09-09,10,5",
        "2026-09-10,10,10",
    ]


def test_load_merges_with_existing_file(path: Path) -> None:
    path.write_text("date,hour,seconds\n2026-09-09,10,100\n")
    tracker = CoverageTracker(path, tz="Europe/Warsaw", flush_interval_s=0)
    tracker.record(10, now=datetime(2026, 9, 9, 8, 0, tzinfo=timezone.utc))
    tracker.flush(force=True)

    assert path.read_text().splitlines() == ["date,hour,seconds", "2026-09-09,10,110"]


def test_load_survives_corrupt_rows(path: Path) -> None:
    path.write_text("date,hour,seconds\n2026-09-09,10,100\ngarbage\n2026-09-09,xx,5\n")
    tracker = CoverageTracker(path, tz="Europe/Warsaw", flush_interval_s=0)
    assert tracker.seconds("2026-09-09", 10) == 100


def test_flush_is_rate_limited(path: Path) -> None:
    tracker = CoverageTracker(path, tz="Europe/Warsaw", flush_interval_s=60)
    t0 = datetime(2026, 9, 9, 8, 0, tzinfo=timezone.utc)
    tracker.record(10, now=t0)
    tracker.flush(now=t0)
    assert path.exists()  # first flush always writes
    tracker.record(10, now=t0.replace(minute=0, second=30))
    tracker.flush(now=t0.replace(minute=0, second=30))
    assert path.read_text().splitlines()[1] == "2026-09-09,10,10"  # not yet rewritten
    tracker.flush(now=t0.replace(minute=1, second=1))
    assert path.read_text().splitlines()[1] == "2026-09-09,10,20"
