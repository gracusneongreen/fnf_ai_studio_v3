"""FastAPI app: serves the preview page + the computer-use chat, on port 3000."""

from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

BASE = Path(__file__).resolve().parent
PREVIEW = Path(__file__).resolve().parents[1] / ".base44" / "preview"
OUTPUT = PREVIEW / "output"
os.makedirs(OUTPUT, exist_ok=True)

app = FastAPI(title="FNF-OMNI")


@app.get("/")
def index():
    return FileResponse(PREVIEW / "index.html")


@app.get("/chat")
def chat_page():
    return FileResponse(BASE / "static" / "chat.html")


app.mount("/output", StaticFiles(directory=OUTPUT), name="output")
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "computer_url": bool(os.getenv("COMPUTER_USE_URL")),
        "anthropic_key": os.getenv("ANTHROPIC_API_KEY", "") not in ("", "dev-placeholder"),
    }


@app.post("/api/chat")
async def chat_api(request: Request):
    body = await request.json()
    history = body.get("messages", [])

    async def stream():
        from .llm import run_agent
        try:
            async for ev in run_agent(history):
                yield f"data: {json.dumps(ev)}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as e:  # noqa: BLE001
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")
