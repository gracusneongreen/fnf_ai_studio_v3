#!/usr/bin/env python3
"""Command-line entry point for FNF-OMNI-STUDIO-V2."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional, Sequence

from cli_chat import StudioChat
from studio import FNFOMNIStudioV2, StudioConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="FNF-OMNI-STUDIO-V2 autonomous chart-to-video toolkit."
    )
    parser.add_argument("--chart", type=Path, help="Psych Engine chart JSON")
    parser.add_argument("--output", type=Path, default=Path("outputs/fnf_sneak_peek.png"))
    parser.add_argument("--sneak-peek", action="store_true", help="export a fast storyboard")
    parser.add_argument("--chat", action="store_true", help="start the Rich terminal chat")
    parser.add_argument("--dashboard", action="store_true", help="start the local web dashboard")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--status", action="store_true", help="print engine status")
    parser.add_argument("--cloud-free", action="store_true", help="use local/free providers only")
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--size", type=int, default=512)
    parser.add_argument("--preview-max-frames", type=int, default=12)
    parser.add_argument("--preview-camera", choices=("wide", "medium", "close"), default="wide")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    studio = FNFOMNIStudioV2(
        StudioConfig(fps=args.fps, size=args.size, cloud_free=args.cloud_free)
    )
    if args.dashboard:
        from web_dashboard import DashboardService, create_dashboard_server

        server = create_dashboard_server(
            service=DashboardService(studio),
            host=args.host,
            port=args.port,
        )
        print(f"FNF-OMNI-STUDIO-V2 dashboard: http://{args.host}:{args.port}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            server.server_close()
        return 0
    if args.chat or not (args.status or args.sneak_peek):
        StudioChat(studio).run()
        return 0
    if args.status:
        print(studio.status())
    if args.sneak_peek:
        if args.chart is None:
            raise SystemExit("--chart is required with --sneak-peek")
        studio.render_sneak_peek(
            args.chart, args.output, args.preview_max_frames, args.preview_camera
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
