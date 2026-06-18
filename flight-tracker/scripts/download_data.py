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
import urllib.error
import urllib.request
from pathlib import Path

import websockets

ADDON_SLUG = "14caed58_flight-tracker"
OUTPUT_PATH = Path("flight-tracker/data/flights.csv")
HTTP_TIMEOUT = 30  # seconds


async def _ws_command(ws: websockets.ClientConnection, payload: dict) -> dict:
    """Send a WS command and return its `result`. Raises on a non-success reply."""
    await ws.send(json.dumps(payload))
    reply = json.loads(await ws.recv())
    if not reply.get("success", False):
        error = reply.get("error", reply)
        raise RuntimeError(f"WS command {payload.get('endpoint', payload)} failed: {error}")
    return reply["result"]


async def fetch_ingress(ws_url: str, token: str) -> tuple[str, str]:
    """Authenticate, open an ingress session, and resolve the addon ingress path."""
    async with websockets.connect(ws_url) as ws:
        await ws.recv()  # auth_required
        await ws.send(json.dumps({"type": "auth", "access_token": token}))
        auth = json.loads(await ws.recv())
        if auth.get("type") != "auth_ok":
            raise RuntimeError(f"WS auth failed: {auth.get('message', auth)}")

        session = await _ws_command(ws, {
            "id": 1,
            "type": "supervisor/api",
            "endpoint": "/ingress/session",
            "method": "post",
        })
        info = await _ws_command(ws, {
            "id": 2,
            "type": "supervisor/api",
            "endpoint": f"/addons/{ADDON_SLUG}/info",
            "method": "get",
        })
        return session["session"], info["ingress_entry"]


async def main() -> None:
    try:
        ws_url = os.environ["HA_WS"]
        token = os.environ["HA_TOKEN"]
        ha_url = os.environ["HA_URL"]
    except KeyError as exc:
        sys.exit(f"missing env var: {exc.args[0]}")

    session, ingress = await fetch_ingress(ws_url, token)

    req = urllib.request.Request(f"{ha_url}{ingress}/flights.csv")
    req.add_header("Cookie", f"ingress_session={session}")
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            data = resp.read()
    except urllib.error.URLError as exc:
        sys.exit(f"failed to download flights.csv: {exc}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_bytes(data)
    line_count = data.count(b"\n")
    print(f"Downloaded to {OUTPUT_PATH} ({line_count} lines)")


if __name__ == "__main__":
    asyncio.run(main())
