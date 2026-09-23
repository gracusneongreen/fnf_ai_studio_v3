"""Loopback FastAPI bridge for configured desktop apps and OSWorld actions.

The bridge intentionally accepts app IDs and structured input only. It never
executes shell strings supplied by a client.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Optional

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from osworld_bridge import OSWorldBridge
from web_dashboard import ConnectedApps


class PointRequest(BaseModel):
    x: int = Field(ge=0)
    y: int = Field(ge=0)


class TypeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4096)
    interval: Optional[float] = Field(default=None, ge=0)


class HotkeyRequest(BaseModel):
    keys: list[str] = Field(min_length=1, max_length=8)


class LocalBridgeService:
    """Structured operations exposed by the local bridge."""

    def __init__(
        self,
        apps: Optional[ConnectedApps] = None,
        bridge: Optional[OSWorldBridge] = None,
    ) -> None:
        self.apps = apps or ConnectedApps()
        self.bridge = bridge or OSWorldBridge()

    def status(self) -> dict[str, Any]:
        return {"apps": self.apps.status(), "active_app": self.apps.active_app}

    def target(self, app_id: str) -> dict[str, Any]:
        try:
            return self.apps.target(app_id)
        except KeyError as exc:
            raise ValueError(str(exc)) from exc

    def launch(self, app_id: str) -> dict[str, Any]:
        try:
            return self.apps.launch(app_id)
        except (KeyError, RuntimeError) as exc:
            raise ValueError(str(exc)) from exc

    def move(self, request: PointRequest) -> dict[str, Any]:
        self.bridge.move_to(request.x, request.y)
        return {"x": request.x, "y": request.y}

    def click(self, request: PointRequest) -> dict[str, Any]:
        self.bridge.click(request.x, request.y)
        return {"x": request.x, "y": request.y}

    def type_text(self, request: TypeRequest) -> dict[str, Any]:
        self.bridge.type_text(request.text, interval=request.interval)
        return {"length": len(request.text)}

    def hotkey(self, request: HotkeyRequest) -> dict[str, Any]:
        self.bridge.hotkey(*request.keys)
        return {"keys": request.keys}

    def screenshot(self) -> dict[str, Any]:
        output = Path("outputs") / "local-bridge-screenshot.png"
        self.bridge.screenshot(output)
        return {"path": str(output)}


def create_app(service: Optional[LocalBridgeService] = None) -> FastAPI:
    """Create the localhost-only API application."""

    bridge_service = service or LocalBridgeService()
    app = FastAPI(
        title="FNF-OMNI-STUDIO-V2 Local Bridge",
        description="Structured local app and computer-use actions.",
        version="1.0.0",
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/status")
    def status() -> dict[str, Any]:
        return bridge_service.status()

    @app.post("/api/apps/{app_id}/target")
    def target(app_id: str) -> dict[str, Any]:
        try:
            return bridge_service.target(app_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/apps/{app_id}/launch")
    def launch(app_id: str) -> dict[str, Any]:
        try:
            return bridge_service.launch(app_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/input/move")
    def move(request: PointRequest) -> dict[str, Any]:
        return bridge_service.move(request)

    @app.post("/api/input/click")
    def click(request: PointRequest) -> dict[str, Any]:
        return bridge_service.click(request)

    @app.post("/api/input/type")
    def type_text(request: TypeRequest) -> dict[str, Any]:
        return bridge_service.type_text(request)

    @app.post("/api/input/hotkey")
    def hotkey(request: HotkeyRequest) -> dict[str, Any]:
        return bridge_service.hotkey(request)

    @app.post("/api/screenshot")
    def screenshot() -> dict[str, Any]:
        return bridge_service.screenshot()

    return app


app = create_app()


def run_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    import uvicorn

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    run_server(args.host, args.port)
