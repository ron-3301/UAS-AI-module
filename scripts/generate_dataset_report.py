#!/usr/bin/env python3
"""Generate a dataset summary report from a manifest."""
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
    parser = argparse.ArgumentParser(description="Generate dataset report")
    parser.add_argument("manifest")
    parser.add_argument("--output", help="Output JSON path")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = dataset_report(load_dataset_manifest(args.manifest))
    if args.dry_run or not args.output:
        print(json.dumps({"ok": True, "dataset_id": report["dataset_id"], "total_images": report["total_images"]}, sort_keys=True))
        return 0
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"ok": True, "output": str(output), "total_images": report["total_images"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
