# Download FNF-OMNI-VIDEO-V1 custom weights
#
# These weights are intentionally NOT committed to Git.  Model artifacts
# (fnf-omni-video-v1.safetensors, ControlNet LoRA weights) reside in
# models/FNF-OMNI-VIDEO-V1/.  The directory is created on demand.
# if the weights are missing.
#
# The `requirements.txt` - a reference does not list those packages that the
# torch-free preview paths require (opencv-python-headless, numpy, Pillow).
# so they must be installed manually in the relevant services.
# (the renderer and web do this in their compose command).
#
# IMPORTANT: This file is created by Base44 for dev environment setup.
# and may be overwritten. Do not edit it.
