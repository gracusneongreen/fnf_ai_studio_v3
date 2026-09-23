"""Optional OSWorld-style computer-use bridge with an auditable action log."""

from __future__ import annotations

import json
import math
import random
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Iterator, List, Optional, Tuple


Point = Tuple[float, float]


@dataclass(frozen=True)
class ComputerAction:
    action: str
    args: dict
    timestamp: float


@dataclass(frozen=True)
class HumanMotionConfig:
    """Deterministic controls for natural-looking desktop interactions."""

    path_steps: int = 18
    jitter_px: float = 1.5
    overshoot_px: float = 6.0
    typing_min_interval: float = 0.025
    typing_max_interval: float = 0.09
    seed: int = 1337

    def validate(self) -> None:
        if self.path_steps < 2:
            raise ValueError("path_steps must be at least 2")
        if self.jitter_px < 0 or self.overshoot_px < 0:
            raise ValueError("cursor variation must not be negative")
        if (
            self.typing_min_interval < 0
            or self.typing_max_interval < self.typing_min_interval
        ):
            raise ValueError("typing intervals must be ordered and non-negative")


def generate_cursor_trajectory(
    start: Point,
    target: Point,
    motion: HumanMotionConfig = HumanMotionConfig(),
) -> List[Point]:
    """Generate a cubic-Bezier cursor path with jitter and decelerating arrival."""

    motion.validate()
    rng = random.Random(motion.seed + round(start[0]) + round(target[1]))
    dx, dy = target[0] - start[0], target[1] - start[1]
    distance = math.hypot(dx, dy)
    if distance == 0:
        return [start] * motion.path_steps
    nx, ny = -dy / distance, dx / distance
    curve = rng.uniform(-0.2, 0.2) * distance
    control_1 = (
        start[0] + dx * 0.32 + nx * curve,
        start[1] + dy * 0.32 + ny * curve,
    )
    control_2 = (
        start[0] + dx * 0.78 + nx * curve * 0.5,
        start[1] + dy * 0.78 + ny * curve * 0.5,
    )
    overshoot = (
        target[0] + dx / distance * motion.overshoot_px,
        target[1] + dy / distance * motion.overshoot_px,
    )
    path: List[Point] = []
    for index in range(motion.path_steps):
        raw_t = index / (motion.path_steps - 1)
        t = 1.0 - (1.0 - raw_t) ** 2
        point = OSWorldBridge._cubic_bezier(start, control_1, control_2, overshoot, t)
        jitter = motion.jitter_px * math.sin(raw_t * math.pi)
        path.append((point[0] + nx * jitter, point[1] + ny * jitter))
    path.append(target)
    return path


class OSWorldBridge:
    """Best-effort desktop adapter; optional dependencies stay optional."""

    def __init__(
        self,
        log_path: Optional[Path] = None,
        motion: HumanMotionConfig = HumanMotionConfig(),
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        motion.validate()
        self.log_path = log_path
        self.motion = motion
        self.sleep_fn = sleep_fn
        self.actions: List[ComputerAction] = []

    def _record(self, action: str, **args: Any) -> None:
        event = ComputerAction(action, args, time.time())
        self.actions.append(event)
        if self.log_path:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(asdict(event)) + "\n")

    def screenshot(
        self,
        output: Optional[Path] = None,
        cursor: Optional[Point] = None,
    ):
        try:
            import mss
            from PIL import Image
        except ImportError as exc:
            raise RuntimeError("install mss and Pillow for desktop screenshots") from exc
        with mss.mss() as capture:
            monitor = capture.monitors[1]
            shot = capture.grab(monitor)
            image = Image.frombytes("RGB", shot.size, shot.rgb)
        if cursor is None:
            try:
                cursor = tuple(self._pyautogui().position())
            except RuntimeError:
                cursor = None
        if cursor is not None:
            self._draw_cursor(image, cursor)
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            image.save(output)
        self._record(
            "screenshot",
            output=str(output) if output else None,
            cursor_visible=cursor is not None,
        )
        return image

    def screenshot_stream(
        self,
        frames: int = 1,
        interval_seconds: float = 0.1,
    ) -> Iterator[Any]:
        """Yield annotated desktop frames for a live visual feedback loop."""

        if frames <= 0 or interval_seconds < 0:
            raise ValueError("frames must be positive and interval non-negative")
        for index in range(frames):
            yield self.screenshot()
            if index + 1 < frames:
                self.sleep_fn(interval_seconds)

    def cursor_path(self, start: Point, target: Point) -> List[Point]:
        """Build a cubic Bezier path with jitter and a small target overshoot."""
        return generate_cursor_trajectory(start, target, self.motion)

    @staticmethod
    def _cubic_bezier(
        start: Point,
        control_1: Point,
        control_2: Point,
        end: Point,
        t: float,
    ) -> Point:
        inverse = 1.0 - t
        return (
            inverse**3 * start[0]
            + 3 * inverse**2 * t * control_1[0]
            + 3 * inverse * t**2 * control_2[0]
            + t**3 * end[0],
            inverse**3 * start[1]
            + 3 * inverse**2 * t * control_1[1]
            + 3 * inverse * t**2 * control_2[1]
            + t**3 * end[1],
        )

    def move_to(self, x: int, y: int) -> None:
        pyautogui = self._pyautogui()
        start = tuple(pyautogui.position())
        path = self.cursor_path(start, (x, y))
        for point in path:
            pyautogui.moveTo(round(point[0]), round(point[1]), duration=0)
        self._record(
            "move",
            start=start,
            target=(x, y),
            steps=len(path),
            overshoot_px=self.motion.overshoot_px,
            jitter_px=self.motion.jitter_px,
        )

    def click(self, x: int, y: int, button: str = "left") -> None:
        self.move_to(x, y)
        self._pyautogui().click(button=button)
        self._record("click", x=x, y=y, button=button)

    def type_text(self, text: str, interval: Optional[float] = None) -> None:
        pyautogui = self._pyautogui()
        rng = random.Random(self.motion.seed + len(text))
        for character in text:
            pyautogui.write(character, interval=0)
            delay = (
                interval
                if interval is not None
                else rng.uniform(
                    self.motion.typing_min_interval,
                    self.motion.typing_max_interval,
                )
            )
            if delay:
                self.sleep_fn(delay)
        self._record(
            "type",
            length=len(text),
            cadence="fixed" if interval is not None else "natural",
        )

    def hotkey(self, *keys: str) -> None:
        self._pyautogui().hotkey(*keys)
        self._record("hotkey", keys=list(keys))

    @staticmethod
    def _pyautogui():
        try:
            import pyautogui
        except ImportError as exc:
            raise RuntimeError(
                "install pyautogui to enable mouse and keyboard automation"
            ) from exc
        return pyautogui

    @staticmethod
    def _draw_cursor(image: Any, cursor: Point) -> None:
        from PIL import ImageDraw

        draw = ImageDraw.Draw(image, "RGBA")
        x, y = round(cursor[0]), round(cursor[1])
        tip = (x, y)
        outline = [(x, y), (x, y + 20), (x + 6, y + 15), (x + 14, y + 27)]
        draw.polygon(outline, fill=(255, 255, 255, 245), outline=(0, 0, 0, 255))
        draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(255, 64, 96, 220))
        draw.ellipse((tip[0] - 2, tip[1] - 2, tip[0] + 2, tip[1] + 2), fill="white")
