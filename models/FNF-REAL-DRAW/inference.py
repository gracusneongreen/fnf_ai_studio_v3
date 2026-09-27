"""FNF-REAL-DRAW inference interface.

This is a backend contract/skeleton. Plug a licensed diffusion/flow model into
generate_backend() rather than bundling model weights in Git.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class DrawRequest:
    prompt: str
    reference_image: Optional[Path] = None
    sketch_image: Optional[Path] = None
    pose_image: Optional[Path] = None
    phase: str = "normal"
    poses: list[str] = field(default_factory=lambda: [
        "idle", "singLEFT", "singDOWN", "singUP", "singRIGHT"
    ])
    transparent: bool = True
    seed: int = 0


@dataclass
class DrawResult:
    frames: list[Path]
    sprite_sheet: Optional[Path]
    metadata: Path


class FNFRealDraw:
    """Model adapter used by FNF AI Studio."""

    def __init__(self, model_path: str | Path):
        self.model_path = Path(model_path)

    def generate_backend(self, request: DrawRequest):
        """Connect the selected licensed model here.

        Expected backend contract:
          backend.generate(prompt, reference, sketch, pose, seed) -> PIL.Image
        """
        raise NotImplementedError(
            "Attach a licensed diffusion/flow backend to FNF-REAL-DRAW."
        )

    def generate(self, request: DrawRequest, output_dir: str | Path) -> DrawResult:
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)

        # Backend integration is intentionally explicit so no model weights or
        # external service credentials are silently downloaded.
        self.generate_backend(request)

        metadata = output / "character_metadata.json"
        metadata.write_text(
            "{\n"
            f'  "model": "FNF-REAL-DRAW",\n'
            f'  "phase": "{request.phase}",\n'
            f'  "poses": {request.poses!r}\n'
            "}\n",
            encoding="utf-8",
        )

        return DrawResult(
            frames=[],
            sprite_sheet=None,
            metadata=metadata,
        )
