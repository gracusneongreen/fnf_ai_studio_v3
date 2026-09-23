"""Optional OSWorld-style computer-use bridge with an auditable action log."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, List, Optional


@dataclass(frozen=True)
class ComputerAction:
    action: str
    args: dict
    timestamp: float


class OSWorldBridge:
    """Best-effort desktop adapter; optional dependencies stay optional."""

    def __init__(self, log_path: Optional[Path] = None) -> None:
        self.log_path = log_path
        self.actions: List[ComputerAction] = []

    def _record(self, action: str, **args: Any) -> None:
        event = ComputerAction(action, args, time.time())
        self.actions.append(event)
        if self.log_path:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(asdict(event)) + "\n")

    def screenshot(self, output: Optional[Path] = None):
        try:
            import mss
            from PIL import Image
        except ImportError as exc:
            raise RuntimeError("install mss and Pillow for desktop screenshots") from exc
        with mss.mss() as capture:
            monitor = capture.monitors[1]
            shot = capture.grab(monitor)
            image = Image.frombytes("RGB", shot.size, shot.rgb)
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            image.save(output)
        self._record("screenshot", output=str(output) if output else None)
        return image

    def click(self, x: int, y: int, button: str = "left") -> None:
        self._pyautogui().click(x=x, y=y, button=button)
        self._record("click", x=x, y=y, button=button)

    def type_text(self, text: str, interval: float = 0.0) -> None:
        self._pyautogui().write(text, interval=interval)
        self._record("type", length=len(text), interval=interval)

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
