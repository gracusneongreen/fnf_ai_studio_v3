"""HTTP client for the external computer-use desktop.

The agent operates a real desktop (where FNF Psych Engine and Krita are
installed) over a small HTTP API. This is compatible with the Anthropic
computer-use reference HTTP server (anthropic-quickstarts/computer-use-demo's
streamable HTTP server). Set COMPUTER_USE_URL to that server's base URL.

Endpoint contract (all POST, JSON in / JSON out):
  POST /screenshot            -> {"image_base64": "<png b64>"}
  POST /cursor_position       -> {"x": int, "y": int}
  POST /mouse_move            {"x","y"}
  POST /click                 {"x","y","button":"left|right|middle","count":1|2|3}
  POST /type                  {"text": str}
  POST /key                   {"key": str}            # e.g. "ctrl+s", "Return"
  POST /scroll                {"x","y","scroll_direction","scroll_amount"}
  POST /left_click_drag       {"start_x","start_y","x","y"}
"""

from __future__ import annotations

import httpx


class DesktopClient:
    def __init__(self, base_url: str, width: int = 1024, height: int = 768):
        self.base = base_url.rstrip("/")
        self.width = width
        self.height = height
        self.http = httpx.Client(timeout=30.0)

    def _post(self, path: str, body: dict | None = None) -> dict:
        r = self.http.post(f"{self.base}{path}", json=body or {})
        r.raise_for_status()
        try:
            return r.json()
        except ValueError:
            return {}

    def screenshot(self) -> str:
        d = self._post("/screenshot")
        return d.get("image_base64") or d.get("image") or ""

    def cursor_position(self) -> dict:
        return self._post("/cursor_position")

    def mouse_move(self, x: int, y: int) -> None:
        self._post("/mouse_move", {"x": x, "y": y})

    def click(self, x: int, y: int, button: str = "left", count: int = 1) -> None:
        self._post("/click", {"x": x, "y": y, "button": button, "count": count})

    def type_text(self, text: str) -> None:
        self._post("/type", {"text": text})

    def key(self, key: str) -> None:
        self._post("/key", {"key": key})

    def scroll(self, x: int, y: int, direction: str, amount: int) -> None:
        self._post("/scroll", {
            "x": x, "y": y,
            "scroll_direction": direction,
            "scroll_amount": amount,
        })

    def drag(self, sx: int, sy: int, x: int, y: int) -> None:
        self._post("/left_click_drag", {"start_x": sx, "start_y": sy, "x": x, "y": y})
