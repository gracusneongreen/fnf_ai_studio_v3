from dataclasses import dataclass, field
from pathlib import Path
import json

POSES = ["idle", "singLEFT", "singDOWN", "singUP", "singRIGHT"]
PHASES = ["normal", "corruption_1", "corruption_2", "corruption_3", "nightmare"]


@dataclass
class CharacterProject:
    name: str
    prompt: str
    phase: str = "normal"
    poses: list[str] = field(default_factory=lambda: POSES.copy())
    reference: str | None = None
    sketch: str | None = None

    def validate(self):
        if self.phase not in PHASES:
            raise ValueError(f"Unknown phase: {self.phase}")
        missing = [p for p in POSES if p not in self.poses]
        if missing:
            raise ValueError(f"Missing required FNF animation poses: {missing}")


def build_generation_prompt(project: CharacterProject) -> str:
    project.validate()
    return (
        "Generate an ORIGINAL 2D rhythm-game character. "
        "Preserve the same identity, proportions, outfit, palette, hair and "
        "silhouette across every generated frame. Bold readable shapes, "
        "clean cartoon linework, expressive pose, transparent background. "
        f"Character: {project.name}. "
        f"Design: {project.prompt}. "
        f"Phase: {project.phase}. "
        f"Required poses: {', '.join(project.poses)}. "
        "Use the supplied reference/sketch only for structure and pose guidance. "
        "Do not reproduce a copyrighted character."
    )


def save_job(project: CharacterProject, out_dir: str = "jobs") -> Path:
    project.validate()
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{project.name.lower().replace(' ', '_')}.json"
    path.write_text(json.dumps({
        "model": "FNF-REAL-DRAW-V0.3",
        "project": project.__dict__,
        "generation_prompt": build_generation_prompt(project),
        "reference_contract": {
            "character": "Boyfriend",
            "purpose": "animation schema only",
            "poses": POSES
        }
    }, indent=2), encoding="utf-8")
    return path
