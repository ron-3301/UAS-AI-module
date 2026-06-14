#!/usr/bin/env python3
"""Camera frame ingestion smoke test."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from uas_ai_module.ingestion.camera import OpenCvCameraSource  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OpenCV camera ingestion smoke test")
    parser.add_argument("--source", default="0", help="OpenCV VideoCapture source")
    parser.add_argument("--frames", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true", help="Validate arguments without opening camera")
    return parser


def _parse_source(value: str):
    try:
        return int(value)
    except ValueError:
        return value


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.frames <= 0:
        print("--frames must be positive", file=sys.stderr)
        return 2
    source = _parse_source(args.source)
    if args.dry_run:
        print(json.dumps({"ok": True, "mode": "dry-run", "source": args.source, "frames": args.frames}, sort_keys=True))
        return 0
    camera = OpenCvCameraSource(source=source, camera_id="smoke-cam")
    try:
        frames = [camera.read() for _ in range(args.frames)]
    finally:
        camera.release()
    print(json.dumps({
        "ok": True,
        "frames": len(frames),
        "width": frames[-1].width,
        "height": frames[-1].height,
        "last_frame_id": frames[-1].frame_id,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
