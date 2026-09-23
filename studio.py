"""FNF-OMNI-STUDIO-V2 orchestration API."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from cloud_ai_connector import CloudAIConfig, FreeAIConnector
from fnf_video_engine import (
    FNFHUDCompositor,
    PoseGuideRenderer,
    limit_timeline,
    parse_chart,
    render_sneak_peek,
)
from pose_generator import FNFOpenPoseGenerator


STUDIO_NAME = "FNF-OMNI-STUDIO-V2"


@dataclass(frozen=True)
class StudioConfig:
    fps: int = 24
    size: int = 512
    pose_hold_ms: float = 180.0
    approach_ms: float = 1600.0
    references_dir: Path = Path("assets/references")
    cloud_free: bool = False
    output_dir: Path = Path("outputs")
    _cloud: CloudAIConfig = field(default_factory=CloudAIConfig, repr=False)


class FNFOMNIStudioV2:
    """Coordinates chart parsing, guides, HUD, previews, and AI backends."""

    def __init__(self, config: StudioConfig = StudioConfig()) -> None:
        if config.fps <= 0 or config.size < 128:
            raise ValueError("fps must be positive and size must be at least 128")
        self.config = config
        self.ai = FreeAIConnector(
            CloudAIConfig(
                cloud_free=config.cloud_free,
                ollama_url=config._cloud.ollama_url,
                ollama_model=config._cloud.ollama_model,
                huggingface_model=config._cloud.huggingface_model,
                request_timeout=config._cloud.request_timeout,
            )
        )

    def load_timeline(self, chart: Path, duration_seconds: Optional[float] = None):
        timeline = parse_chart(chart, self.config.fps)
        return limit_timeline(timeline, duration_seconds)

    def pose_generator(self, chart: Path, duration_seconds: Optional[float] = None):
        timeline = self.load_timeline(chart, duration_seconds)
        return FNFOpenPoseGenerator(
            timeline, self.config.size, self.config.pose_hold_ms
        )

    def render_sneak_peek(
        self,
        chart: Path,
        output: Path,
        max_frames: int = 12,
        camera: str = "wide",
    ) -> Path:
        import argparse

        args = argparse.Namespace(
            chart=chart,
            fps=self.config.fps,
            tail_ms=1000.0,
            duration_seconds=None,
            preview_size=self.config.size,
            pose_hold_ms=self.config.pose_hold_ms,
            approach_ms=self.config.approach_ms,
            preview_max_frames=max_frames,
            preview_columns=3,
            preview_beat_stride=4,
            preview_fps=2.0,
            preview_camera=camera,
            preview_style="FNF-OMNI-STUDIO-V2 neon stage",
            preview_output=output,
        )
        render_sneak_peek(args)
        return output

    def status(self) -> dict:
        return {
            "studio": STUDIO_NAME,
            "fps": self.config.fps,
            "size": self.config.size,
            "references_dir": str(self.config.references_dir),
            "reference_files": [
                path.name
                for path in sorted(self.config.references_dir.glob("*"))
                if path.is_file()
            ],
            "ai": self.ai.status(),
        }

    @staticmethod
    def hud(timeline, size: int = 512, approach_ms: float = 1600.0):
        return FNFHUDCompositor(timeline, size, approach_ms)

    @staticmethod
    def pose_renderer(timeline, size: int = 512, pose_hold_ms: float = 180.0):
        return PoseGuideRenderer(timeline, size, pose_hold_ms)
