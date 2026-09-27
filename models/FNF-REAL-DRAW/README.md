# FNF-REAL-DRAW

FNF-REAL-DRAW is the asset-generation model layer for FNF AI Studio.

## Goal

Turn a user's drawing, sketch, pose sheet, or text description into a consistent
2D rhythm-game character/asset set while preserving editable animation structure.

## Core pipeline

1. Input: text + optional sketch/reference.
2. Character design pass.
3. Pose/gesture conditioning.
4. Consistency pass across all frames.
5. Layer/body-part separation.
6. Sprite-sheet packing.
7. Export to PNG + engine metadata.

## Character workflow

Example request:

"Create a dark corruption character with black hoodie, red pants,
white/brown shoes, five corruption phases, idle and four singing poses."

The model should produce:

- character turnaround/reference sheet
- idle
- singLEFT
- singDOWN
- singUP
- singRIGHT
- miss variants
- expression variants
- corruption phase variants
- transparent PNG assets
- optional separated body parts for rigging

## Training dataset

Do not train on scraped copyrighted datasets by default. Prefer:

- user-owned drawings
- explicitly licensed assets
- synthetic training examples
- public-domain material with compatible licenses

Each sample should contain:

- image
- caption
- pose label
- expression label
- character ID
- phase ID
- palette metadata
- optional segmentation mask

## Planned implementation

- Diffusion/flow base model selected by deployment environment
- LoRA adapters for the project's visual language
- ControlNet-style sketch/pose conditioning
- reference-image consistency adapter
- segmentation model for body-part extraction
- deterministic sprite-sheet/export pipeline

The model itself is intentionally separated from the export engine so that
weights can be replaced without changing FNF AI Studio.
