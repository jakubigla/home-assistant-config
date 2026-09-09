"""Poll-coverage tracker: records how many seconds each local date/hour was observed.

The dashboard needs to know which hours were actually watched so that an hour
with no flights because the add-on was offline is not mistaken for a quiet hour.
"""

from __future__ import annotations

import csv
import logging
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

HEADER = ["date", "hour", "seconds"]


class CoverageTracker:
    def __init__(self, path: Path, tz: str = "Europe/Warsaw", flush_interval_s: float = 60) -> None:
        self._path = path
        self._tz = ZoneInfo(tz)
        self._flush_interval = flush_interval_s
        self._counts: dict[tuple[str, int], int] = defaultdict(int)
        self._last_flush: datetime | None = None
        self._dirty = False
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        with self._path.open(newline="") as fh:
            for row in csv.DictReader(fh):
                try:
                    self._counts[(row["date"], int(row["hour"]))] += int(float(row["seconds"]))
                except (KeyError, TypeError, ValueError):
                    logger.warning("Skipping malformed coverage row: %r", row)

    def seconds(self, date: str, hour: int) -> int:
        return self._counts.get((date, hour), 0)

    def record(self, seconds: float, now: datetime | None = None) -> None:
        """Credit `seconds` of observation to the local date/hour of `now`."""
        local = (now or datetime.now(timezone.utc)).astimezone(self._tz)
        self._counts[(local.strftime("%Y-%m-%d"), local.hour)] += int(round(seconds))
        self._dirty = True

    def flush(self, force: bool = False, now: datetime | None = None) -> None:
        """Write the CSV if dirty and the rate limit allows (or `force`)."""
        if not self._dirty:
            return
        now = now or datetime.now(timezone.utc)
        if not force and self._last_flush is not None:
            if (now - self._last_flush).total_seconds() < self._flush_interval:
                return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        with tmp.open("w", newline="") as fh:
            writer = csv.writer(fh, lineterminator="\n")
            writer.writerow(HEADER)
            for (date, hour), secs in sorted(self._counts.items()):
                writer.writerow([date, hour, secs])
        os.replace(tmp, self._path)
        self._last_flush = now
        self._dirty = False
