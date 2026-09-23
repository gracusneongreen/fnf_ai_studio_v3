#!/bin/sh
# Re-renders the torch-free previews (storyboard PNG/GIF + pose-guide MP4)
# whenever a tracked source file changes. Output is served on port 3000.
set -u
OUT=/app/.base44/preview/output
mkdir -p "$OUT"
CHART="${PREVIEW_CHART:-examples/sample_chart.json}"

render() {
  echo "[render] $(date -u +%H:%M:%S) rendering previews from $CHART"
  python fnf_video_engine.py --chart "$CHART" --sneak-peek --preview-camera wide \
    --preview-style "neon rooftop stage" --preview-output "$OUT/storyboard.png" &&
  python fnf_video_engine.py --chart "$CHART" --sneak-peek --preview-camera wide \
    --preview-style "neon rooftop stage" --preview-output "$OUT/storyboard.gif" &&
  python fnf_video_engine.py --chart "$CHART" --pose-preview --duration-seconds 4 \
    --output "$OUT/pose_preview_raw.mp4" &&
  ffmpeg -loglevel error -y -i "$OUT/pose_preview_raw.mp4" -c:v libx264 \
    -pix_fmt yuv420p -movflags +faststart "$OUT/pose_preview.mp4" &&
  date -u +%Y-%m-%dT%H:%M:%SZ > "$OUT/status.txt" && echo "[render] done" ||
  { echo "render failed at $(date -u +%H:%M:%S) - see renderer logs" > "$OUT/status.txt"; echo "[render] FAILED"; }
}

stamp() {
  find . -path ./.git -prune -o -path ./.base44/preview/output -prune -o \
    \( -name '*.py' -o -name '*.json' \) -type f -newer "$OUT/.last" -print 2>/dev/null | head -1
}

touch "$OUT/.last"
render
while true; do
  sleep 2
  if [ -n "$(stamp)" ]; then touch "$OUT/.last"; render; fi
done
