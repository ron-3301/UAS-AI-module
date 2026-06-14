#!/usr/bin/env python3
"""x86-only detector training entrypoint.

This script is intentionally not part of the Jetson runtime. Use `--dry-run` to
validate dataset/training metadata without importing PyTorch/Ultralytics.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from uas_ai_module.data.dataset_manifest import dataset_report, load_dataset_manifest  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train detector on x86 development machine")
    parser.add_argument("--dataset-manifest", required=True)
    parser.add_argument("--config", default="configs/training.yaml", help="Training config path, if available")
    parser.add_argument("--output-dir", default="training_runs/detector")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs without training")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.epochs <= 0:
        print("--epochs must be positive", file=sys.stderr)
        return 2
    manifest = load_dataset_manifest(args.dataset_manifest)
    report = dataset_report(manifest)
    if args.dry_run:
        print(json.dumps({
            "ok": True,
            "mode": "dry-run",
            "dataset_id": manifest.dataset_id,
            "total_images": report["total_images"],
            "epochs": args.epochs,
            "output_dir": args.output_dir,
        }, sort_keys=True))
        return 0
    try:
        import torch  # type: ignore  # noqa: F401
        import ultralytics  # type: ignore  # noqa: F401
    except Exception as exc:
        print(f"training dependencies unavailable; install requirements-dev.txt on x86: {exc}", file=sys.stderr)
        return 3
    print("real training loop is intentionally not implemented in this baseline; use dry-run/governance first", file=sys.stderr)
    return 4


if __name__ == "__main__":
    raise SystemExit(main())
