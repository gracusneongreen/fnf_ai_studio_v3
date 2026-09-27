from __future__ import annotations

import json
from pathlib import Path
from dataclasses import dataclass, asdict


POSES = ["idle", "singLEFT", "singDOWN", "singUP", "singRIGHT"]


@dataclass
class CharacterSpec:
    name: str
    description: str
    phase: str = "normal"
    poses: list[str] | None = None

    def __post_init__(self):
        if self.poses is None:
            self.poses = POSES.copy()


def build_prompt(spec: CharacterSpec) -> str:
    return (
        "Create an ORIGINAL 2D rhythm-game character sprite set. "
        "Keep one consistent character identity across all frames. "
        "Bold readable silhouette, clean outlines, cel shading, expressive pose. "
        f"Character name: {spec.name}. "
        f"Description: {spec.description}. "
        f"Corruption phase: {spec.phase}. "
        f"Animation poses: {', '.join(spec.poses)}. "
        "Transparent background. No copyrighted character reproduction."
    )


def write_job(spec: CharacterSpec, output: str = "character_job.json") -> Path:
    path = Path(output)
    path.write_text(
        json.dumps({
            "model": "FNF-REAL-DRAW",
            "spec": asdict(spec),
            "prompt": build_prompt(spec),
            "reference_contract": {
                "animation_schema": POSES,
                "reference_character": "Boyfriend",
                "reference_use": "pose/schema guidance only"
            }
        }, indent=2),
        encoding="utf-8"
    )
    return path


if __name__ == "__main__":
    spec = CharacterSpec(
        name="Gracjan",
        description="black hoodie, red pants, black hair, white shoes with brown details",
        phase="normal"
    )
    print(write_job(spec))
