"""Anthropic computer-use agent loop.

Runs the computer_20250124 tool against an external desktop (DesktopClient),
streaming events (text, actions, screenshots) back to the chat UI.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from typing import AsyncGenerator

from anthropic import Anthropic

from .computer import DesktopClient
from .fnf_knowledge import SYSTEM_PROMPT


def _block_to_dict(b) -> dict:
    if b.type == "text":
        return {"type": "text", "text": b.text}
    if b.type == "tool_use":
        return {"type": "tool_use", "id": b.id, "name": b.name, "input": b.input}
    return {"type": b.type}


def _img_content(image_b64: str) -> list:
    return [{"type": "image", "source": {
        "type": "base64", "media_type": "image/png", "data": image_b64,
    }}]


def _handle_action(desktop: DesktopClient, inp: dict) -> tuple[list, str | None]:
    """Execute one computer action. Returns (tool_result_content, screenshot_b64)."""
    action = inp.get("action")
    coord = inp.get("coordinate")
    x, y = (coord[0], coord[1]) if coord else (None, None)

    if action == "screenshot":
        img = desktop.screenshot()
        return _img_content(img), img
    if action == "cursor_position":
        pos = desktop.cursor_position()
        return [{"type": "text", "text": json.dumps(pos)}], None
    if action == "mouse_move":
        desktop.mouse_move(x, y)
        img = desktop.screenshot()
        return _img_content(img), img
    if action in ("left_click", "right_click", "middle_click",
                  "double_click", "triple_click"):
        button = action.replace("_click", "")
        count = {"double_click": 2, "triple_click": 3}.get(action, 1)
        desktop.click(x, y, button, count)
        img = desktop.screenshot()
        return _img_content(img), img
    if action == "left_click_drag":
        sc = inp.get("start_coordinate", [0, 0])
        desktop.drag(sc[0], sc[1], x, y)
        img = desktop.screenshot()
        return _img_content(img), img
    if action == "type":
        desktop.type_text(inp.get("text", ""))
        img = desktop.screenshot()
        return _img_content(img), img
    if action == "key":
        desktop.key(inp.get("key", ""))
        img = desktop.screenshot()
        return _img_content(img), img
    if action == "scroll":
        desktop.scroll(x, y, inp.get("scroll_direction", "down"),
                       int(inp.get("scroll_amount", 1)))
        img = desktop.screenshot()
        return _img_content(img), img
    if action == "wait":
        duration = inp.get("duration") or inp.get("text") or 1
        time.sleep(float(duration))
        img = desktop.screenshot()
        return _img_content(img), img
    # Unknown action: return current screen so the model can recover.
    img = desktop.screenshot()
    return _img_content(img), img


async def run_agent(history: list) -> AsyncGenerator[dict, None]:
    key = os.getenv("ANTHROPIC_API_KEY", "")
    url = os.getenv("COMPUTER_USE_URL", "")
    if not key or key == "dev-placeholder":
        yield {"type": "error",
               "message": "ANTHROPIC_API_KEY is not set. Add it in your Base44 "
                          "secrets (console.anthropic.com -> API Keys)."}
        return
    if not url:
        yield {"type": "error",
               "message": "COMPUTER_USE_URL is not set. Point it at your "
                          "computer-use desktop server where FNF Psych Engine "
                          "and Krita are running."}
        return

    width = int(os.getenv("COMPUTER_DISPLAY_WIDTH", "1024"))
    height = int(os.getenv("COMPUTER_DISPLAY_HEIGHT", "768"))
    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
    desktop = DesktopClient(url, width, height)
    client = Anthropic()
    tools = [{
        "type": "computer_20250124", "name": "computer",
        "display_width_px": width, "display_height_px": height,
        "display_number": 1,
    }]
    messages = [dict(m) for m in history]

    while True:
        resp = await asyncio.to_thread(
            client.beta.messages.create,
            model=model, max_tokens=4096, tools=tools,
            system=SYSTEM_PROMPT, messages=messages,
            betas=["computer-use-2025-01-24"],
        )
        messages.append({"role": "assistant",
                         "content": [_block_to_dict(b) for b in resp.content]})

        for b in resp.content:
            if b.type == "text" and b.text.strip():
                yield {"type": "text", "text": b.text}

        if resp.stop_reason == "end_turn":
            return

        tool_results = []
        for b in resp.content:
            if b.type == "tool_use" and b.name == "computer":
                yield {"type": "action", "action": b.input.get("action"),
                       "input": b.input}
                try:
                    content, img = await asyncio.to_thread(_handle_action,
                                                           desktop, b.input)
                    if img:
                        yield {"type": "screenshot", "image": img}
                except Exception as e:  # noqa: BLE001
                    content = [{"type": "text", "text": f"action failed: {e}"}]
                    yield {"type": "error", "message": f"{e}"}
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": b.id,
                    "content": content,
                })

        if not tool_results:
            return
        messages.append({"role": "user", "content": tool_results})
