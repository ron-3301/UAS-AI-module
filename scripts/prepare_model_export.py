#!/usr/bin/env python3
"""Validate and summarize a model export plan.

This script prepares x86-side export work. It does not run PyTorch or TensorRT
unless future non-dry-run implementations are added deliberately.
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

from uas_ai_module.data.export_plan import export_plan_summary, load_export_plan  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare/validate model export plan")
    parser.add_argument("plan")
    parser.add_argument("--check-checkpoints", action="store_true")
    parser.add_argument("--output", help="Optional output summary JSON")
    parser.add_argument("--dry-run", action="store_true", help="Validate only; do not export")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    plan = load_export_plan(args.plan, validate_checkpoint_exists=args.check_checkpoints and not args.dry_run)
    summary = export_plan_summary(plan)
    if args.output and not args.dry_run:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"ok": True, "plan_id": plan.plan_id, "artifacts": len(plan.artifacts), "mode": "dry-run" if args.dry_run else "validated"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
