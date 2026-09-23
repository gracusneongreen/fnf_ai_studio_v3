#!/usr/bin/env python3
"""Hybrid Friday Night Funkin' video generator.

The diffusion model creates only the scene and characters.  Timing-sensitive
gameplay elements are drawn afterwards with OpenCV so arrows and HUD text stay
crisp and deterministic.
"""

from __future__ import annotations

import argparse
import bisect
import json
import logging
import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw

LOGGER = logging.getLogger("fnf-video-engine")
DIRECTIONS = ("left", "down", "up", "right")
SINGERS = ("opponent", "player")
ARCHITECTURE_NAME = "FNF-OMNI-VIDEO-V1"
MODEL_ROOT = Path(__file__).resolve().parent / "models" / ARCHITECTURE_NAME
DEFAULT_WEIGHTS_PATH = MODEL_ROOT / "fnf-omni-video-v1.safetensors"


@dataclass(frozen=True)
class NoteEvent:
    """A normalized chart note with an absolute song time."""

    time_ms: float
    frame: int
    direction: int
    singer: str
    sustain_ms: float = 0.0
    note_type: str = ""


@dataclass(frozen=True)
class BPMSegment:
    """A BPM value that becomes active at ``start_ms``."""

    start_ms: float
    start_frame: int
    bpm: float
    section_index: int


@dataclass(frozen=True)
class ChartSection:
    """Timing and active singer metadata for one chart section."""

    section_index: int
    start_ms: float
    end_ms: float
    start_frame: int
    end_frame: int
    bpm: float
    must_hit: bool


@dataclass(frozen=True)
class ChartTimeline:
    song_name: str
    fps: int
    initial_bpm: float
    notes: Tuple[NoteEvent, ...]
    bpm_segments: Tuple[BPMSegment, ...]
    sections: Tuple[ChartSection, ...]
    duration_ms: float

    @property
    def frame_count(self) -> int:
        return max(1, int(math.ceil(self.duration_ms * self.fps / 1000.0)))

    def bpm_at(self, time_ms: float) -> BPMSegment:
        starts = [segment.start_ms for segment in self.bpm_segments]
        index = max(0, bisect.bisect_right(starts, time_ms) - 1)
        return self.bpm_segments[index]


def milliseconds_to_frame(time_ms: float, fps: int) -> int:
    """Map milliseconds to the nearest frame without banker's rounding."""

    if fps <= 0:
        raise ValueError("fps must be positive")
    return int(math.floor((max(0.0, time_ms) * fps / 1000.0) + 0.5))


def _positive_number(value: Any, field_name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric, got {value!r}") from exc
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"{field_name} must be positive, got {value!r}")
    return number


