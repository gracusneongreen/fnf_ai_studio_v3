"""FNF-REAL-DRAW AI chat layer.

The chat is the natural-language controller for the generation pipeline.
It converts a user's request into a structured character job without
pretending that a text model itself is an image model.
"""

from dataclasses import dataclass, field
import json

POSES = ["idle", "singLEFT", "singDOWN", "singUP", "singRIGHT"]


@dataclass
class ChatSession:
    character_name: str = "NewCharacter"
    messages: list[dict] = field(default_factory=list)

    def system_prompt(self) -> str:
        return (
            "You are FNF-REAL-DRAW AI, an assistant for creating ORIGINAL "
            "2D rhythm-game characters and animations. "
            "You understand FNF-style animation schemas, sprite sheets, "
            "Sparrow XML and Psych Engine asset conventions. "
            "Use Boyfriend only as a structural animation reference. "
            "Never reproduce copyrighted character artwork."
        )

    def ask(self, user_text: str) -> dict:
        self.messages.append({"role": "user", "content": user_text})
        text = user_text.lower()

        poses = POSES if any(p.lower() in text for p in POSES) else POSES.copy()
        phase = "nightmare" if "nightmare" in text else (
            "corruption_3" if "corruption" in text else "normal"
        )

        return {
            "assistant": (
                "Got it. I will build an original FNF-inspired character "
                f"with phase={phase} and poses={poses}."
            ),
            "job": {
                "character_name": self.character_name,
                "request": user_text,
                "phase": phase,
                "poses": poses,
                "reference_mode": "animation_schema_only"
            }
        }

    def export_job(self, job: dict, path: str = "jobs/chat_job.json"):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(job, f, indent=2, ensure_ascii=False)
