#!/usr/bin/env python3
"""Generate or compare normalized golden replay outputs."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from uas_ai_module.output.golden import compare_packets, normalize_packets  # noqa: E402
from uas_ai_module.pipeline import Pipeline  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate/compare normalized golden replay outputs")
    parser.add_argument("manifest", help="Replay manifest JSON")
    parser.add_argument("--steps", type=int, default=1)
    parser.add_argument("--output", help="Golden output JSON path")
    parser.add_argument("--compare", help="Compare against an existing golden JSON file")
    parser.add_argument("--uas-id", default="uas-golden")
    parser.add_argument("--dry-run", action="store_true", help="Run replay and print normalized packets without writing")
    return parser


def replay_packets(manifest: str, *, steps: int, uas_id: str) -> list[dict]:
    pipeline = Pipeline.replay(manifest, uas_id=uas_id)
    return [pipeline.run_once().advisory for _ in range(steps)]


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.steps <= 0:
        print("--steps must be positive", file=sys.stderr)
        return 2

    normalized = normalize_packets(replay_packets(args.manifest, steps=args.steps, uas_id=args.uas_id))

    if args.compare:
        expected = json.loads(Path(args.compare).read_text())
        mismatches = compare_packets(normalized, expected)
        if mismatches:
            print("Golden replay comparison failed:", file=sys.stderr)
            for mismatch in mismatches:
                print(f"- {mismatch}", file=sys.stderr)
            return 1
        print(json.dumps({"ok": True, "mode": "compare", "packets": len(normalized)}, sort_keys=True))
        return 0

    if args.dry_run or not args.output:
        print(json.dumps(normalized, indent=2, sort_keys=True))
        return 0

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(normalized, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"ok": True, "mode": "write", "output": str(output), "packets": len(normalized)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
