# FNF-REAL-DRAW V0.8 — MOTION DATASET + POSE EXTRACTION

V0.8 turns motion references into structured temporal pose data.

Pipeline:
video/images -> frame extraction -> pose backend -> normalized skeleton JSON -> sequence validation -> interpolation/refinement -> character retargeting

Supported backend contracts:
- MediaPipe adapter contract
- OpenPose-compatible adapter contract
- JSON/manual pose import
- future RTMPose/custom adapters

V0.8 does not bundle model weights. Add only datasets and references you are licensed or authorized to process.

Quick start:
python cli.py inspect path/to/sequence.json
python cli.py normalize path/to/sequence.json output.json
