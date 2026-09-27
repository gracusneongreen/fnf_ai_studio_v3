# FNF-REAL-DRAW V0.9 — REAL POSE AI

Final motion stage: real video/image sequences can enter through a detector adapter, become temporal skeleton data, pass QC, and be retargeted to an original character rig.

Pipeline:
VIDEO/IMAGE SEQUENCE -> POSE DETECTOR -> CONFIDENCE FILTER -> TEMPORAL SMOOTHING -> BONE CONSTRAINTS -> RETARGET -> CHARACTER RENDER -> FRAME QC -> SPRITESHEET/XML

V0.9 keeps detector backends modular. It does not bundle model weights. A backend may be MediaPipe, OpenPose-compatible, RTMPose, or another authorized local detector.

Commands:
python cli.py detect <folder> <output.json>
python cli.py validate <sequence.json>
python cli.py retarget <sequence.json> <output.json>

The detector adapter contract is intentionally simple: each frame returns joints, confidence, width and height.

This version does not guarantee perfect human motion. Quality depends on source footage, detector accuracy, camera angle, occlusion, frame rate and the amount/diversity of authorized motion data.

Training/processing data must be licensed, user-owned, or otherwise authorized.
