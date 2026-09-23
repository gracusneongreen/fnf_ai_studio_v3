# Agent notes

- This repo is a Python **CLI** (no web app). The Base44 preview is served by a
  FastAPI app (`agent/app.py`) on port 3000:
  - `/` — torch-free render previews (storyboard PNG/GIF + pose-guide MP4).
  - `/chat` — computer-use agent chat page (see below).
- The sandbox has **no GPU**, so the full diffusion render (`FNFOmniVideoV1Pipeline`,
  needs torch/diffusers + HF model downloads) is not run here. Only the torch-free
  paths run: `--sneak-peek` (PNG/GIF storyboard) and `--pose-preview` (MP4).
- `renderer` service installs only `opencv-python-headless`, numpy, Pillow and
  ffmpeg, then runs `.base44/preview/render_loop.sh`, which re-renders into
  `.base44/preview/output/` (gitignored) whenever a `.py`/`.json` file changes.
- `web` service installs `agent/requirements.txt` (fastapi/uvicorn/anthropic/httpx)
  and runs `uvicorn agent.app:app --reload`.
- OpenCV writes `mp4v`, which browsers can't play; the loop transcodes to H.264
  with ffmpeg for the preview page.

## Computer-use agent (`/chat`)
- A real Anthropic computer-use loop (`agent/llm.py`) drives the
  `computer_20250124` tool against an **external desktop** (`agent/computer.py`,
  HTTP client) where FNF Psych Engine and Krita are installed.
- "Eyes" = live screenshots streamed into the chat; "hands" = action log of
  clicks/types/keys. The system prompt (`agent/fnf_knowledge.py`) encodes FNF
  anatomy, Psych Engine, and Krita knowledge.
- Needs two secrets (set via Base44 secrets → `/run/base44/app.env`):
  - `ANTHROPIC_API_KEY` — Anthropic API key (console.anthropic.com → API Keys).
  - `COMPUTER_USE_URL` — base URL of your computer-use desktop HTTP server
    (compatible with Anthropic's computer-use-demo streamable HTTP server).
  The app boots without them (placeholders in `.env.base44-defaults`); the chat
  shows a clear error until both are set.

## Verify
- Renders: `cat .base44/preview/output/status.txt` (timestamp or "render failed");
  `docker compose -f docker-compose.base44.yml logs renderer` for errors.
- Agent health: `curl -s localhost:3000/api/health`.
- Tests (torch-free): `docker compose -f docker-compose.base44.yml exec -T renderer python -m unittest discover -s tests`
- Hugging Face auth is only relevant for the full GPU render (not run here).
