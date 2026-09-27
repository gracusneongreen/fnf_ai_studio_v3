from dataclasses import dataclass, field
from pathlib import Path
import json

POSES = ["idle", "singLEFT", "singDOWN", "singUP", "singRIGHT"]


@dataclass
class DrawInput:
    image_path: str
    character_name: str
    phase: str = "normal"
    parts: list[str] = field(default_factory=lambda: [
        "head", "hair", "torso", "left_arm", "right_arm",
        "left_hand", "right_hand", "left_leg", "right_leg", "shoes"
    ])


def build_animation_plan(item: DrawInput) -> dict:
    if not Path(item.image_path).exists():
        raise FileNotFoundError(item.image_path)

    return {
        "character": item.character_name,
        "source": item.image_path,
        "phase": item.phase,
        "parts": item.parts,
        "poses": POSES,
        "consistency_lock": {
            "identity": True,
            "outfit": True,
            "palette": True,
            "silhouette": True,
            "proportions": True
        }
    }


def save_plan(item: DrawInput, output: str):
    plan = build_animation_plan(item)
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(json.dumps(plan, indent=2), encoding="utf-8")
