#!/usr/bin/env python3
"""Validate dataset governance manifest."""
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
    parser = argparse.ArgumentParser(description="Validate dataset manifest")
    parser.add_argument("manifest")
    parser.add_argument("--check-files", action="store_true", help="Require referenced dataset files/directories to exist")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print summary only")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    manifest = load_dataset_manifest(args.manifest, validate_files_exist=args.check_files and not args.dry_run)
    report = dataset_report(manifest)
    print(json.dumps({"ok": True, "dataset_id": manifest.dataset_id, "total_images": manifest.total_images, "splits": manifest.split_names()}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
