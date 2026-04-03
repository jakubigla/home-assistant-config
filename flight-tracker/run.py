#!/usr/bin/env python3
"""Flight tracker add-on entry point: polling loop + Ingress web server."""

import asyncio
import json
import logging
import shutil
from pathlib import Path

from aiohttp import web

from flight_tracker import run_fr24_pipeline

OPTIONS_PATH = Path("/data/options.json")
STATIC_DIR = Path("/app/static")
DATA_DIR = Path("/data")

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
    for filename in ("dashboard.html", "airports.json", "airlines.json", "aircraft.json"):
        src = STATIC_DIR / filename
        dst = DATA_DIR / filename
        if src.exists():
            shutil.copy2(src, dst)
            logger.info("Copied %s to %s", src, dst)


async def poll_loop(interval: int) -> None:
    """Run the FR24 pipeline on a fixed interval."""
    logger.info("Starting polling loop (interval=%ds)", interval)
    while True:
        try:
            count = run_fr24_pipeline()
            logger.info("Poll complete. New flights: %d", count)
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

    # Start web server and polling loop concurrently
    runner = await start_web_server()
    try:
        await poll_loop(interval)
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
