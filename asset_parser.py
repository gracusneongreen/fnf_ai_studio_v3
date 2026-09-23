"""Parsers for local FNF spritesheets and character configuration files."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass(frozen=True)
class SpriteFrame:
    name: str
    x: int
    y: int
    width: int
    height: int
    frame_x: int = 0
    frame_y: int = 0
    frame_width: Optional[int] = None
    frame_height: Optional[int] = None


@dataclass(frozen=True)
class SpriteSheet:
    image_path: Optional[str]
    frames: tuple[SpriteFrame, ...]


def _integer(element: ET.Element, name: str, default: int = 0) -> int:
    value = element.attrib.get(name)
    return default if value is None else int(float(value))


def parse_spritesheet(path: Path) -> SpriteSheet:
    """Parse Sparrow/TexturePacker-style ``TextureAtlas`` XML."""

    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise ValueError(f"invalid spritesheet XML in {path}: {exc}") from exc
    frames = []
    for element in root.findall(".//SubTexture"):
        name = element.attrib.get("name")
        if not name:
            raise ValueError(f"spritesheet frame in {path} is missing name")
        frames.append(
            SpriteFrame(
                name=name,
                x=_integer(element, "x"),
                y=_integer(element, "y"),
                width=_integer(element, "width"),
                height=_integer(element, "height"),
                frame_x=_integer(element, "frameX"),
                frame_y=_integer(element, "frameY"),
                frame_width=(
                    _integer(element, "frameWidth")
                    if "frameWidth" in element.attrib
                    else None
                ),
                frame_height=(
                    _integer(element, "frameHeight")
                    if "frameHeight" in element.attrib
                    else None
                ),
            )
        )
    return SpriteSheet(root.attrib.get("imagePath"), tuple(frames))


def load_character_config(path: Path) -> dict[str, Any]:
    """Load and validate a character JSON config without discarding metadata."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid character JSON in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("character config must contain a JSON object")
    return payload
