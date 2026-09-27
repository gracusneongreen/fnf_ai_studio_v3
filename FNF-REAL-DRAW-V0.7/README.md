# FNF-REAL-DRAW V0.7 — REAL MOTION PIPELINE

V0.7 adds a sequence-first human-motion pipeline to the V0.6 AI draw/animate foundation.

## Goals
- LM Studio and vLLM through OpenAI-compatible local endpoints.
- Provider/model selection from .env and CLI.
- Human motion represented as temporal skeleton/keypoint sequences, not isolated images.
- Character-lock metadata so identity, proportions, outfit and palette stay stable.
- Interpolation and motion constraints for smoother movement.
- Dataset schemas for licensed, user-owned, or otherwise authorized motion references.
- Export contracts for spritesheet, Sparrow XML and Psych Engine.

This is an engineering pipeline and dataset contract. It does not ship model weights or claim perfect human-motion generation.

## Quick start
1. Copy .env.example to .env.
2. Install requirements: python -m pip install -r requirements.txt
3. List configured local models: python cli.py models
4. Run chat: python cli.py chat
5. Inspect a motion JSON: python cli.py motion path/to/sequence.json

Typical local endpoints:
- LM Studio: http://localhost:1234/v1
- vLLM: http://localhost:8000/v1

These are defaults only; configure the actual endpoint in .env.

## Motion pipeline
reference frames -> pose/keypoints -> temporal sequence -> constraints -> interpolation -> character rig -> render -> QC -> engine export

FNF animation names such as idle and singLEFT are treated as technical animation labels only. Do not use copyrighted artwork as training data unless you have the required rights.
