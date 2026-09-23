"""Fast storyboard generator for the FNF-OMNI-PREVIEW-LITE architecture."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Sequence, Set, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw

PREVIEW_ARCHITECTURE_NAME = "FNF-OMNI-PREVIEW-LITE"


@dataclass(frozen=True)
class FNFOmniPreviewConfig:
    """Rendering controls for a lightweight storyboard or animated preview."""

    size: int = 384
    max_frames: int = 12
    columns: int = 3
    beat_stride: int = 4
    gif_fps: float = 2.0
    camera_angle: str = "wide"
    background_style: str = "neon rhythm stage"
    architecture: str = PREVIEW_ARCHITECTURE_NAME

    def validate(self) -> None:
        if self.architecture != PREVIEW_ARCHITECTURE_NAME:
            raise ValueError(f"expected architecture {PREVIEW_ARCHITECTURE_NAME!r}")
        if self.size < 128:
            raise ValueError("preview size must be at least 128 pixels")
        if self.max_frames <= 0:
            raise ValueError("preview max frames must be positive")
        if self.columns <= 0:
            raise ValueError("preview columns must be positive")
        if self.beat_stride <= 0:
            raise ValueError("preview beat stride must be positive")
        if not math.isfinite(self.gif_fps) or self.gif_fps <= 0:
            raise ValueError("preview GIF FPS must be positive")
        if self.camera_angle not in {"wide", "medium", "close"}:
            raise ValueError("preview camera must be wide, medium, or close")


@dataclass(frozen=True)
class PreviewKeyframe:
    time_ms: float
    reasons: Tuple[str, ...]


class FNFOmniPreviewEngine:
    """Generate key-beat storyboards without loading the diffusion pipeline."""

    CAMERA_CROPS = {
        "wide": (0.0, 0.0, 1.0, 1.0),
        "medium": (0.08, 0.08, 0.92, 0.92),
        "close": (0.18, 0.08, 0.82, 0.72),
    }

    def __init__(
        self,
        timeline: Any,
        pose_renderer: Any,
        hud_compositor: Any,
        config: FNFOmniPreviewConfig,
    ):
        config.validate()
        self.timeline = timeline
        self.pose_renderer = pose_renderer
        self.hud_compositor = hud_compositor
        self.config = config

    @staticmethod
    def _even_sample(
        items: Sequence[PreviewKeyframe], count: int
    ) -> List[PreviewKeyframe]:
        if count <= 0 or not items:
            return []
        if len(items) <= count:
            return list(items)
        if count == 1:
            return [items[0]]
        indices = {
            round(index * (len(items) - 1) / (count - 1)) for index in range(count)
        }
        return [items[index] for index in sorted(indices)]

    def select_keyframes(self) -> List[PreviewKeyframe]:
        """Prioritize section/BPM boundaries, then fill with periodic song beats."""

        candidates: Dict[int, Tuple[float, Set[str], int]] = {}

        def add(time_ms: float, reason: str, priority: int) -> None:
            final_frame_ms = max(
                0.0, self.timeline.duration_ms - (1000.0 / self.timeline.fps)
            )
            clamped = min(max(0.0, time_ms), final_frame_ms)
            key = int(round(clamped))
            if key not in candidates:
                candidates[key] = (clamped, set(), priority)
            saved_time, reasons, saved_priority = candidates[key]
            reasons.add(reason)
            candidates[key] = (saved_time, reasons, min(priority, saved_priority))

        add(0.0, "song start", 0)
        previous_must_hit = None
        for section in self.timeline.sections:
            singer = "player" if section.must_hit else "opponent"
            is_turn_switch = (
                previous_must_hit is not None and section.must_hit != previous_must_hit
            )
            priority = 0 if is_turn_switch else 1
            reason = (
                f"turn switch: {singer}"
                if is_turn_switch
                else f"section {section.section_index + 1}: {singer}"
            )
            add(section.start_ms, reason, priority)
            previous_must_hit = section.must_hit
        for segment in self.timeline.bpm_segments:
            add(segment.start_ms, f"BPM {segment.bpm:g}", 0)

        for index, segment in enumerate(self.timeline.bpm_segments):
            segment_end = (
                self.timeline.bpm_segments[index + 1].start_ms
                if index + 1 < len(self.timeline.bpm_segments)
                else self.timeline.duration_ms
            )
            interval_ms = (60000.0 / segment.bpm) * self.config.beat_stride
            beat_ms = segment.start_ms
            while beat_ms < segment_end:
                add(beat_ms, "key beat", 2)
                beat_ms += interval_ms

        add(self.timeline.duration_ms, "song end", 1)
        keyframes = [
            PreviewKeyframe(time_ms, tuple(sorted(reasons)))
            for time_ms, reasons, _priority in candidates.values()
        ]
        priorities = {
            int(round(time_ms)): priority
            for time_ms, _reasons, priority in candidates.values()
        }
        keyframes.sort(key=lambda frame: frame.time_ms)
        selected: List[PreviewKeyframe] = []
        for priority in sorted(set(priorities.values())):
            remaining = self.config.max_frames - len(selected)
            if remaining <= 0:
                break
            group = [
                frame
                for frame in keyframes
                if priorities[int(round(frame.time_ms))] == priority
            ]
            selected.extend(self._even_sample(group, remaining))
        return sorted(selected, key=lambda frame: frame.time_ms)

    def _background(self) -> Image.Image:
        digest = hashlib.sha256(self.config.background_style.encode("utf-8")).digest()
        top = np.array([24 + digest[0] % 72, 18 + digest[1] % 52, 48 + digest[2] % 96])
        bottom = np.array(
            [12 + digest[3] % 48, 12 + digest[4] % 48, 20 + digest[5] % 64]
        )
        mix = np.linspace(0.0, 1.0, self.config.size, dtype=np.float32)[:, None]
        rows = top * (1.0 - mix) + bottom * mix
        pixels = np.repeat(rows[:, None, :], self.config.size, axis=1).astype(np.uint8)
        image = Image.fromarray(pixels)
        draw = ImageDraw.Draw(image, "RGBA")
        width = self.config.size
        horizon = int(width * 0.68)
        draw.rectangle((0, horizon, width, width), fill=(15, 15, 24, 255))
        draw.polygon(
            ((0, 0), (int(width * 0.42), horizon), (int(width * 0.22), horizon)),
            fill=(255, 255, 255, 22),
        )
        draw.polygon(
            ((width, 0), (int(width * 0.58), horizon), (int(width * 0.78), horizon)),
            fill=(255, 255, 255, 22),
        )
        for offset in range(0, width, max(16, width // 12)):
            draw.line((width // 2, horizon, offset, width), fill=(255, 255, 255, 18))
        return image

    def _apply_camera(self, pose: Image.Image) -> Image.Image:
        left, top, right, bottom = self.CAMERA_CROPS[self.config.camera_angle]
        size = pose.width
        crop = pose.crop(
            (
                round(left * size),
                round(top * size),
                round(right * size),
                round(bottom * size),
            )
        )
        return crop.resize(
            (self.config.size, self.config.size), Image.Resampling.LANCZOS
        )

    @staticmethod
    def _wrap_text(draw: ImageDraw.ImageDraw, text: str, max_width: int) -> List[str]:
        """Wrap a label to the available pixel width using Pillow's active font."""

        words = text.split()
        lines: List[str] = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if draw.textbbox((0, 0), candidate)[2] <= max_width:
                current = candidate
                continue
            if current:
                lines.append(current)
                current = ""
            if draw.textbbox((0, 0), word)[2] <= max_width:
                current = word
                continue
            shortened = word
            while shortened and draw.textbbox((0, 0), f"{shortened}...")[2] > max_width:
                shortened = shortened[:-1]
            lines.append(f"{shortened}..." if shortened else "...")
        if current:
            lines.append(current)
        return lines or [""]

    def render_keyframe(self, keyframe: PreviewKeyframe) -> Image.Image:
        pose = self._apply_camera(self.pose_renderer.render(keyframe.time_ms))
        background = np.asarray(self._background()).copy()
        pose_pixels = np.asarray(pose.convert("RGB"))
        pose_mask = np.max(pose_pixels, axis=2) > 12
        background[pose_mask] = pose_pixels[pose_mask]
        composed_bgr = self.hud_compositor.compose(
            Image.fromarray(background), keyframe.time_ms
        )
        composed = Image.fromarray(cv2.cvtColor(composed_bgr, cv2.COLOR_BGR2RGB))

        seconds = keyframe.time_ms / 1000.0
        reason = ", ".join(keyframe.reasons)
        measure = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        text_width = self.config.size - 16
        label_lines = [f"{seconds:06.2f}s | {self.config.camera_angle}"]
        label_lines.extend(self._wrap_text(measure, reason, text_width))
        label_lines.extend(
            self._wrap_text(
                measure, f"style: {self.config.background_style[:64]}", text_width
            )
        )
        line_height = max(12, measure.textbbox((0, 0), "Ag")[3] + 3)
        footer_height = max(48, 8 + line_height * len(label_lines))
        card = Image.new(
            "RGB", (self.config.size, self.config.size + footer_height), (12, 12, 18)
        )
        card.paste(composed, (0, 0))
        draw = ImageDraw.Draw(card)
        for index, line in enumerate(label_lines):
            color = (170, 205, 255) if line.startswith("style:") else (255, 255, 255)
            draw.text(
                (8, self.config.size + 5 + index * line_height),
                line,
                fill=color,
            )
        return card

    def _save_contact_sheet(
        self, frames: Sequence[Image.Image], output_path: Path
    ) -> None:
        columns = min(self.config.columns, len(frames))
        rows = math.ceil(len(frames) / columns)
        margin = 12
        header = 42
        card_width, card_height = frames[0].size
        sheet = Image.new(
            "RGB",
            (
                columns * card_width + (columns + 1) * margin,
                rows * card_height + (rows + 1) * margin + header,
            ),
            (7, 7, 12),
        )
        draw = ImageDraw.Draw(sheet)
        draw.text(
            (margin, margin),
            f"{PREVIEW_ARCHITECTURE_NAME} | {self.timeline.song_name}",
            fill=(255, 255, 255),
        )
        for index, frame in enumerate(frames):
            column = index % columns
            row = index // columns
            x = margin + column * (card_width + margin)
            y = margin + header + row * (card_height + margin)
            sheet.paste(frame, (x, y))
        sheet.save(output_path, format="PNG")

    def _save_gif(self, frames: Sequence[Image.Image], output_path: Path) -> None:
        duration_ms = max(1, round(1000.0 / self.config.gif_fps))
        frames[0].save(
            output_path,
            format="GIF",
            save_all=True,
            append_images=list(frames[1:]),
            duration=duration_ms,
            loop=0,
            disposal=2,
        )

    def export(self, output_path: Path) -> List[PreviewKeyframe]:
        """Render selected keyframes to a PNG contact sheet or animated GIF."""

        output_path = output_path.expanduser().resolve()
        suffix = output_path.suffix.lower()
        if suffix not in {".png", ".gif"}:
            raise ValueError("sneak peek output must end in .png or .gif")
        keyframes = self.select_keyframes()
        if not keyframes:
            raise RuntimeError("no preview keyframes were selected")
        frames = [self.render_keyframe(keyframe) for keyframe in keyframes]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if suffix == ".gif":
            self._save_gif(frames, output_path)
        else:
            self._save_contact_sheet(frames, output_path)
        return keyframes
