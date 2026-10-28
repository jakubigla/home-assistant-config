#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["websockets>=13"]
# ///
"""Read-only Home Assistant client for the autonomous review agents.

Only GETs, template rendering and an allowlist of read-only WebSocket commands are
possible. There is deliberately no way to call a service, fire an event or write
config through this tool.

Usage:
  ha_ro.py get /api/states/sensor.foo
  ha_ro.py errorlog [--tail N]
  ha_ro.py template '{{ states("sensor.foo") }}'
  ha_ro.py ws trace/list '{"domain": "automation"}'
  ha_ro.py ws logbook/get_events '{"start_time": "...", "end_time": "..."}'
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

from websockets.sync.client import connect

# WebSocket command types that only read state.
WS_ALLOWED = {
    "get_states",
    "get_config",
    "get_services",
    "config/entity_registry/list",
    "config/device_registry/list",
    "config/area_registry/list",
    "config/floor_registry/list",
    "config/label_registry/list",
    "trace/list",
    "trace/get",
    "logbook/get_events",
    "history/history_during_period",
    "history/stream",
    "recorder/statistics_during_period",
    "recorder/list_statistic_ids",
    "system_log/list",
    "repairs/list_issues",
    "persistent_notification/get",
    "lovelace/config",
    "automation/config",
    "script/config",
    "config/auth/list",
    "supervisor/api",
}
# supervisor/api is a passthrough; only these read endpoints are allowed through it.
SUPERVISOR_READ_ENDPOINTS = (
    "/addons",
    "/supervisor/info",
    "/supervisor/stats",
    "/core/info",
    "/core/stats",
    "/host/info",
    "/os/info",
    "/resolution/info",
    "/store",
)


def _env() -> tuple[str, str]:
    url = os.environ.get("HA_URL", "").rstrip("/")
    token = os.environ.get("API_ACCESS_TOKEN") or os.environ.get("HA_TOKEN", "")
    if not url or not token:
        sys.exit("HA_URL / API_ACCESS_TOKEN not set")
    return url, token


def _request(method: str, path: str, body: bytes | None = None) -> bytes:
    url, token = _env()
    req = urllib.request.Request(
        url + path,
        data=body,
        method=method,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
        return resp.read()


def cmd_get(args: argparse.Namespace) -> None:
    if not args.path.startswith("/api/"):
        sys.exit("path must start with /api/")
    if args.path.startswith(("/api/services", "/api/events")) and args.path.count("/") > 2:
        sys.exit("service/event endpoints are blocked")
    sys.stdout.buffer.write(_request("GET", args.path))


def cmd_errorlog(args: argparse.Namespace) -> None:
    try:
        text = _request("GET", "/api/error_log").decode(errors="replace")
    except urllib.error.HTTPError as err:
        if err.code != 404:
            raise
        # No file-based core log on HA OS; fall back to the structured system log.
        args.type, args.json = "system_log/list", None
        return cmd_ws(args)
    print("\n".join(text.splitlines()[-args.tail :]))


def cmd_template(args: argparse.Namespace) -> None:
    sys.stdout.buffer.write(
        _request("POST", "/api/template", json.dumps({"template": args.template}).encode())
    )


def cmd_ws(args: argparse.Namespace) -> None:
    if args.type not in WS_ALLOWED:
        sys.exit(f"ws type {args.type!r} not allowed; allowed: {sorted(WS_ALLOWED)}")
    payload = json.loads(args.json) if args.json else {}
    if args.type == "supervisor/api":
        endpoint = payload.get("endpoint", "")
        if payload.get("method", "get").lower() != "get" or not endpoint.startswith(
            SUPERVISOR_READ_ENDPOINTS
        ):
            sys.exit("supervisor/api limited to GET on read endpoints")
    url, token = _env()
    ws_url = url.replace("http", "ws", 1) + "/api/websocket"
    with connect(ws_url, max_size=None) as ws:
        ws.recv()  # auth_required
        ws.send(json.dumps({"type": "auth", "access_token": token}))
        if json.loads(ws.recv()).get("type") != "auth_ok":
            sys.exit("auth failed")
        ws.send(json.dumps({"id": 1, "type": args.type, **payload}))
        while True:
            msg = json.loads(ws.recv())
            if msg.get("id") != 1:
                continue
            if msg.get("type") == "result":
                if not msg.get("success"):
                    sys.exit(json.dumps(msg.get("error")))
                json.dump(msg.get("result"), sys.stdout)
                return
            if msg.get("type") == "event":  # history/stream: first event holds the data
                json.dump(msg.get("event"), sys.stdout)
                return


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("get")
    p.add_argument("path")
    p.set_defaults(fn=cmd_get)
    p = sub.add_parser("errorlog")
    p.add_argument("--tail", type=int, default=300)
    p.set_defaults(fn=cmd_errorlog)
    p = sub.add_parser("template")
    p.add_argument("template")
    p.set_defaults(fn=cmd_template)
    p = sub.add_parser("ws")
    p.add_argument("type")
    p.add_argument("json", nargs="?")
    p.set_defaults(fn=cmd_ws)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
