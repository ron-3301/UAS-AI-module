#!/usr/bin/env python3
"""Capture camera frames to .npy files for integration fixtures."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from uas_ai_module.ingestion.camera import OpenCvCameraSource  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Capture camera frames to .npy files")
    parser.add_argument("--source", default="0")
    parser.add_argument("--frames", type=int, default=1)
    parser.add_argument("--output-dir", default="captures")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def parse_source(value: str):
    try:
        return int(value)
    except ValueError:
        return value


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.frames <= 0:
        print("--frames must be positive", file=sys.stderr)
        return 2
    if args.dry_run:
        print(json.dumps({"ok": True, "mode": "dry-run", "source": args.source, "frames": args.frames}, sort_keys=True))
        return 0
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    source = OpenCvCameraSource(parse_source(args.source), camera_id="capture")
    saved = []
    try:
        for _ in range(args.frames):
            frame = source.read()
            path = output_dir / f"{frame.frame_id}.npy"
            np.save(path, frame.data)
            saved.append(str(path))
    finally:
        source.release()
    print(json.dumps({"ok": True, "saved": saved}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
