#!/usr/bin/env python3
"""x86-only ONNX export entrypoint."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from uas_ai_module.data.export_plan import load_export_plan  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export training checkpoint(s) to ONNX")
    parser.add_argument("--export-plan", required=True)
    parser.add_argument("--artifact-name")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    plan = load_export_plan(args.export_plan)
    artifacts = [a for a in plan.artifacts if args.artifact_name in {None, a.name}]
    if not artifacts:
        print(f"artifact not found: {args.artifact_name}", file=sys.stderr)
        return 2
    if args.dry_run:
        print(json.dumps({
            "ok": True,
            "mode": "dry-run",
            "plan_id": plan.plan_id,
            "artifacts": [artifact.name for artifact in artifacts],
        }, sort_keys=True))
        return 0
    try:
        import torch  # type: ignore  # noqa: F401
        import onnx  # type: ignore  # noqa: F401
    except Exception as exc:
        print(f"export dependencies unavailable; install requirements-dev.txt on x86: {exc}", file=sys.stderr)
        return 3
    print("real ONNX export implementation requires model-specific export adapter", file=sys.stderr)
    return 4


if __name__ == "__main__":
    raise SystemExit(main())
