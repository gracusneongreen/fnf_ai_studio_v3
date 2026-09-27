# FNF-REAL-DRAW V0.6 — REAL AI ANIMATOR

V0.6 adds the real image-to-image / pose-conditioning integration contract.

Goal:
User-owned PNG/sketch -> pose conditioning -> generated animation frames.

The implementation uses Diffusers pipelines when the selected model/backend supports
image-to-image and optional ControlNet/IP-Adapter capabilities. Model weights are
external and must be authorized for the user's use.

## Run

Set:
- FNF_IMAGE_MODEL
- optional FNF_CONTROLNET_MODEL
- FNF_DEVICE

Then:
python animate.py --input character.png --output output

If the selected model does not expose the required image/pose conditioning APIs,
the program reports a clear capability error instead of silently producing fake output.
