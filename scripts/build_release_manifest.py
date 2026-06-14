#!/usr/bin/env python3
"""Build a source file SHA-256 manifest."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from uas_ai_module.release.source_manifest import build_source_manifest  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build source SHA-256 release manifest")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--output", help="Output JSON path")
    parser.add_argument("--dry-run", action="store_true", help="Print manifest summary without writing")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    manifest = build_source_manifest(args.root)
    data = manifest.to_dict()
    if args.dry_run or not args.output:
        print(json.dumps({"ok": True, "file_count": manifest.file_count}, sort_keys=True))
        return 0
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"ok": True, "output": str(output), "file_count": manifest.file_count}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
