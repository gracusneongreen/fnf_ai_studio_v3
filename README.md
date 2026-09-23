# FNF-OMNI-STUDIO-V2

`FNF-OMNI-STUDIO-V2` is the orchestration layer on top of the deterministic
V1 chart, pose, storyboard, and OpenCV HUD primitives. It exposes a complete
local CLI, optional Rich chat, a free/local AI connector, reference-asset
discovery, and an auditable OSWorld-style computer-use bridge.

## V2 quick start

```bash
python main.py --status --cloud-free
python main.py --chart examples/sample_chart.json --sneak-peek \
  --output outputs/storyboard.png --preview-camera wide
python main.py --chat
python main.py --dashboard --cloud-free
```

`--cloud-free` only uses a local Ollama instance or an explicitly configured
Hugging Face endpoint. It does not bypass provider quotas, payment controls, or
authentication requirements. Set `HF_TOKEN` only when using a Hugging Face
free-tier model; no token is required for local Ollama.

### V2 modules

```text
main.py                    CLI entry point and flags
studio.py                  FNF-OMNI-STUDIO-V2 orchestration API
cli_chat.py                Rich slash-command terminal interface
pose_generator.py          held singing poses and beat metadata
hud_compositor.py          public HUD facade
cloud_ai_connector.py      local/free provider selection
osworld_bridge.py          optional screenshots and input logging
assets/references/         stable reference asset contract
```

Reference image filenames are documented in
`assets/references/README.md`. Small generated PNG placeholders are included
for smoke tests; replace them with project-owned reference art before
conditioning a render.

`OSWorldBridge` provides deterministic cubic-Bezier cursor paths with
overshoot, micro-jitter, deceleration, natural typing cadence, screenshot
streams, and a visible cursor overlay. Typed text is never retained in the
action log; install `mss` and `pyautogui` from `requirements.txt` to enable the
desktop adapter.

Open the dashboard preview at `http://127.0.0.1:8765` after starting the
dashboard. The **Connect Your Apps** tab reads these optional local settings:
`FNF_PSYCH_ENGINE_PATH`, `FNF_SPRITE_EDITOR_PATH`, `FNF_VIDEO_EDITOR_PATH`, and
`FNF_WORKSPACE`. Connected entries can be targeted or launched from the panel;
chat commands `/status`, `/connect`, `/target APP_ID`, and `/launch APP_ID`
are also available.

`FNF-OMNI-VIDEO-V1` is a hybrid 1:1 video architecture. Its
`FNFOmniVideoV1Pipeline` combines AnimateDiff, OpenPose ControlNet, and custom
LoRA weights, while OpenCV draws the timing-sensitive FNF arrows, strumline,
health bar, and score as a deterministic final pass.

## Project layout

```text
fnf_video_engine.py                         Main pipeline and CLI
fnf_omni_preview.py                         FNF-OMNI-PREVIEW-LITE engine
examples/sample_chart.json                  Psych Engine sample chart
models/download_weights.py                  Atomic weight installer
models/FNF-OMNI-VIDEO-V1/model_manifest.json Model configuration
models/FNF-OMNI-PREVIEW-LITE/model_manifest.json Preview configuration
models/FNF-OMNI-VIDEO-V1/README.md           Weight publishing instructions
tests/                                      Parser, renderer, and model tests
```

## Setup

Python 3.10+ and an NVIDIA GPU with a recent CUDA driver are recommended. A
16-frame 512x512 chunk typically needs a high-memory GPU; CPU execution is
supported by Diffusers but is impractically slow for full songs.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip

# Install the PyTorch wheel appropriate for your CUDA version first. Example:
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
pip install -r requirements.txt
```

Base model files download from Hugging Face on the first run. If a selected
model requires license acceptance, authenticate with `hf auth login` first.

Custom `FNF-OMNI-VIDEO-V1` weights are not committed to Git. Once they are
published, install them into the conventional location with a pinned revision
and checksum:

```bash
python models/download_weights.py \
  --repo-id OWNER/FNF-OMNI-VIDEO-V1 \
  --filename fnf-omni-video-v1.safetensors \
  --revision COMMIT_OR_TAG \
  --sha256 EXPECTED_SHA256
```

The downloader also accepts `--url` for direct HTTPS sources. Source defaults
can be recorded in `models/FNF-OMNI-VIDEO-V1/model_manifest.json` after the
weights are published.

## Run

### Sneak Peek storyboard

Review key beats, section switches, camera framing, character placement, and a
deterministic background palette before running diffusion:

```bash
python fnf_video_engine.py \
  --chart examples/sample_chart.json \
  --sneak-peek \
  --preview-camera wide \
  --preview-style "neon rooftop stage" \
  --preview-output storyboard.png
```

Set `--preview-output storyboard.gif` for a low-FPS animated preview. Useful
controls include `--preview-max-frames`, `--preview-beat-stride`,
`--preview-columns`, `--preview-size`, `--preview-fps`, and
`--duration-seconds`. This path uses `FNFOmniPreviewEngine` and never loads
Torch, Diffusers, or model weights.

### Pose-guide preview

First validate chart parsing, BPM poses, HUD animation, and MP4 support without
downloading models:

```bash
python fnf_video_engine.py \
  --chart examples/sample_chart.json \
  --pose-preview \
  --duration-seconds 4 \
  --output pose_preview.mp4
```

### Full FNF-OMNI-VIDEO-V1 render

Generate the AI-backed video:

```bash
python fnf_video_engine.py \
  --chart /path/to/song-hard.json \
  --fps 24 \
  --size 512 \
  --chunk-size 16 \
  --output fnf_gameplay.mp4
```

The pipeline automatically loads
`models/FNF-OMNI-VIDEO-V1/fnf-omni-video-v1.safetensors` when present. Use
`--weights /path/to/other.safetensors` to override it. The former `--lora` and
`--lora-scale` flags remain aliases for compatibility.

For a 60 FPS export, pass `--fps 60`. This generates every output frame and is
therefore much more expensive than 24 FPS. Use `--duration-seconds 5` for short
iteration runs. `--guides-dir pose_guides` saves the exact ControlNet inputs for
inspection. Run `python fnf_video_engine.py --help` for model IDs, prompt,
conditioning, seed, timing, and quality controls.

The engine draws BODY_18 guides itself, so `controlnet_aux` and a separate pose
detector are not required. `diffusers`, `transformers`, `accelerate`, `peft`,
`safetensors`, OpenCV, NumPy, and Pillow are installed by `requirements.txt`.

The MP4 is silent; mux the original song afterward if needed, for example:

```bash
ffmpeg -i fnf_gameplay.mp4 -i Inst.ogg -c:v copy -c:a aac -shortest final.mp4
```

## Chart interpretation

The parser accepts both `{ "song": { ... } }` Psych Engine charts and unwrapped
song objects. It integrates `changeBPM`, `bpm`, `lengthInSteps`, and
`sectionBeats` section timing. Legacy notes use Psych's relative-side rule;
charts marked `format: "psych_v1"` use absolute lanes 0-3 for the player and
4-7 for the opponent. Lane modulo four maps to Left, Down, Up, Right, and
sustain lengths keep the corresponding pose active.
