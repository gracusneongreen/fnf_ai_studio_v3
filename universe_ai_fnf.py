#!/usr/bin/env python3
"""UNIVERSE-AI-FNF: a multi-skill Friday Night Funkin' model.

The model is a deterministic skill router.  Each skill consumes the parsed
chart timeline (plus an optional reference image and song audio) and writes
inspectable artifacts:

``eyes``          vision pass over a reference frame, palette extraction
``audio``         beat grid, hit windows, and per-beat loudness
``hands``         per-note wrist/hand targets for animation and capture
``coder``         Psych Engine Lua generated from the chart structure
``draw``          FNF-style sprite sheet, Sparrow atlas, and health icons
``mods``          a complete installable Psych Engine mod folder
``computer_use``  GUI action plan and launch script for an automated playtest
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import shutil
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Type

import numpy as np
from PIL import Image, ImageDraw

from fnf_video_engine import (
    DIRECTIONS,
    SINGERS,
    ChartTimeline,
    PoseGuideRenderer,
    limit_timeline,
    parse_chart,
)

LOGGER = logging.getLogger("universe-ai-fnf")
UNIVERSE_ARCHITECTURE_NAME = "UNIVERSE-AI-FNF"
MODEL_ROOT = Path(__file__).resolve().parent / "models" / UNIVERSE_ARCHITECTURE_NAME
MANIFEST_PATH = MODEL_ROOT / "model_manifest.json"

# BODY_18 wrist indices used by PoseGuideRenderer.
RIGHT_WRIST = 4
LEFT_WRIST = 7
DEFAULT_PALETTE: Tuple[Tuple[int, int, int], ...] = (
    (49, 176, 209),  # boyfriend hair cyan
    (168, 55, 98),  # shirt magenta
    (247, 200, 166),  # skin
    (33, 34, 48),  # outline navy
    (255, 255, 255),  # highlight
)


@dataclass(frozen=True)
class UniverseAIFNFConfig:
    """Skill selection and asset naming for one UNIVERSE-AI-FNF run."""

    skills: Tuple[str, ...]
    mod_name: str = "UniverseAI"
    character_name: str = "universe-bf"
    art_style: str = "fnf bold outline cel shading"
    sprite_size: int = 256
    seed: int = 1337
    reference_image: Optional[Path] = None
    audio_path: Optional[Path] = None
    architecture: str = UNIVERSE_ARCHITECTURE_NAME

    def validate(self) -> None:
        if self.architecture != UNIVERSE_ARCHITECTURE_NAME:
            raise ValueError(f"expected architecture {UNIVERSE_ARCHITECTURE_NAME!r}")
        if not self.skills:
            raise ValueError("at least one skill must be selected")
        unknown = [skill for skill in self.skills if skill not in SKILL_REGISTRY]
        if unknown:
            raise ValueError(f"unknown skills: {', '.join(sorted(unknown))}")
        if self.sprite_size < 128 or self.sprite_size % 2:
            raise ValueError("sprite size must be even and at least 128 pixels")
        if not self.mod_name or any(character in self.mod_name for character in "/\\"):
            raise ValueError("mod name must be a non-empty single path segment")
        if not self.character_name or any(
            character in self.character_name for character in "/\\"
        ):
            raise ValueError("character name must be a non-empty single path segment")


@dataclass(frozen=True)
class SkillResult:
    skill: str
    summary: str
    data: Dict[str, Any]
    artifacts: Tuple[Path, ...] = ()


@dataclass
class UniverseSession:
    """Shared state handed to every skill during a run."""

    timeline: ChartTimeline
    config: UniverseAIFNFConfig
    output_dir: Path
    results: Dict[str, SkillResult] = field(default_factory=dict)

    def directory(self, name: str) -> Path:
        path = self.output_dir / name
        path.mkdir(parents=True, exist_ok=True)
        return path

    def data_of(self, skill: str) -> Dict[str, Any]:
        if skill not in self.results:
            raise KeyError(f"skill {skill!r} has not run yet")
        return self.results[skill].data


class UniverseSkill:
    """One capability of the model."""

    name = ""
    requires: Tuple[str, ...] = ()

    def __init__(self, session: UniverseSession):
        self.session = session

    @property
    def timeline(self) -> ChartTimeline:
        return self.session.timeline

    @property
    def config(self) -> UniverseAIFNFConfig:
        return self.session.config

    def run(self) -> SkillResult:
        raise NotImplementedError


def _write_json(path: Path, payload: Dict[str, Any]) -> Path:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


class EyesSkill(UniverseSkill):
    """Read a reference frame and derive the palette the artist skills use."""

    name = "eyes"
    PALETTE_SIZE = 5

    def _source_image(self) -> Tuple[Image.Image, str]:
        reference = self.config.reference_image
        if reference is not None:
            path = reference.expanduser().resolve()
            if not path.is_file():
                raise FileNotFoundError(f"reference image not found: {path}")
            with Image.open(path) as image:
                return image.convert("RGB"), str(path)
        renderer = PoseGuideRenderer(self.timeline, self.config.sprite_size)
        return renderer.render(0.0), "pose_guide:0ms"

    def _palette(self, image: Image.Image) -> List[Tuple[int, int, int]]:
        thumbnail = image.resize((64, 64), Image.Resampling.BILINEAR)
        quantized = thumbnail.quantize(
            colors=self.PALETTE_SIZE, method=Image.Quantize.MEDIANCUT
        )
        raw_palette = quantized.getpalette() or []
        counts = sorted(quantized.getcolors() or [], key=lambda item: -item[0])
        palette: List[Tuple[int, int, int]] = []
        for _count, index in counts:
            start = index * 3
            channels = raw_palette[start:start + 3]
            if len(channels) == 3:
                palette.append((channels[0], channels[1], channels[2]))
        while len(palette) < self.PALETTE_SIZE:
            palette.append(DEFAULT_PALETTE[len(palette) % len(DEFAULT_PALETTE)])
        return palette[: self.PALETTE_SIZE]

    def _swatch(self, palette: Sequence[Tuple[int, int, int]], path: Path) -> Path:
        cell = 64
        image = Image.new("RGB", (cell * len(palette), cell), (12, 12, 18))
        draw = ImageDraw.Draw(image)
        for index, color in enumerate(palette):
            draw.rectangle((index * cell, 0, (index + 1) * cell - 1, cell - 1), color)
        image.save(path, format="PNG")
        return path

    def run(self) -> SkillResult:
        image, source = self._source_image()
        palette = self._palette(image)
        pixels = np.asarray(image, dtype=np.float32)
        luminance = pixels @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
        directory = self.session.directory("eyes")
        swatch = self._swatch(palette, directory / "palette.png")
        data: Dict[str, Any] = {
            "source": source,
            "resolution": [image.width, image.height],
            "palette": [list(color) for color in palette],
            "palette_hex": ["#%02x%02x%02x" % color for color in palette],
            "brightness": round(float(luminance.mean()) / 255.0, 4),
            "contrast": round(float(luminance.std()) / 255.0, 4),
            "subject_coverage": round(float((luminance > 24.0).mean()), 4),
        }
        report = _write_json(directory / "vision.json", data)
        return SkillResult(
            skill=self.name,
            summary=(
                f"read {source} and extracted {len(palette)} palette colors "
                f"(brightness {data['brightness']:.2f})"
            ),
            data=data,
            artifacts=(swatch, report),
        )


class AudioSkill(UniverseSkill):
    """Turn chart timing, and optional song audio, into a beat-accurate map."""

    name = "audio"

    def _beats(self) -> List[Dict[str, Any]]:
        beats: List[Dict[str, Any]] = []
        segments = self.timeline.bpm_segments
        for index, segment in enumerate(segments):
            end_ms = (
                segments[index + 1].start_ms
                if index + 1 < len(segments)
                else self.timeline.duration_ms
            )
            beat_ms = 60000.0 / segment.bpm
            position = segment.start_ms
            beat_number = 0
            while position < end_ms:
                beats.append(
                    {
                        "time_ms": round(position, 3),
                        "bpm": segment.bpm,
                        "downbeat": beat_number % 4 == 0,
                    }
                )
                position += beat_ms
                beat_number += 1
        return beats

    def _loudness(self, beats: Sequence[Dict[str, Any]]) -> Optional[List[float]]:
        audio_path = self.config.audio_path
        if audio_path is None:
            return None
        path = audio_path.expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"audio file not found: {path}")
        if path.suffix.lower() != ".wav":
            raise ValueError("audio analysis supports uncompressed .wav input")
        with wave.open(str(path), "rb") as handle:
            if handle.getsampwidth() != 2:
                raise ValueError("audio analysis supports 16-bit PCM WAV input")
            rate = handle.getframerate()
            channels = handle.getnchannels()
            samples = np.frombuffer(
                handle.readframes(handle.getnframes()), dtype="<i2"
            ).astype(np.float32)
        if channels > 1:
            samples = samples.reshape(-1, channels).mean(axis=1)
        window = max(1, int(rate * 0.05))
        loudness: List[float] = []
        for beat in beats:
            start = int(beat["time_ms"] * rate / 1000.0)
            chunk = samples[start:start + window]
            if chunk.size == 0:
                loudness.append(0.0)
                continue
            loudness.append(
                round(float(np.sqrt(np.mean(np.square(chunk)))) / 32768.0, 5)
            )
        return loudness

    def run(self) -> SkillResult:
        beats = self._beats()
        loudness = self._loudness(beats)
        if loudness is not None:
            for beat, value in zip(beats, loudness):
                beat["rms"] = value
        lane_histogram = {
            direction: sum(
                1 for note in self.timeline.notes if note.direction == index
            )
            for index, direction in enumerate(DIRECTIONS)
        }
        step_ms = 15000.0 / self.timeline.initial_bpm
        data: Dict[str, Any] = {
            "song": self.timeline.song_name,
            "duration_ms": round(self.timeline.duration_ms, 3),
            "initial_bpm": self.timeline.initial_bpm,
            "bpm_changes": [
                {"time_ms": round(segment.start_ms, 3), "bpm": segment.bpm}
                for segment in self.timeline.bpm_segments
            ],
            "beat_count": len(beats),
            "beats": beats,
            "lane_histogram": lane_histogram,
            "notes_per_singer": {
                singer: sum(1 for note in self.timeline.notes if note.singer == singer)
                for singer in SINGERS
            },
            # Psych-style windows scale with the step of the opening tempo.
            "hit_windows_ms": {
                "sick": round(step_ms * 0.30, 2),
                "good": round(step_ms * 0.55, 2),
                "bad": round(step_ms * 0.80, 2),
                "shit": round(step_ms, 2),
            },
            "loudness_source": (
                str(self.config.audio_path.expanduser().resolve())
                if self.config.audio_path is not None
                else None
            ),
        }
        artifact = _write_json(self.session.directory("audio") / "beatmap.json", data)
        return SkillResult(
            skill=self.name,
            summary=(
                f"mapped {len(beats)} beats across "
                f"{len(self.timeline.bpm_segments)} tempo segment(s)"
            ),
            data=data,
            artifacts=(artifact,),
        )


class HandsSkill(UniverseSkill):
    """Emit per-note wrist targets so hands land exactly on the beat."""

    name = "hands"
    requires = ("audio",)

    def _targets(self) -> List[Dict[str, Any]]:
        renderer = PoseGuideRenderer(self.timeline, self.config.sprite_size)
        targets: List[Dict[str, Any]] = []
        for note in self.timeline.notes:
            points = renderer.body_points(note.singer, note.direction, note.time_ms)
            left = points[LEFT_WRIST]
            right = points[RIGHT_WRIST]
            targets.append(
                {
                    "time_ms": round(note.time_ms, 3),
                    "frame": note.frame,
                    "singer": note.singer,
                    "direction": DIRECTIONS[note.direction],
                    "sustain_ms": round(note.sustain_ms, 3),
                    "left_hand": [round(left[0], 4), round(left[1], 4)],
                    "right_hand": [round(right[0], 4), round(right[1], 4)],
                    # The arm that actually travels for this arrow.
                    "lead_hand": "left" if note.direction in (0, 2) else "right",
                }
            )
        return targets

    def _trails(self, targets: Sequence[Dict[str, Any]], path: Path) -> Path:
        size = self.config.sprite_size
        image = Image.new("RGB", (size, size), (10, 10, 16))
        draw = ImageDraw.Draw(image)
        radius = max(2, size // 90)
        per_singer: Dict[str, List[Tuple[float, float]]] = {
            singer: [] for singer in SINGERS
        }
        for target in targets:
            hand = target[f"{target['lead_hand']}_hand"]
            per_singer[target["singer"]].append((hand[0] * size, hand[1] * size))
        colors = {"player": (120, 230, 255), "opponent": (255, 140, 190)}
        for singer, points in per_singer.items():
            if len(points) > 1:
                draw.line(points, fill=colors[singer], width=max(1, size // 200))
            for x, y in points:
                draw.ellipse(
                    (x - radius, y - radius, x + radius, y + radius),
                    fill=colors[singer],
                )
        image.save(path, format="PNG")
        return path

    def run(self) -> SkillResult:
        directory = self.session.directory("hands")
        targets = self._targets()
        track = _write_json(
            directory / "hand_track.json",
            {
                "song": self.timeline.song_name,
                "fps": self.timeline.fps,
                "space": "normalized_xy",
                "targets": targets,
            },
        )
        trails = self._trails(targets, directory / "hand_trails.png")
        return SkillResult(
            skill=self.name,
            summary=f"solved {len(targets)} wrist targets from chart notes",
            data={"target_count": len(targets), "targets": targets},
            artifacts=(track, trails),
        )


class CoderSkill(UniverseSkill):
    """Generate Psych Engine Lua that reacts to this chart's structure."""

    name = "coder"

    def _lua(self) -> str:
        bpm_changes = [
            f"\t[{index}] = {{time = {segment.start_ms:.1f}, bpm = {segment.bpm:g}}},"
            for index, segment in enumerate(self.timeline.bpm_segments)
        ]
        switches = []
        previous: Optional[bool] = None
        for section in self.timeline.sections:
            if previous is not None and section.must_hit != previous:
                singer = "player" if section.must_hit else "opponent"
                switches.append(
                    f"\t{{time = {section.start_ms:.1f}, focus = '{singer}'}},"
                )
            previous = section.must_hit
        lines = [
            "-- Generated by UNIVERSE-AI-FNF (coder skill). Do not edit by hand.",
            f"-- song: {self.timeline.song_name}",
            "",
            "local tempoMap = {",
            *bpm_changes,
            "}",
            "",
            "local cameraCues = {",
            *switches,
            "}",
            "",
            "local nextCue = 1",
            "",
            "function onCreate()",
            f"\tsetProperty('defaultCamZoom', {1.05:.2f})",
            "\tfor _, cue in pairs(tempoMap) do",
            "\t\tdebugPrint('tempo ' .. cue.bpm .. ' at ' .. cue.time)",
            "\tend",
            "end",
            "",
            "function onUpdate(elapsed)",
            "\tlocal cue = cameraCues[nextCue]",
            "\tif cue ~= nil and getSongPosition() >= cue.time then",
            "\t\ttriggerEvent('Camera Follow Pos', '', '')",
            "\t\tcameraSetTarget(cue.focus)",
            "\t\tnextCue = nextCue + 1",
            "\tend",
            "end",
            "",
            "function onBeatHit()",
            "\tif curBeat % 4 == 0 then",
            "\t\ttriggerEvent('Add Camera Zoom', '0.03', '0.03')",
            "\tend",
            "end",
            "",
            "function goodNoteHit(id, direction, noteType, isSustain)",
            "\tif noteType == 'Alt Animation' then",
            "\t\tcharacterPlayAnim('boyfriend', singAnimations[direction + 1] "
            ".. '-alt', true)",
            "\tend",
            "end",
            "",
        ]
        return "\n".join(lines)

    def run(self) -> SkillResult:
        script = self._lua()
        path = self.session.directory("coder") / "universe.lua"
        path.write_text(script, encoding="utf-8")
        hooks = [
            line.split("(")[0].removeprefix("function ").strip()
            for line in script.splitlines()
            if line.startswith("function ")
        ]
        data = {
            "language": "lua",
            "target": "psych_engine",
            "hooks": hooks,
            "line_count": len(script.splitlines()),
        }
        return SkillResult(
            skill=self.name,
            summary=f"generated {data['line_count']} lines of Lua ({len(hooks)} hooks)",
            data=data,
            artifacts=(path,),
        )


