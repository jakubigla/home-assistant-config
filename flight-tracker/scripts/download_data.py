#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "websockets>=13",
# ]
# ///
"""Download flights.csv from the HA flight-tracker add-on via ingress proxy."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import urllib.request
from pathlib import Path

import websockets

ADDON_SLUG = "14caed58_flight-tracker"
OUTPUT_PATH = Path("flight-tracker/data/flights.csv")


async def main() -> None:
    try:
        ws_url = os.environ["HA_WS"]
        token = os.environ["HA_TOKEN"]
        ha_url = os.environ["HA_URL"]
    except KeyError as exc:
        sys.exit(f"missing env var: {exc.args[0]}")

    async with websockets.connect(ws_url) as ws:
        await ws.recv()
        await ws.send(json.dumps({"type": "auth", "access_token": token}))
        await ws.recv()

        await ws.send(json.dumps({
            "id": 1,
            "type": "supervisor/api",
            "endpoint": "/ingress/session",
            "method": "post",
        }))
        session = json.loads(await ws.recv())["result"]["session"]

        await ws.send(json.dumps({
            "id": 2,
            "type": "supervisor/api",
            "endpoint": f"/addons/{ADDON_SLUG}/info",
            "method": "get",
        }))
        ingress = json.loads(await ws.recv())["result"]["ingress_entry"]

    req = urllib.request.Request(f"{ha_url}{ingress}/flights.csv")
    req.add_header("Cookie", f"ingress_session={session}")
    data = urllib.request.urlopen(req).read()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_bytes(data)
    print(f"Downloaded to {OUTPUT_PATH} ({data.decode().count(chr(10))} lines)")


if __name__ == "__main__":
    asyncio.run(main())
