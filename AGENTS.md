# Agent notes

- This repo is a Python **CLI** (no web app). The Base44 preview is a small static
  page at `.base44/preview/index.html` served by the `web` service on port 3000.
- The sandbox has **no GPU**, so the full diffusion render (`FNFOmniVideoV1Pipeline`,
  needs torch/diffusers + HF model downloads) is not run here. Only the torch-free
  paths run: `--sneak-peek` (PNG/GIF storyboard) and `--pose-preview` (MP4).
- `renderer` service installs only `opencv-python-headless`, numpy, Pillow and
  ffmpeg, then runs `.base44/preview/render_loop.sh`, which re-renders into
  `.base44/preview/output/` (gitignored) whenever a `.py`/`.json` file changes.
- OpenCV writes `mp4v`, which browsers can't play; the loop transcodes to H.264
  with ffmpeg for the preview page.
- Verify: `cat .base44/preview/output/status.txt` shows a timestamp (or "render failed");
  `docker compose -f docker-compose.base44.yml logs renderer` for errors.
- Tests (torch-free): `docker compose -f docker-compose.base44.yml exec -T renderer python -m unittest discover -s tests`
- No secrets are needed. Hugging Face auth is only relevant for the full GPU render.
