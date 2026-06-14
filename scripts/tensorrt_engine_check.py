#!/usr/bin/env python3
"""TensorRT engine boundary check."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from uas_ai_module.detection.tensorrt_detector import TensorRtDetector  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate TensorRT .engine runtime boundary")
    parser.add_argument("engine", help="Path to .engine artifact")
    parser.add_argument("--dry-run", action="store_true", help="Validate suffix without loading TensorRT")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    detector = TensorRtDetector(args.engine)
    result = {"ok": True, "engine": str(detector.engine_path), "mode": "dry-run" if args.dry_run else "boundary"}
    if not args.dry_run:
        # The detector boundary currently raises if actual inference is attempted.
        result["note"] = "engine suffix validated; real TensorRT execution requires Jetson backend implementation"
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