def parse_chart(path: Path, fps: int, tail_ms: float = 1000.0) -> ChartTimeline:
    """Parse a Psych Engine/base-game chart into a frame-addressable timeline.

    Psych charts store absolute note timestamps, while BPM changes live on
    sections.  Section lengths are integrated to determine the exact start of
    each BPM segment. Legacy lanes 4-7 invert ``mustHitSection``; Psych v1
    lanes use absolute ownership. Lane modulo four gives Left, Down, Up, Right.
    """

    if fps <= 0:
        raise ValueError("fps must be positive")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid chart JSON in {path}: {exc}") from exc

    wrapped_song = payload.get("song") if isinstance(payload, dict) else None
    song = wrapped_song if isinstance(wrapped_song, dict) else payload
    if not isinstance(song, dict):
        raise ValueError("chart must contain a JSON object at its root or 'song' key")

    initial_bpm = _positive_number(song.get("bpm", 120), "song.bpm")
    sections = song.get("notes", [])
    if not isinstance(sections, list):
        raise ValueError("song.notes must be a list of sections")
    is_psych_v1 = song.get("format") == "psych_v1"

    current_bpm = initial_bpm
    section_start_ms = 0.0
    bpm_segments: List[BPMSegment] = [BPMSegment(0.0, 0, initial_bpm, 0)]
    notes: List[NoteEvent] = []
    chart_sections: List[ChartSection] = []

    for section_index, section in enumerate(sections):
        if not isinstance(section, dict):
            LOGGER.warning("Ignoring malformed section %d", section_index)
            continue

        if section.get("changeBPM") and section.get("bpm") is not None:
            new_bpm = _positive_number(
                section["bpm"], f"song.notes[{section_index}].bpm"
            )
            if not math.isclose(new_bpm, current_bpm):
                current_bpm = new_bpm
                segment = BPMSegment(
                    section_start_ms,
                    milliseconds_to_frame(section_start_ms, fps),
                    current_bpm,
                    section_index,
                )
                # A first-section override is active from time zero, so replace
                # rather than retain two contradictory zero-time segments.
                if math.isclose(section_start_ms, 0.0):
                    bpm_segments[0] = segment
                else:
                    bpm_segments.append(segment)

        must_hit = bool(section.get("mustHitSection", False))
        length_steps_value = section.get("lengthInSteps")
        if length_steps_value is None:
            length_steps_value = float(section.get("sectionBeats", 4.0)) * 4.0
        length_steps = _positive_number(
            length_steps_value, f"song.notes[{section_index}].lengthInSteps"
        )
        section_end_ms = section_start_ms + length_steps * (60000.0 / current_bpm / 4.0)
        chart_sections.append(
            ChartSection(
                section_index=section_index,
                start_ms=section_start_ms,
                end_ms=section_end_ms,
                start_frame=milliseconds_to_frame(section_start_ms, fps),
                end_frame=milliseconds_to_frame(section_end_ms, fps),
                bpm=current_bpm,
                must_hit=must_hit,
            )
        )
        raw_notes = section.get("sectionNotes", [])
        if not isinstance(raw_notes, list):
            raise ValueError(f"song.notes[{section_index}].sectionNotes must be a list")

        for raw_note in raw_notes:
            if not isinstance(raw_note, (list, tuple)) or len(raw_note) < 2:
                LOGGER.warning("Ignoring malformed note in section %d", section_index)
                continue
            try:
                time_ms = max(0.0, float(raw_note[0]))
                raw_lane = int(raw_note[1])
                sustain_ms = max(0.0, float(raw_note[2])) if len(raw_note) > 2 else 0.0
            except (TypeError, ValueError):
                LOGGER.warning("Ignoring non-numeric note %r", raw_note)
                continue
            if raw_lane < 0:  # Event notes are encoded with negative note data.
                continue

            opposite_side = raw_lane >= 4
            # Psych v1 stores absolute sides (0-3 player, 4-7 opponent).
            # Legacy/base-game charts store sides relative to mustHitSection.
            is_player = not opposite_side if is_psych_v1 else must_hit != opposite_side
            note_type = str(raw_note[3]) if len(raw_note) > 3 else ""
            notes.append(
                NoteEvent(
                    time_ms=time_ms,
                    frame=milliseconds_to_frame(time_ms, fps),
                    direction=raw_lane % 4,
                    singer="player" if is_player else "opponent",
                    sustain_ms=sustain_ms,
                    note_type=note_type,
                )
            )

        section_start_ms = section_end_ms

    notes.sort(key=lambda note: (note.time_ms, note.singer, note.direction))
    final_note_ms = max((note.time_ms + note.sustain_ms for note in notes), default=0.0)
    duration_ms = max(section_start_ms, final_note_ms) + max(0.0, tail_ms)
    song_name = str(song.get("song") or path.stem)
    return ChartTimeline(
        song_name=song_name,
        fps=fps,
        initial_bpm=initial_bpm,
        notes=tuple(notes),
        bpm_segments=tuple(bpm_segments),
        sections=tuple(chart_sections),
        duration_ms=duration_ms,
    )


# OpenPose BODY_18 indices and edges.  The palette follows the familiar
# red-to-violet OpenPose visualization, which works directly as ControlNet input.
BODY_EDGES: Tuple[Tuple[int, int], ...] = (
    (1, 2),
    (1, 5),
    (2, 3),
    (3, 4),
    (5, 6),
    (6, 7),
    (1, 8),
    (8, 9),
    (9, 10),
    (1, 11),
    (11, 12),
    (12, 13),
    (1, 0),
    (0, 14),
    (14, 16),
    (0, 15),
    (15, 17),
)
OPENPOSE_COLORS: Tuple[Tuple[int, int, int], ...] = (
    (255, 0, 0),
    (255, 85, 0),
    (255, 170, 0),
    (255, 255, 0),
    (170, 255, 0),
    (85, 255, 0),
    (0, 255, 0),
    (0, 255, 85),
    (0, 255, 170),
    (0, 255, 255),
    (0, 170, 255),
    (0, 85, 255),
    (0, 0, 255),
    (85, 0, 255),
    (170, 0, 255),
    (255, 0, 255),
    (255, 0, 170),
)


