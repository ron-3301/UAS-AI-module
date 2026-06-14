#!/usr/bin/env python3
"""TensorRT engine build entrypoint.

Run on Jetson or an environment with TensorRT tooling available. `--dry-run`
validates the export plan without invoking TensorRT.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from uas_ai_module.data.export_plan import load_export_plan  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build TensorRT engine(s) from ONNX artifact(s)")
    parser.add_argument("--export-plan", required=True)
    parser.add_argument("--artifact-name")
    parser.add_argument("--trtexec", default="trtexec")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    plan = load_export_plan(args.export_plan)
    artifacts = [a for a in plan.artifacts if args.artifact_name in {None, a.name}]
    if not artifacts:
        print(f"artifact not found: {args.artifact_name}", file=sys.stderr)
        return 2
    commands = []
    for artifact in artifacts:
        if artifact.tensorrt_output is None:
            continue
        commands.append([
            args.trtexec,
            f"--onnx={artifact.onnx_output}",
            f"--saveEngine={artifact.tensorrt_output}",
        ])
    if args.dry_run:
        print(json.dumps({"ok": True, "mode": "dry-run", "commands": commands}, sort_keys=True))
        return 0
    if shutil.which(args.trtexec) is None:
        print(f"TensorRT tool not found: {args.trtexec}", file=sys.stderr)
        return 3
    for command in commands:
        subprocess.run(command, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
