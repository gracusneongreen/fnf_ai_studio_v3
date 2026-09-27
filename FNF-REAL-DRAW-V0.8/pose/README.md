# Pose extraction adapters

The project uses an adapter contract so you can plug in a local pose detector without rewriting the motion pipeline.

Recommended architecture:
image/video -> detector -> joint coordinates + confidence -> sequence builder -> QC -> retarget -> character renderer.

Do not assume one detector is perfect. Keep confidence values and reject low-confidence frames when required.
