#!/usr/bin/env python3
"""Check aggregate class balance in a dataset manifest."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from uas_ai_module.data.dataset_manifest import class_balance_warnings, load_dataset_manifest  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check dataset class balance")
    parser.add_argument("manifest")
    parser.add_argument("--min-fraction", type=float, default=0.005)
    parser.add_argument("--max-imbalance-ratio", type=float, default=50.0)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    manifest = load_dataset_manifest(args.manifest)
    warnings = class_balance_warnings(
        manifest,
        min_fraction=args.min_fraction,
        max_imbalance_ratio=args.max_imbalance_ratio,
    )
    result = {"ok": not warnings, "warnings": warnings, "dataset_id": manifest.dataset_id}
    print(json.dumps(result, sort_keys=True))
    return 0 if not warnings or args.dry_run else 1


if __name__ == "__main__":
    raise SystemExit(main())
