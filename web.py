
from __future__ import annotations

import copy
import datetime as dt
import ipaddress
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "data" / "state.json"
APP = ROOT / "app.py"
BACKUPS = ROOT / "data" / "backups"

app = FastAPI(title="Azure Network Lab Portal", version="0.2.0")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


def load_state() -> dict[str, Any]:
    if not STATE.exists():
        raise RuntimeError(f"State file not found: {STATE}")
    return json.loads(STATE.read_text(encoding="utf-8"))


def save_state(state: dict[str, Any]) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def run_cli(*args: str) -> str:
    result = subprocess.run(
        [sys.executable, str(APP), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    output = result.stdout
    if result.stderr:
        output += ("\n" if output else "") + result.stderr
    if result.returncode:
        raise RuntimeError(output.strip() or "CLI command failed")
    return output.strip()


def command(*parts: str) -> dict[str, Any]:
    try:
        return {"ok": True, "output": run_cli(*parts)}
    except Exception as exc:
        return {"ok": False, "output": str(exc)}


class RouteRequest(BaseModel):
    source: str
    destination: str


class CommandRequest(BaseModel):
    args: list[str]


class ResetRequest(BaseModel):
    confirm: bool


SHOW_TARGETS = {
    "vnet",
    "vpn",
    "bgp",
    "expressroute",
    "routes",
    "route-server",
    "nva",
    "route-server-peers",
    "nva-routes",
    "coexistence",
}


@app.get("/", response_class=HTMLResponse)
def index():
    return (ROOT / "templates" / "index.html").read_text(encoding="utf-8")


@app.get("/api/state")
def state():
    try:
        return load_state()
    except Exception as exc:
        raise HTTPException(500, str(exc))


@app.get("/api/show/{target}")
def show(target: str):
    if target not in SHOW_TARGETS:
        raise HTTPException(404, "Unknown show target")
    result = command("show", target)
    if not result["ok"]:
        raise HTTPException(500, result["output"])
    return result


@app.post("/api/cli")
def cli(req: CommandRequest):
    # The browser UI only sends commands from its own forms.
    # Keep a conservative allow-list of simulator resources/actions.
    allowed = {
        "group": {"create"},
        "vnet": {"create"},
        "subnet": {"create", "associate-nsg"},
        "peering": {"create"},
        "nsg": {"create"},
        "route": {"table-create", "create", "associate"},
        "vpn": {"gateway-create", "local-create", "connection-create"},
        "bgp": {"peer-create", "advertise", "learn"},
        "route-server": {"create", "peer-create"},
        "nva": {"create", "advertise"},
        "expressroute": {"create", "peer", "advertise"},
        "hybrid": {"create"},
        "wan": {"create", "hub-create"},
    }

    if len(req.args) < 2:
        raise HTTPException(400, "A resource and action are required")

    resource, action = req.args[0], req.args[1]
    if resource not in allowed or action not in allowed[resource]:
        raise HTTPException(400, "Command is not enabled in the web portal")

    result = command(*req.args)
    if not result["ok"]:
        raise HTTPException(400, result["output"])
    return result


@app.post("/api/route/simulate")
def route(req: RouteRequest):
    try:
        ipaddress.ip_address(req.source)
        ipaddress.ip_address(req.destination)
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    result = command(
        "route",
        "simulate",
        "--source",
        req.source,
        "--destination",
        req.destination,
    )
    if not result["ok"]:
        raise HTTPException(500, result["output"])
    return result


@app.post("/api/hybrid/route-simulate")
def hybrid_route(req: RouteRequest):
    try:
        ipaddress.ip_address(req.source)
        ipaddress.ip_address(req.destination)
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    result = command(
        "hybrid",
        "route-simulate",
        "--source",
        req.source,
        "--destination",
        req.destination,
    )
    if not result["ok"]:
        raise HTTPException(500, result["output"])
    return result


@app.post("/api/reset")
def reset(req: ResetRequest):
    if not req.confirm:
        raise HTTPException(400, "Reset confirmation required")

    state = load_state()

    BACKUPS.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = BACKUPS / f"state-{stamp}.json"
    shutil.copy2(STATE, backup)

    blank = copy.deepcopy(state)
    for key, value in list(blank.items()):
        if isinstance(value, dict):
            blank[key] = {}
        elif isinstance(value, list):
            blank[key] = []

    save_state(blank)

    return {
        "ok": True,
        "output": f"Lab reset to blank state. Backup: {backup.name}",
        "backup": backup.name,
    }
