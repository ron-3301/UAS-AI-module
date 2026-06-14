#!/usr/bin/env python3
"""Run deterministic mission replay through the rebuilt advisory pipeline."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from uas_ai_module.output.schema_validator import AdvisorySchemaValidator  # noqa: E402
from uas_ai_module.pipeline import Pipeline  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Replay recorded/synthetic mission frames")
    parser.add_argument("manifest", help="Replay manifest JSON")
    parser.add_argument("--uas-id", default="uas-replay")
    parser.add_argument("--steps", type=int, default=1)
    parser.add_argument("--validate-output-schema", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Validate manifest/load pipeline but do not emit packets")
    args = parser.parse_args(argv)

    if args.steps <= 0:
        parser.error("--steps must be positive")

    pipeline = Pipeline.replay(args.manifest, uas_id=args.uas_id)
    if args.dry_run:
        print(json.dumps({"ok": True, "manifest": args.manifest, "mode": "dry-run"}, sort_keys=True))
        return 0
    validator = AdvisorySchemaValidator() if args.validate_output_schema else None
    packets = []
    try:
        for _ in range(args.steps):
            packet = pipeline.run_once().advisory
            if validator:
                validator.validate(packet)
            packets.append(packet)
    except EOFError as exc:
        print(f"replay exhausted: {exc}", file=sys.stderr)
        return 2

    if args.pretty:
        print(json.dumps(packets[0] if len(packets) == 1 else packets, indent=2, sort_keys=True))
    else:
        for packet in packets:
            print(json.dumps(packet, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