class PoseGuideRenderer:
    """Create two-character OpenPose-style guides driven by chart events."""

    def __init__(self, timeline: ChartTimeline, size: int, pose_hold_ms: float = 180.0):
        if size <= 0:
            raise ValueError("size must be positive")
        self.timeline = timeline
        self.size = size
        self.pose_hold_ms = pose_hold_ms
        self._notes: Dict[str, List[NoteEvent]] = {
            singer: [note for note in timeline.notes if note.singer == singer]
            for singer in SINGERS
        }
        self._times: Dict[str, List[float]] = {
            singer: [note.time_ms for note in notes]
            for singer, notes in self._notes.items()
        }

    def _active_note(self, singer: str, time_ms: float) -> Optional[NoteEvent]:
        index = bisect.bisect_right(self._times[singer], time_ms) - 1
        if index < 0:
            return None
        note = self._notes[singer][index]
        hold_ms = max(self.pose_hold_ms, note.sustain_ms + self.pose_hold_ms * 0.4)
        return note if time_ms <= note.time_ms + hold_ms else None

    def _idle_motion(self, time_ms: float) -> Tuple[float, float]:
        segment = self.timeline.bpm_at(time_ms)
        beat_ms = 60000.0 / segment.bpm
        beat_position = max(0.0, time_ms - segment.start_ms) / beat_ms
        beat_number = int(math.floor(beat_position))
        phase = beat_position - beat_number
        # A fast dip and recovery on every beat, alternating horizontal lean.
        bob = math.sin(phase * math.pi) * 0.025
        sway = (-1.0 if beat_number % 2 == 0 else 1.0) * 0.018
        return bob, sway

    @staticmethod
    def _base_body(center_x: float) -> List[Tuple[float, float]]:
        return [
            (center_x, 0.24),  # nose
            (center_x, 0.34),  # neck
            # Anatomical right is image-left for a front-facing character.
            (center_x - 0.065, 0.35),
            (center_x - 0.10, 0.46),
            (center_x - 0.12, 0.57),
            (center_x + 0.065, 0.35),
            (center_x + 0.10, 0.46),
            (center_x + 0.12, 0.57),
            (center_x - 0.045, 0.55),
            (center_x - 0.055, 0.70),
            (center_x - 0.065, 0.87),
            (center_x + 0.045, 0.55),
            (center_x + 0.055, 0.70),
            (center_x + 0.065, 0.87),
            (center_x - 0.018, 0.225),
            (center_x + 0.018, 0.225),
            (center_x - 0.038, 0.235),
            (center_x + 0.038, 0.235),
        ]

    def _posed_body(
        self, singer: str, direction: Optional[int], time_ms: float
    ) -> List[Tuple[float, float]]:
        center_x = 0.29 if singer == "opponent" else 0.71
        points = self._base_body(center_x)
        if direction is None:
            bob, sway = self._idle_motion(time_ms)
            return [(x + sway, y + bob) for x, y in points]

        if direction == 0:  # Left: lean and point the left arm.
            points = [(x - (0.025 if y < 0.58 else 0.0), y) for x, y in points]
            points[3], points[4] = (center_x - 0.14, 0.40), (center_x - 0.22, 0.36)
        elif direction == 1:  # Down: crouch with bent knees.
            points = [(x, y + (0.07 if y < 0.58 else 0.0)) for x, y in points]
            points[9], points[10] = (center_x - 0.11, 0.71), (center_x - 0.13, 0.84)
            points[12], points[13] = (center_x + 0.11, 0.71), (center_x + 0.13, 0.84)
        elif direction == 2:  # Up: both hands above the head.
            points[3], points[4] = (center_x - 0.10, 0.27), (center_x - 0.08, 0.13)
            points[6], points[7] = (center_x + 0.10, 0.27), (center_x + 0.08, 0.13)
            points[0] = (center_x, 0.20)
        elif direction == 3:  # Right: lean and point the right arm.
            points = [(x + (0.025 if y < 0.58 else 0.0), y) for x, y in points]
            points[6], points[7] = (center_x + 0.14, 0.40), (center_x + 0.22, 0.36)
        return points

    def render(self, time_ms: float) -> Image.Image:
        canvas = Image.new("RGB", (self.size, self.size), "black")
        draw = ImageDraw.Draw(canvas)
        line_width = max(2, self.size // 128)
        joint_radius = max(2, self.size // 100)

        for singer in SINGERS:
            active_note = self._active_note(singer, time_ms)
            direction = active_note.direction if active_note else None
            normalized = self._posed_body(singer, direction, time_ms)
            points = [
                (int(round(x * self.size)), int(round(y * self.size)))
                for x, y in normalized
            ]
            for edge_index, (start, end) in enumerate(BODY_EDGES):
                draw.line(
                    (points[start], points[end]),
                    fill=OPENPOSE_COLORS[edge_index],
                    width=line_width,
                )
            for index, (x, y) in enumerate(points):
                color = OPENPOSE_COLORS[index % len(OPENPOSE_COLORS)]
                draw.ellipse(
                    (
                        x - joint_radius,
                        y - joint_radius,
                        x + joint_radius,
                        y + joint_radius,
                    ),
                    fill=color,
                )
        return canvas


@dataclass
class HUDState:
    health: float = 0.5
    score: int = 0
    misses: int = 0


class FNFHUDCompositor:
    """Deterministic OpenCV renderer for arrows, score, and health."""

    NOTE_COLORS = (
        (194, 75, 194),  # left, BGR purple
        (255, 194, 75),  # down, BGR cyan
        (83, 214, 83),  # up, green
        (75, 75, 235),  # right, red
    )

    def __init__(
        self,
        timeline: ChartTimeline,
        size: int,
        approach_ms: float = 1600.0,
        state: Optional[HUDState] = None,
    ):
        self.timeline = timeline
        self.size = size
        self.approach_ms = approach_ms
        self.state = state or HUDState()
        self.strum_y = int(size * 0.15)
        self.spawn_y = int(size * 0.78)
        lane_gap = size * 0.065
        self.lane_centers: Dict[str, Tuple[int, ...]] = {
            "opponent": tuple(int(size * 0.18 + lane * lane_gap) for lane in range(4)),
            "player": tuple(int(size * 0.62 + lane * lane_gap) for lane in range(4)),
        }
        self._note_times = [note.time_ms for note in timeline.notes]

    @staticmethod
    def _arrow_points(
        center: Tuple[int, int], direction: int, radius: int
    ) -> np.ndarray:
        # Start with an upward arrow, then rotate in 90-degree increments.
        cx, cy = center
        points = np.array(
            [
                (-radius, 0),
                (-radius // 2, 0),
                (-radius // 2, radius),
                (radius // 2, radius),
                (radius // 2, 0),
                (radius, 0),
                (0, -radius),
            ],
            dtype=np.float64,
        )
        rotations = {0: -1, 1: 2, 2: 0, 3: 1}
        angle = rotations[direction] * (math.pi / 2.0)
        rotation = np.array(
            [[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]]
        )
        points = points @ rotation.T
        points[:, 0] += cx
        points[:, 1] += cy
        return np.rint(points).astype(np.int32)

    def _draw_arrow(
        self,
        frame: np.ndarray,
        center: Tuple[int, int],
        direction: int,
        color: Tuple[int, int, int],
        filled: bool,
    ) -> None:
        radius = max(9, self.size // 36)
        contour = self._arrow_points(center, direction, radius)
        if filled:
            cv2.fillPoly(frame, [contour], color, lineType=cv2.LINE_8)
            cv2.polylines(frame, [contour], True, (20, 20, 20), 2, cv2.LINE_8)
        else:
            cv2.polylines(frame, [contour], True, color, 2, cv2.LINE_8)

    def compose(self, rgb_frame: Image.Image, time_ms: float) -> np.ndarray:
        resized = rgb_frame.convert("RGB").resize(
            (self.size, self.size), Image.Resampling.LANCZOS
        )
        frame = cv2.cvtColor(np.asarray(resized), cv2.COLOR_RGB2BGR).copy()

        # Fixed receptors on the opponent and player halves.
        for singer in SINGERS:
            for direction, x in enumerate(self.lane_centers[singer]):
                self._draw_arrow(
                    frame, (x, self.strum_y), direction, (210, 210, 210), False
                )

        # Notes travel from the lower playfield to the receptor at their timestamp.
        early_limit = time_ms + self.approach_ms
        late_limit = time_ms - 120.0
        first_note = bisect.bisect_left(self._note_times, late_limit)
        final_note = bisect.bisect_right(self._note_times, early_limit)
        for note in self.timeline.notes[first_note:final_note]:
            progress = 1.0 - ((note.time_ms - time_ms) / self.approach_ms)
            y = int(round(self.spawn_y + progress * (self.strum_y - self.spawn_y)))
            x = self.lane_centers[note.singer][note.direction]
            self._draw_arrow(
                frame, (x, y), note.direction, self.NOTE_COLORS[note.direction], True
            )

        self._draw_health_and_score(frame)
        return frame

    def _draw_health_and_score(self, frame: np.ndarray) -> None:
        health = float(np.clip(self.state.health, 0.0, 1.0))
        x0, x1 = int(self.size * 0.12), int(self.size * 0.88)
        y0, y1 = int(self.size * 0.87), int(self.size * 0.905)
        split = int(round(x0 + (x1 - x0) * (1.0 - health)))
        cv2.rectangle(frame, (x0, y0), (split, y1), (35, 35, 215), -1, cv2.LINE_8)
        cv2.rectangle(frame, (split, y0), (x1, y1), (45, 205, 55), -1, cv2.LINE_8)
        cv2.rectangle(frame, (x0, y0), (x1, y1), (15, 15, 15), 3, cv2.LINE_8)

        text = f"Score: {self.state.score} | Misses: {self.state.misses}"
        font_scale = max(0.4, self.size / 900.0)
        thickness = max(1, self.size // 300)
        (text_width, _), _ = cv2.getTextSize(
            text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness
        )
        origin = ((self.size - text_width) // 2, int(self.size * 0.955))
        cv2.putText(
            frame,
            text,
            origin,
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            (0, 0, 0),
            thickness + 2,
            cv2.LINE_8,
        )
        cv2.putText(
            frame,
            text,
            origin,
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            (255, 255, 255),
            thickness,
            cv2.LINE_8,
        )


@dataclass(frozen=True)
class FNFOmniVideoV1Config:
    """Model and inference configuration for FNF-OMNI-VIDEO-V1."""

    base_model: str
    motion_adapter: str
    controlnet_model: str
    weights_path: Optional[Path]
    weights_scale: float
    prompt: str
    negative_prompt: str
    inference_steps: int
    guidance_scale: float
    controlnet_scale: float
    seed: int
    architecture: str = ARCHITECTURE_NAME

    def resolved_weights_path(self) -> Optional[Path]:
        """Resolve an explicit weight path or discover the conventional local file."""

        if self.weights_path is not None:
            return self.weights_path.expanduser().resolve()
        if DEFAULT_WEIGHTS_PATH.is_file():
            return DEFAULT_WEIGHTS_PATH
        return None


class FNFOmniVideoV1Pipeline:
    """FNF-OMNI-VIDEO-V1 AnimateDiff, OpenPose ControlNet, and LoRA pipeline."""

    def __init__(self, config: FNFOmniVideoV1Config):
        if config.architecture != ARCHITECTURE_NAME:
            raise ValueError(
                f"expected architecture {ARCHITECTURE_NAME!r}, "
                f"got {config.architecture!r}"
            )
        self.config = config
        self.pipe: Any = None
        self.torch: Any = None

    def load(self) -> None:
        try:
            import torch
            from diffusers import (
                AnimateDiffControlNetPipeline,
                ControlNetModel,
                DDIMScheduler,
                MotionAdapter,
            )
        except ImportError as exc:
            raise RuntimeError(
                "AnimateDiff dependencies are missing. "
                "Run: pip install -r requirements.txt"
            ) from exc

        weights_path = self.config.resolved_weights_path()
        if weights_path is not None:
            if not weights_path.is_file():
                raise FileNotFoundError(f"weights not found: {weights_path}")
            if weights_path.suffix.lower() != ".safetensors":
                raise ValueError("--weights must point to a .safetensors file")

        self.torch = torch
        if torch.cuda.is_available():
            dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
        else:
            dtype = torch.float32
            LOGGER.warning(
                "CUDA is unavailable; AnimateDiff on CPU will be extremely slow"
            )

        LOGGER.info("Loading motion adapter: %s", self.config.motion_adapter)
        motion_adapter = MotionAdapter.from_pretrained(
            self.config.motion_adapter, torch_dtype=dtype
        )
        LOGGER.info("Loading OpenPose ControlNet: %s", self.config.controlnet_model)
        controlnet = ControlNetModel.from_pretrained(
            self.config.controlnet_model, torch_dtype=dtype
        )
        LOGGER.info("Loading Stable Diffusion base: %s", self.config.base_model)
        self.pipe = AnimateDiffControlNetPipeline.from_pretrained(
            self.config.base_model,
            motion_adapter=motion_adapter,
            controlnet=controlnet,
            torch_dtype=dtype,
        )
        self.pipe.scheduler = DDIMScheduler.from_config(
            self.pipe.scheduler.config,
            beta_schedule="linear",
            clip_sample=False,
            timestep_spacing="linspace",
            steps_offset=1,
        )

        if weights_path is not None:
            LOGGER.info("Loading %s weights: %s", ARCHITECTURE_NAME, weights_path)
            self.pipe.load_lora_weights(
                str(weights_path.parent),
                weight_name=weights_path.name,
                adapter_name="fnf_omni_video_v1",
            )
            self.pipe.set_adapters(
                ["fnf_omni_video_v1"],
                adapter_weights=[self.config.weights_scale],
            )

        self.pipe.enable_vae_slicing()
        if torch.cuda.is_available():
            # Requires accelerate; components are moved to the GPU only as needed.
            self.pipe.enable_model_cpu_offload()
        else:
            self.pipe.to("cpu")

    def generate(self, guides: Sequence[Image.Image]) -> List[Image.Image]:
        if self.pipe is None:
            self.load()
        if not guides:
            return []
        # A CPU generator is accepted by Diffusers and stays deterministic even
        # when model components are being moved by model CPU offload.
        generator = self.torch.Generator(device="cpu").manual_seed(self.config.seed)
        result = self.pipe(
            prompt=self.config.prompt,
            negative_prompt=self.config.negative_prompt,
            conditioning_frames=list(guides),
            num_frames=len(guides),
            height=guides[0].height,
            width=guides[0].width,
            num_inference_steps=self.config.inference_steps,
            guidance_scale=self.config.guidance_scale,
            controlnet_conditioning_scale=self.config.controlnet_scale,
            generator=generator,
            decode_chunk_size=min(8, len(guides)),
            output_type="pil",
        )
        return list(result.frames[0])


def _batched_indices(frame_count: int, chunk_size: int) -> Iterable[range]:
    for start in range(0, frame_count, chunk_size):
        yield range(start, min(start + chunk_size, frame_count))


def limit_timeline(
    timeline: ChartTimeline, duration_seconds: Optional[float]
) -> ChartTimeline:
    """Return a timeline truncated to a short preview duration."""

    if duration_seconds is None:
        return timeline
    duration_ms = min(timeline.duration_ms, duration_seconds * 1000.0)
    if math.isclose(duration_ms, timeline.duration_ms):
        return timeline
    sections = tuple(
        replace(
            section,
            end_ms=min(section.end_ms, duration_ms),
            end_frame=milliseconds_to_frame(
                min(section.end_ms, duration_ms), timeline.fps
            ),
        )
        for section in timeline.sections
        if section.start_ms < duration_ms
    )
    return replace(
        timeline,
        notes=tuple(note for note in timeline.notes if note.time_ms < duration_ms),
        bpm_segments=tuple(
            segment
            for segment in timeline.bpm_segments
            if segment.start_ms < duration_ms
        ),
        sections=sections,
        duration_ms=duration_ms,
    )


def render_sneak_peek(args: argparse.Namespace) -> None:
    """Export a FNF-OMNI-PREVIEW-LITE storyboard without diffusion inference."""

    from fnf_omni_preview import FNFOmniPreviewConfig, FNFOmniPreviewEngine

    timeline = parse_chart(args.chart.expanduser().resolve(), args.fps, args.tail_ms)
    timeline = limit_timeline(timeline, args.duration_seconds)
    pose_renderer = PoseGuideRenderer(timeline, args.preview_size, args.pose_hold_ms)
    compositor = FNFHUDCompositor(timeline, args.preview_size, args.approach_ms)
    engine = FNFOmniPreviewEngine(
        timeline,
        pose_renderer,
        compositor,
        FNFOmniPreviewConfig(
            size=args.preview_size,
            max_frames=args.preview_max_frames,
            columns=args.preview_columns,
            beat_stride=args.preview_beat_stride,
            gif_fps=args.preview_fps,
            camera_angle=args.preview_camera,
            background_style=args.preview_style,
        ),
    )
    keyframes = engine.export(args.preview_output)
    LOGGER.info(
        "Wrote %s with %d storyboard keyframes",
        args.preview_output.expanduser().resolve(),
        len(keyframes),
    )


def render_video(args: argparse.Namespace) -> None:
    chart_path = args.chart.expanduser().resolve()
    timeline = parse_chart(chart_path, args.fps, args.tail_ms)
    frame_count = timeline.frame_count
    if args.duration_seconds is not None:
        frame_count = min(
            frame_count, max(1, math.ceil(args.duration_seconds * args.fps))
        )

    LOGGER.info(
        "Loaded %s: %d notes, %d BPM segment(s), %.2fs / %d frames",
        timeline.song_name,
        len(timeline.notes),
        len(timeline.bpm_segments),
        frame_count / args.fps,
        frame_count,
    )
    pose_renderer = PoseGuideRenderer(timeline, args.size, args.pose_hold_ms)
    compositor = FNFHUDCompositor(timeline, args.size, args.approach_ms)

    model: Optional[FNFOmniVideoV1Pipeline] = None
    if not args.pose_preview:
        model = FNFOmniVideoV1Pipeline(
            FNFOmniVideoV1Config(
                base_model=args.base_model,
                motion_adapter=args.motion_adapter,
                controlnet_model=args.controlnet_model,
                weights_path=args.weights_path,
                weights_scale=args.weights_scale,
                prompt=args.prompt,
                negative_prompt=args.negative_prompt,
                inference_steps=args.inference_steps,
                guidance_scale=args.guidance_scale,
                controlnet_scale=args.controlnet_scale,
                seed=args.seed,
            )
        )

    output_path = args.output.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        str(output_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        float(args.fps),
        (args.size, args.size),
    )
    if not writer.isOpened():
        raise RuntimeError(
            f"OpenCV could not open MP4 writer for {output_path}; check codec support"
        )

    if args.guides_dir is not None:
        args.guides_dir.mkdir(parents=True, exist_ok=True)

    written = 0
    try:
        for indices in _batched_indices(frame_count, args.chunk_size):
            guides = [
                pose_renderer.render(index * 1000.0 / args.fps) for index in indices
            ]
            if args.guides_dir is not None:
                for index, guide in zip(indices, guides):
                    guide.save(args.guides_dir / f"pose_{index:06d}.png")

            backgrounds = guides if model is None else model.generate(guides)
            if len(backgrounds) != len(guides):
                raise RuntimeError(
                    f"pipeline returned {len(backgrounds)} frames for "
                    f"{len(guides)} guides"
                )
            for frame_index, background in zip(indices, backgrounds):
                time_ms = frame_index * 1000.0 / args.fps
                writer.write(compositor.compose(background, time_ms))
                written += 1
            LOGGER.info("Rendered %d/%d frames", written, frame_count)
    finally:
        writer.release()

    if written != frame_count:
        raise RuntimeError(f"video export stopped after {written}/{frame_count} frames")
    LOGGER.info("Wrote %s", output_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate square FNF gameplay video with AnimateDiff and an OpenCV HUD."
        )
    )
    parser.add_argument(
        "--chart", type=Path, required=True, help="Psych Engine chart JSON"
    )
    parser.add_argument(
        "--weights",
        "--lora",
        dest="weights_path",
        type=Path,
        help=(
            "FNF-OMNI-VIDEO-V1 .safetensors weights; defaults to "
            "models/FNF-OMNI-VIDEO-V1/fnf-omni-video-v1.safetensors"
        ),
    )
    parser.add_argument("--output", type=Path, default=Path("fnf_video.mp4"))
    parser.add_argument("--fps", type=int, choices=(24, 30, 60), default=24)
    parser.add_argument("--size", type=int, default=512, help="square output size")
    parser.add_argument("--chunk-size", type=int, default=16)
    parser.add_argument(
        "--duration-seconds", type=float, help="optional preview duration cap"
    )
    parser.add_argument("--tail-ms", type=float, default=1000.0)
    parser.add_argument("--pose-hold-ms", type=float, default=180.0)
    parser.add_argument("--approach-ms", type=float, default=1600.0)
    parser.add_argument(
        "--guides-dir", type=Path, help="also save ControlNet guide PNGs"
    )
    parser.add_argument(
        "--pose-preview",
        action="store_true",
        help="skip model loading and use the pose guides as the video background",
    )
    parser.add_argument(
        "--sneak-peek",
        action="store_true",
        help="export a fast FNF-OMNI-PREVIEW-LITE PNG storyboard or GIF",
    )
    parser.add_argument(
        "--preview-output",
        type=Path,
        default=Path("fnf_sneak_peek.png"),
        help="sneak peek output ending in .png or .gif",
    )
    parser.add_argument("--preview-size", type=int, default=384)
    parser.add_argument("--preview-max-frames", type=int, default=12)
    parser.add_argument("--preview-columns", type=int, default=3)
    parser.add_argument("--preview-beat-stride", type=int, default=4)
    parser.add_argument("--preview-fps", type=float, default=2.0)
    parser.add_argument(
        "--preview-camera", choices=("wide", "medium", "close"), default="wide"
    )
    parser.add_argument("--preview-style", default="neon rhythm stage")

    parser.add_argument(
        "--base-model", default="stable-diffusion-v1-5/stable-diffusion-v1-5"
    )
    parser.add_argument(
        "--motion-adapter", default="guoyww/animatediff-motion-adapter-v1-5-2"
    )
    parser.add_argument(
        "--controlnet-model", default="lllyasviel/sd-controlnet-openpose"
    )
    parser.add_argument(
        "--weights-scale",
        "--lora-scale",
        dest="weights_scale",
        type=float,
        default=0.8,
    )
    parser.add_argument("--inference-steps", type=int, default=25)
    parser.add_argument("--guidance-scale", type=float, default=7.5)
    parser.add_argument("--controlnet-scale", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument(
        "--prompt",
        default=(
            "Friday Night Funkin style rhythm battle, two full body cartoon singers, "
            "bold outlines, colorful stage, game animation, centered composition"
        ),
    )
    parser.add_argument(
        "--negative-prompt",
        default=(
            "interface, HUD, arrows, text, logo, watermark, blurry, malformed hands, "
            "extra limbs, cropped character"
        ),
    )
    parser.add_argument("--verbose", action="store_true")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.size < 256 or args.size % 8:
        parser.error("--size must be at least 256 and divisible by 8")
    if args.chunk_size <= 0:
        parser.error("--chunk-size must be positive")
    if args.duration_seconds is not None and args.duration_seconds <= 0:
        parser.error("--duration-seconds must be positive")
    if args.inference_steps <= 0:
        parser.error("--inference-steps must be positive")
    if args.pose_hold_ms < 0:
        parser.error("--pose-hold-ms cannot be negative")
    if args.approach_ms <= 0:
        parser.error("--approach-ms must be positive")
    if args.preview_size < 128:
        parser.error("--preview-size must be at least 128")
    if args.preview_max_frames <= 0:
        parser.error("--preview-max-frames must be positive")
    if args.preview_columns <= 0:
        parser.error("--preview-columns must be positive")
    if args.preview_beat_stride <= 0:
        parser.error("--preview-beat-stride must be positive")
    if not math.isfinite(args.preview_fps) or args.preview_fps <= 0:
        parser.error("--preview-fps must be positive")
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )
    if args.sneak_peek:
        render_sneak_peek(args)
        return 0
    if (
        not args.pose_preview
        and args.weights_path is None
        and not DEFAULT_WEIGHTS_PATH.is_file()
    ):
        LOGGER.warning(
            "%s weights are not installed; run models/download_weights.py or "
            "pass --weights. Generation will use the base checkpoint style.",
            ARCHITECTURE_NAME,
        )
    render_video(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
