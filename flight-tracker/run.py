#!/usr/bin/env python3
"""Flight tracker add-on entry point: polling loop + Ingress web server."""

import asyncio
import json
import logging
import os
import shutil
import time
from pathlib import Path

from aiohttp import web

from coverage_tracker import CoverageTracker
from flight_tracker import run_fr24_pipeline

OPTIONS_PATH = Path(os.environ.get("FLIGHT_TRACKER_DATA_DIR", "/data")) / "options.json"
STATIC_DIR = Path(os.environ.get("FLIGHT_TRACKER_STATIC_DIR", "/app/static"))
DATA_DIR = Path(os.environ.get("FLIGHT_TRACKER_DATA_DIR", "/data"))
COVERAGE_PATH = DATA_DIR / "coverage.csv"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("flight-tracker")


def load_options() -> dict:
    """Load add-on options from /data/options.json."""
    if OPTIONS_PATH.exists():
        return json.loads(OPTIONS_PATH.read_text())
    return {"poll_interval_seconds": 10}


def setup_static_files() -> None:
    """Copy static assets to /data/ so the web server can serve them alongside CSV."""
    for src in sorted(STATIC_DIR.iterdir()):
        if not src.is_file():
            continue
        dst = DATA_DIR / src.name
        shutil.copy2(src, dst)
        logger.info("Copied %s to %s", src, dst)


async def poll_loop(interval: int, coverage: CoverageTracker) -> None:
    """Run the FR24 pipeline on a fixed interval, crediting observed time on success."""
    logger.info("Starting polling loop (interval=%ds)", interval)
    last_ok: float | None = None
    while True:
        try:
            count = run_fr24_pipeline()
            logger.info("Poll complete. New flights: %d", count)
            now = time.monotonic()
            # Credit the time since the previous successful poll, capped so an
            # outage is never counted as observed.
            observed = interval if last_ok is None else min(now - last_ok, 2 * interval)
            last_ok = now
            coverage.record(observed)
            coverage.flush()
        except Exception:
            logger.exception("Polling failed")
        await asyncio.sleep(interval)


async def start_web_server() -> web.AppRunner:
    """Start an aiohttp static file server for /data/ on the Ingress port."""
    app = web.Application()

    async def index_handler(request: web.Request) -> web.FileResponse:
        return web.FileResponse(DATA_DIR / "dashboard.html")

    app.router.add_get("/", index_handler)
    app.router.add_static("/", DATA_DIR, show_index=False)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8099)
    await site.start()
    logger.info("Web server started on port 8099")
    return runner


async def main() -> None:
    options = load_options()
    interval = options.get("poll_interval_seconds", 10)

    # Ensure /data exists and copy static assets
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    setup_static_files()

    coverage = CoverageTracker(COVERAGE_PATH)

    # Start web server and polling loop concurrently
    runner = await start_web_server()
    try:
        await poll_loop(interval, coverage)
    finally:
        coverage.flush(force=True)
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
