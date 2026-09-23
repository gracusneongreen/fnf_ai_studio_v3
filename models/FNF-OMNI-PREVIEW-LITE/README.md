# FNF-OMNI-PREVIEW-LITE

`FNFOmniPreviewEngine` is a zero-weight, programmatic storyboard module. It
selects song start/end, BPM boundaries, section switches, and periodic key
beats, then renders pose/HUD cards without loading Torch, Diffusers, ControlNet,
or the full `FNF-OMNI-VIDEO-V1` weights.

Use it through the main CLI:

```bash
python fnf_video_engine.py \
  --chart examples/sample_chart.json \
  --sneak-peek \
  --preview-camera wide \
  --preview-style "neon rooftop stage" \
  --preview-output storyboard.png
```

Use a `.gif` output path for a low-FPS animated storyboard. Camera choices are
`wide`, `medium`, and `close`.
