from pathlib import Path
import json

POSES = ["idle", "singLEFT", "singDOWN", "singUP", "singRIGHT"]


def build_pose_jobs(character_prompt: str, phase: str = "normal"):
    return [
        {
            "pose": pose,
            "phase": phase,
            "prompt": (
                "Create an original 2D rhythm-game character frame. "
                "Keep the exact same character identity, outfit, palette, "
                "hair and proportions as the master design. "
                f"Animation pose: {pose}. Phase: {phase}. "
                f"Master design: {character_prompt}"
            ),
        }
        for pose in POSES
    ]


def save_pose_jobs(character_prompt: str, phase: str, path: str):
    jobs = build_pose_jobs(character_prompt, phase)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(jobs, indent=2), encoding="utf-8")