class DrawSkill(UniverseSkill):
    """Draw the character in FNF style: flat cel fills and heavy outlines."""

    name = "draw"
    requires = ("eyes",)
    POSES = ("idle", "singLEFT", "singDOWN", "singUP", "singRIGHT")

    @staticmethod
    def _saturation(color: Sequence[int]) -> int:
        return max(color) - min(color)

    def _colors(self) -> Dict[str, Tuple[int, int, int]]:
        palette: List[Tuple[int, int, int]] = [
            (color[0], color[1], color[2])
            for color in self.session.data_of("eyes")["palette"]
        ]
        while len(palette) < 5:
            palette.append(DEFAULT_PALETTE[len(palette)])
        # Saturated reference colors read as hair and clothing in FNF art;
        # the lightest flat color becomes skin and the rest is trim.
        vivid = sorted(palette, key=self._saturation, reverse=True)
        skin = max(palette, key=lambda color: sum(color) + self._saturation(color) // 2)
        remaining = [color for color in vivid if color != skin] or vivid
        return {
            "outline": (18, 18, 28),
            "hair": remaining[0],
            "shirt": remaining[min(1, len(remaining) - 1)],
            "accent": remaining[min(2, len(remaining) - 1)],
            "skin": skin,
        }

    def _draw_pose(
        self, pose: str, colors: Dict[str, Tuple[int, int, int]]
    ) -> Image.Image:
        size = self.config.sprite_size
        direction = None if pose == "idle" else DIRECTIONS.index(pose[4:].lower())
        renderer = PoseGuideRenderer(self.timeline, size)
        points = renderer.body_points("player", direction, 0.0)
        # Re-center the player-side skeleton inside its own sprite cell.
        shift = 0.71 - 0.5
        scaled = [((x - shift) * size, y * size) for x, y in points]
        cell = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(cell)
        limb = max(6, size // 18)
        outline = limb + max(4, size // 32)

        def bone(start: int, end: int, color: Tuple[int, int, int]) -> None:
            draw.line(
                (scaled[start], scaled[end]),
                fill=colors["outline"],
                width=outline,
                joint="curve",
            )
            draw.line(
                (scaled[start], scaled[end]), fill=color, width=limb, joint="curve"
            )

        for start, end in ((8, 9), (9, 10), (11, 12), (12, 13)):
            bone(start, end, colors["accent"])
        draw.polygon(
            (scaled[2], scaled[5], scaled[11], scaled[8]), fill=colors["outline"]
        )
        for start, end in ((2, 3), (3, 4), (5, 6), (6, 7)):
            bone(start, end, colors["shirt"])
        torso = [scaled[2], scaled[5], scaled[11], scaled[8]]
        inset = limb * 0.35
        draw.polygon(
            [
                (torso[0][0] + inset, torso[0][1] + inset),
                (torso[1][0] - inset, torso[1][1] + inset),
                (torso[2][0] - inset, torso[2][1] - inset),
                (torso[3][0] + inset, torso[3][1] - inset),
            ],
            fill=colors["shirt"],
        )
        for index in (4, 7):
            x, y = scaled[index]
            draw.ellipse(
                (x - limb, y - limb, x + limb, y + limb),
                fill=colors["skin"],
                outline=colors["outline"],
                width=max(2, size // 90),
            )

        head_radius = size * 0.105
        head_x, head_y = scaled[0][0], scaled[0][1] - head_radius * 0.35
        draw.ellipse(
            (
                head_x - head_radius,
                head_y - head_radius,
                head_x + head_radius,
                head_y + head_radius,
            ),
            fill=colors["skin"],
            outline=colors["outline"],
            width=max(3, size // 64),
        )
        draw.pieslice(
            (
                head_x - head_radius,
                head_y - head_radius * 1.35,
                head_x + head_radius,
                head_y + head_radius * 0.5,
            ),
            start=180,
            end=360,
            fill=colors["hair"],
            outline=colors["outline"],
            width=max(3, size // 64),
        )
        eye_offset = head_radius * (0.0 if direction is None else 0.22)
        if direction == 0:
            eye_offset = -head_radius * 0.3
        elif direction == 3:
            eye_offset = head_radius * 0.3
        for side in (-1, 1):
            eye_x = head_x + side * head_radius * 0.38 + eye_offset
            eye_y = head_y - head_radius * 0.1
            radius = head_radius * 0.15
            draw.ellipse(
                (eye_x - radius, eye_y - radius, eye_x + radius, eye_y + radius),
                fill=colors["outline"],
            )
        mouth_open = head_radius * (0.5 if direction is not None else 0.22)
        draw.ellipse(
            (
                head_x - head_radius * 0.32,
                head_y + head_radius * 0.28,
                head_x + head_radius * 0.32,
                head_y + head_radius * 0.28 + mouth_open,
            ),
            fill=colors["outline"],
        )
        return cell

    def _sprite_sheet(self, colors: Dict[str, Tuple[int, int, int]]) -> Image.Image:
        size = self.config.sprite_size
        sheet = Image.new("RGBA", (size * len(self.POSES), size), (0, 0, 0, 0))
        for index, pose in enumerate(self.POSES):
            sheet.paste(self._draw_pose(pose, colors), (index * size, 0))
        return sheet

    def _atlas_xml(self) -> str:
        size = self.config.sprite_size
        entries = "\n".join(
            f'\t<SubTexture name="{pose}0000" x="{index * size}" y="0" '
            f'width="{size}" height="{size}" frameX="0" frameY="0" '
            f'frameWidth="{size}" frameHeight="{size}"/>'
            for index, pose in enumerate(self.POSES)
        )
        return (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            f'<TextureAtlas imagePath="{self.config.character_name}.png">\n'
            f"{entries}\n"
            "</TextureAtlas>\n"
        )

    def _icons(self, colors: Dict[str, Tuple[int, int, int]]) -> Image.Image:
        icons = Image.new("RGBA", (300, 150), (0, 0, 0, 0))
        head = self._draw_pose("idle", colors).resize(
            (150, 150), Image.Resampling.LANCZOS
        )
        icons.paste(head, (0, 0))
        losing = head.copy()
        pixels = np.asarray(losing).astype(np.float32)
        pixels[..., 0] = np.clip(pixels[..., 0] * 1.25, 0, 255)
        pixels[..., 1] *= 0.6
        pixels[..., 2] *= 0.6
        icons.paste(Image.fromarray(pixels.astype(np.uint8), "RGBA"), (150, 0))
        return icons

    def run(self) -> SkillResult:
        directory = self.session.directory("draw")
        colors = self._colors()
        sheet_path = directory / f"{self.config.character_name}.png"
        self._sprite_sheet(colors).save(sheet_path, format="PNG")
        xml_path = directory / f"{self.config.character_name}.xml"
        xml_path.write_text(self._atlas_xml(), encoding="utf-8")
        icon_path = directory / f"icon-{self.config.character_name}.png"
        self._icons(colors).save(icon_path, format="PNG")
        data = {
            "style": self.config.art_style,
            "poses": list(self.POSES),
            "sprite_size": self.config.sprite_size,
            "colors": {name: list(color) for name, color in colors.items()},
            "sheet": str(sheet_path),
            "atlas": str(xml_path),
            "icons": str(icon_path),
        }
        return SkillResult(
            skill=self.name,
            summary=(
                f"drew {len(self.POSES)} FNF poses plus a 150x150 health icon pair"
            ),
            data=data,
            artifacts=(sheet_path, xml_path, icon_path),
        )


class ModsSkill(UniverseSkill):
    """Assemble a full Psych Engine mod folder from the other skills' output."""

    name = "mods"
    requires = ("audio", "coder", "draw")

    def _song_id(self) -> str:
        cleaned = "".join(
            character if character.isalnum() else "-"
            for character in self.timeline.song_name.lower()
        )
        return "-".join(part for part in cleaned.split("-") if part) or "universe-song"

    def _character_json(self) -> Dict[str, Any]:
        size = self.config.sprite_size
        animations = [
            {
                "anim": pose,
                "name": f"{pose}0000",
                "fps": 24,
                "loop": pose == "idle",
                "indices": [],
                "offsets": [0, 0],
            }
            for pose in DrawSkill.POSES
        ]
        icon_colors = self.session.data_of("draw")["colors"]["hair"]
        return {
            "animations": animations,
            "image": f"characters/{self.config.character_name}",
            "position": [0, 0],
            "camera_position": [0, 0],
            "flip_x": False,
            "no_antialiasing": False,
            "healthicon": self.config.character_name,
            "healthbar_colors": icon_colors,
            "sing_duration": 4,
            "scale": round(size / 256.0, 3),
        }

    def _week_json(self, song_id: str) -> Dict[str, Any]:
        return {
            "songs": [[song_id, self.config.character_name, [255, 255, 255]]],
            "weekCharacters": ["dad", "bf", "gf"],
            "weekBackground": "stage",
            "weekBefore": "",
            "weekName": f"{self.config.mod_name} Week",
            "storyName": self.config.mod_name,
            "freeplayColor": self.session.data_of("draw")["colors"]["shirt"],
            "startUnlocked": True,
            "hiddenUntilUnlocked": False,
            "hideStoryMode": False,
            "hideFreeplay": False,
            "difficulties": "Easy, Normal, Hard",
        }

    def run(self) -> SkillResult:
        root = self.session.directory("mods") / self.config.mod_name
        song_id = self._song_id()
        audio = self.session.data_of("audio")
        draw = self.session.data_of("draw")
        for relative in (
            f"data/{song_id}",
            "characters",
            "images/characters",
            "images/icons",
            "scripts",
            "weeks",
        ):
            (root / relative).mkdir(parents=True, exist_ok=True)

        written: List[Path] = [
            _write_json(
                root / "pack.json",
                {
                    "name": self.config.mod_name,
                    "description": (
                        f"{UNIVERSE_ARCHITECTURE_NAME} generated mod for "
                        f"{self.timeline.song_name}"
                    ),
                    "restart": False,
                    "color": draw["colors"]["hair"],
                },
            ),
            _write_json(
                root / f"data/{song_id}/meta.json",
                {
                    "name": self.timeline.song_name,
                    "bpm": self.timeline.initial_bpm,
                    "duration_ms": audio["duration_ms"],
                    "hit_windows_ms": audio["hit_windows_ms"],
                    "generated_by": UNIVERSE_ARCHITECTURE_NAME,
                },
            ),
            _write_json(
                root / f"data/{song_id}/{song_id}.json",
                {
                    "song": {
                        "song": self.timeline.song_name,
                        "bpm": self.timeline.initial_bpm,
                        "speed": 1,
                        "player1": self.config.character_name,
                        "player2": "dad",
                        "gfVersion": "gf",
                        "stage": "stage",
                        "notes": [
                            {
                                "lengthInSteps": 16,
                                "mustHitSection": section.must_hit,
                                "bpm": section.bpm,
                                "changeBPM": index > 0
                                and not math.isclose(
                                    section.bpm,
                                    self.timeline.sections[index - 1].bpm,
                                ),
                                "sectionNotes": [
                                    [
                                        round(note.time_ms, 3),
                                        note.direction
                                        + (0 if note.singer == "player" else 4),
                                        round(note.sustain_ms, 3),
                                        note.note_type,
                                    ]
                                    for note in self.timeline.notes
                                    if section.start_ms <= note.time_ms < section.end_ms
                                ],
                            }
                            for index, section in enumerate(self.timeline.sections)
                        ],
                        "format": "psych_v1",
                    }
                },
            ),
            _write_json(
                root / f"characters/{self.config.character_name}.json",
                self._character_json(),
            ),
            _write_json(root / "weeks/universe.json", self._week_json(song_id)),
        ]

        characters = root / "images/characters"
        copies = (
            (Path(draw["sheet"]), characters / Path(draw["sheet"]).name),
            (Path(draw["atlas"]), characters / Path(draw["atlas"]).name),
            (Path(draw["icons"]), root / f"images/icons/{Path(draw['icons']).name}"),
            (
                self.session.results["coder"].artifacts[0],
                root / "scripts/universe.lua",
            ),
        )
        for source, destination in copies:
            shutil.copyfile(source, destination)
            written.append(destination)

        mods_list = root.parent / "modsList.txt"
        mods_list.write_text(f"{self.config.mod_name}|1\n", encoding="utf-8")
        written.append(mods_list)

        data = {
            "mod_name": self.config.mod_name,
            "song_id": song_id,
            "root": str(root),
            "files": [str(path) for path in written],
        }
        return SkillResult(
            skill=self.name,
            summary=f"packaged {len(written)} mod files under {root}",
            data=data,
            artifacts=tuple(written),
        )


class ComputerUseSkill(UniverseSkill):
    """Plan the GUI steps that install the mod and play the song end to end."""

    name = "computer_use"
    requires = ("mods",)

    def run(self) -> SkillResult:
        mods = self.session.data_of("mods")
        directory = self.session.directory("computer_use")
        steps: List[Dict[str, Any]] = [
            {
                "action": "shell",
                "command": (
                    f"cp -r '{mods['root']}' \"$FNF_GAME_DIR/mods/\""
                ),
                "why": "install the generated mod folder",
            },
            {
                "action": "launch",
                "target": "$FNF_GAME_DIR/FridayNightFunkin",
                "wait_ms": 8000,
            },
            {"action": "assert_screen", "expect": "title screen", "timeout_ms": 20000},
            {"action": "key", "keys": ["enter"], "why": "leave the title screen"},
            {"action": "key", "keys": ["enter"], "why": "dismiss the warning"},
            {"action": "key", "keys": ["right", "right"], "why": "select Freeplay"},
            {"action": "key", "keys": ["enter"]},
            {
                "action": "type_search",
                "text": self.timeline.song_name,
                "why": "find the generated song",
            },
            {"action": "key", "keys": ["enter"], "why": "start the song"},
            {
                "action": "wait",
                "duration_ms": int(round(self.timeline.duration_ms)),
                "why": "play the chart to the end",
            },
            {
                "action": "assert_screen",
                "expect": "results screen",
                "timeout_ms": 15000,
            },
            {
                "action": "screenshot",
                "path": "playtest_result.png",
                "why": "capture proof of the run",
            },
        ]
        plan = _write_json(
            directory / "actions.json",
            {
                "mod": mods["mod_name"],
                "song": self.timeline.song_name,
                "steps": steps,
            },
        )
        script = directory / "run_playtest.sh"
        script.write_text(
            "\n".join(
                (
                    "#!/usr/bin/env bash",
                    "# Generated by UNIVERSE-AI-FNF (computer_use skill).",
                    "set -euo pipefail",
                    ': "${FNF_GAME_DIR:?set FNF_GAME_DIR to the game install}"',
                    f"cp -r '{mods['root']}' \"$FNF_GAME_DIR/mods/\"",
                    f"cp '{Path(mods['root']).parent / 'modsList.txt'}' "
                    '"$FNF_GAME_DIR/modsList.txt"',
                    'cd "$FNF_GAME_DIR"',
                    "./FridayNightFunkin",
                    "",
                )
            ),
            encoding="utf-8",
        )
        script.chmod(0o755)
        data = {"step_count": len(steps), "steps": steps, "script": str(script)}
        return SkillResult(
            skill=self.name,
            summary=f"planned {len(steps)} GUI steps for an automated playtest",
            data=data,
            artifacts=(plan, script),
        )


SKILL_REGISTRY: Dict[str, Type[UniverseSkill]] = {
    skill.name: skill
    for skill in (
        EyesSkill,
        AudioSkill,
        HandsSkill,
        CoderSkill,
        DrawSkill,
        ModsSkill,
        ComputerUseSkill,
    )
}
ALL_SKILLS: Tuple[str, ...] = tuple(SKILL_REGISTRY)


def resolve_skill_order(requested: Sequence[str]) -> Tuple[str, ...]:
    """Expand requested skills with their prerequisites, in execution order."""

    unknown = [name for name in requested if name not in SKILL_REGISTRY]
    if unknown:
        raise ValueError(f"unknown skills: {', '.join(sorted(unknown))}")
    needed: set[str] = set()

    def visit(name: str, chain: Tuple[str, ...]) -> None:
        if name in chain:
            cycle = " -> ".join(chain + (name,))
            raise ValueError(f"circular skill dependency: {cycle}")
        if name in needed:
            return
        for requirement in SKILL_REGISTRY[name].requires:
            visit(requirement, chain + (name,))
        needed.add(name)

    for name in requested:
        visit(name, ())
    return tuple(name for name in ALL_SKILLS if name in needed)


@dataclass(frozen=True)
class UniverseRunReport:
    architecture: str
    song: str
    skills: Tuple[str, ...]
    results: Tuple[SkillResult, ...]
    output_dir: Path

    def to_dict(self) -> Dict[str, Any]:
        return {
            "architecture": self.architecture,
            "song": self.song,
            "skills": list(self.skills),
            "output_dir": str(self.output_dir),
            "results": [
                {
                    "skill": result.skill,
                    "summary": result.summary,
                    "artifacts": [str(path) for path in result.artifacts],
                    "data": result.data,
                }
                for result in self.results
            ],
        }


class UniverseAIFNF:
    """Router that executes the selected UNIVERSE-AI-FNF skills in order."""

    def __init__(self, timeline: ChartTimeline, config: UniverseAIFNFConfig):
        config.validate()
        self.timeline = timeline
        self.config = config

    @staticmethod
    def capabilities() -> Dict[str, Dict[str, Any]]:
        return {
            name: {
                "requires": list(skill.requires),
                "description": (skill.__doc__ or "").strip().splitlines()[0],
            }
            for name, skill in SKILL_REGISTRY.items()
        }

    def run(self, output_dir: Path) -> UniverseRunReport:
        output_dir = output_dir.expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        session = UniverseSession(self.timeline, self.config, output_dir)
        order = resolve_skill_order(self.config.skills)
        for name in order:
            LOGGER.info("Running skill %s", name)
            result = SKILL_REGISTRY[name](session).run()
            session.results[name] = result
            LOGGER.info("%s: %s", name, result.summary)
        report = UniverseRunReport(
            architecture=UNIVERSE_ARCHITECTURE_NAME,
            song=self.timeline.song_name,
            skills=order,
            results=tuple(session.results[name] for name in order),
            output_dir=output_dir,
        )
        _write_json(output_dir / "universe_report.json", report.to_dict())
        return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "UNIVERSE-AI-FNF: computer use, coder, audio, eyes, hands, full FNF "
            "mods, and FNF draw style from one chart."
        )
    )
    parser.add_argument("--chart", type=Path, help="Psych Engine chart JSON")
    parser.add_argument(
        "--skills",
        default="all",
        help=f"comma separated subset of: {', '.join(ALL_SKILLS)} (default: all)",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("universe_out"))
    parser.add_argument(
        "--reference-image", type=Path, help="character reference for the eyes skill"
    )
    parser.add_argument("--audio", type=Path, help="16-bit PCM WAV of the song")
    parser.add_argument("--mod-name", default="UniverseAI")
    parser.add_argument("--character", dest="character_name", default="universe-bf")
    parser.add_argument("--art-style", default="fnf bold outline cel shading")
    parser.add_argument("--sprite-size", type=int, default=256)
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--fps", type=int, choices=(24, 30, 60), default=24)
    parser.add_argument("--tail-ms", type=float, default=1000.0)
    parser.add_argument(
        "--duration-seconds", type=float, help="optional timeline duration cap"
    )
    parser.add_argument(
        "--status", action="store_true", help="print the model capabilities and exit"
    )
    parser.add_argument("--verbose", action="store_true")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )
    if args.status:
        print(
            json.dumps(
                {
                    "architecture": UNIVERSE_ARCHITECTURE_NAME,
                    "manifest": str(MANIFEST_PATH),
                    "skills": UniverseAIFNF.capabilities(),
                },
                indent=2,
            )
        )
        return 0
    if args.chart is None:
        parser.error("--chart is required unless --status is used")
    if args.duration_seconds is not None and args.duration_seconds <= 0:
        parser.error("--duration-seconds must be positive")

    requested = (
        ALL_SKILLS
        if args.skills.strip().lower() == "all"
        else tuple(part.strip() for part in args.skills.split(",") if part.strip())
    )
    config = UniverseAIFNFConfig(
        skills=requested,
        mod_name=args.mod_name,
        character_name=args.character_name,
        art_style=args.art_style,
        sprite_size=args.sprite_size,
        seed=args.seed,
        reference_image=args.reference_image,
        audio_path=args.audio,
    )
    try:
        config.validate()
    except ValueError as error:
        parser.error(str(error))

    timeline = parse_chart(args.chart.expanduser().resolve(), args.fps, args.tail_ms)
    timeline = limit_timeline(timeline, args.duration_seconds)
    report = UniverseAIFNF(timeline, config).run(args.output_dir)
    LOGGER.info(
        "Wrote %s for %d skill(s)",
        report.output_dir / "universe_report.json",
        len(report.skills),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
