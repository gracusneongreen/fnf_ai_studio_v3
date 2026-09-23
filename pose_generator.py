"""OpenPose-style FNF pose generation built on the V1 timeline parser."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

from fnf_video_engine import DIRECTIONS, PoseGuideRenderer


@dataclass(frozen=True)
class PoseFrame:
    """A deterministic pose selection for one timestamp."""

    timestamp_ms: float
    poses: Dict[str, int]
    beat_phase: float
    is_beat: bool


class FNFOpenPoseGenerator:
    """Generate held singing poses and beat-synchronised idle bops."""

    def __init__(
        self,
        timeline,
        size: int = 512,
        pose_hold_ms: float = 180.0,
        beat_bop_px: float = 0.025,
    ) -> None:
        self.timeline = timeline
        self.renderer = PoseGuideRenderer(timeline, size, pose_hold_ms)
        self.beat_bop_px = beat_bop_px

    def pose_at(self, timestamp_ms: float) -> PoseFrame:
        poses = {"player": -1, "opponent": -1}
        for note in self.timeline.notes:
            if note.time_ms <= timestamp_ms <= note.time_ms + max(
                180.0, note.sustain_ms
            ):
                poses[note.singer] = note.direction
        beat_ms = 60000.0 / self.timeline.bpm_at(timestamp_ms).bpm
        beat_number = timestamp_ms / beat_ms
        phase = beat_number - int(beat_number)
        return PoseFrame(
            timestamp_ms=timestamp_ms,
            poses=poses,
            beat_phase=phase,
            is_beat=phase < 0.02 or phase > 0.98,
        )

    def render(self, timestamp_ms: float):
        return self.renderer.render(timestamp_ms)

    @staticmethod
    def direction_name(direction: int) -> str:
        return DIRECTIONS[direction % len(DIRECTIONS)]
