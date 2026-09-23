"""Rich terminal chat and command interface for FNF-OMNI-STUDIO-V2."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from studio import FNFOMNIStudioV2, STUDIO_NAME


def _console():
    try:
        from rich.console import Console
    except ImportError:
        return None
    return Console()


def _print(console, message: str) -> None:
    if console:
        console.print(message)
    else:
        print(message)


class StudioChat:
    def __init__(self, studio: Optional[FNFOMNIStudioV2] = None) -> None:
        self.studio = studio or FNFOMNIStudioV2()
        self.console = _console()

    def execute(self, line: str) -> bool:
        parts = line.strip().split()
        command = parts[0].lower() if parts else ""
        if command in {"/quit", "/exit"}:
            return False
        if command == "/help":
            _print(self.console, "[bold]Commands:[/bold] /status /skills /plan /render /help /quit")
        elif command == "/status":
            _print(self.console, str(self.studio.status()))
        elif command == "/skills":
            _print(self.console, "chart-parser openpose-guide hud-compositor sneak-peek cloud-free osworld-bridge")
        elif command == "/plan":
            _print(self.console, "Parse chart -> generate pose guides -> compose deterministic HUD -> export preview/video.")
        elif command == "/render":
            if len(parts) < 3:
                _print(self.console, "Usage: /render CHART.json OUTPUT.png")
            else:
                output = self.studio.render_sneak_peek(Path(parts[1]), Path(parts[2]))
                _print(self.console, f"Wrote {output}")
        elif line.strip():
            _print(self.console, "Studio chat is ready. Use /help for engine commands.")
        return True

    def run(self) -> None:
        _print(self.console, f"[bold cyan]{STUDIO_NAME}[/bold cyan] ready. /help for commands.")
        while True:
            try:
                line = input("fnf> ")
            except (EOFError, KeyboardInterrupt):
                print()
                return
            if not self.execute(line):
                return
