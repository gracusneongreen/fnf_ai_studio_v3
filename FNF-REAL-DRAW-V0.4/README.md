# FNF-REAL-DRAW V0.4 — REAL IMAGE BACKEND

V0.4 turns the V0.3 orchestration layer into a runnable image-generation backend.

## Architecture

Chat AI -> structured job -> image backend -> identity/pose set -> PNG -> export.

The backend uses the Hugging Face Diffusers ecosystem through a configurable model ID.
No model weights are committed to Git.

## Quick start

1. Install Python 3.10+.
2. Install dependencies from requirements.txt.
3. Set FNF_IMAGE_MODEL to a model you are licensed/authorized to use.
4. Run:

python generate.py --prompt "original dark corruption rhythm-game character" --output output

For GPU inference, install the PyTorch build appropriate for your CUDA environment.

## Important

This project does not ship Boyfriend artwork or model weights. BF remains an animation/schema reference.
Use only user-owned, licensed, public-domain, or otherwise authorized training/reference data.
