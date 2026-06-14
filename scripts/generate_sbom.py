#!/usr/bin/env python3
"""Generate a minimal requirements-based SBOM."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from uas_ai_module.release.sbom import parse_requirements_file  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate requirements-based SBOM")
    parser.add_argument("--requirements", action="append", default=[str(ROOT / "requirements" / "requirements-runtime.txt")])
    parser.add_argument("--output", help="Output JSON path")
    parser.add_argument("--dry-run", action="store_true", help="Print summary without writing")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    entries = []
    for req in args.requirements:
        entries.extend(item.to_dict() for item in parse_requirements_file(req))
    data = {"version": "1.0", "requirements": entries}
    if args.dry_run or not args.output:
        print(json.dumps({"ok": True, "requirements": len(entries)}, sort_keys=True))
        return 0
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"ok": True, "output": str(output), "requirements": len(entries)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
