#!/usr/bin/env python3
"""Run the Phase 17 external execution readiness gate.

This gate does not require real hardware. It verifies that all external
integration entrypoints can be planned/dry-run safely and advisory-only.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class CheckCommand:
    name: str
    command: tuple[str, ...]


CHECKS = (
    CheckCommand("phase16_gate", (sys.executable, "scripts/phase16_check.py", "--stop-on-failure")),
    CheckCommand(
        "external_validation_plan_dry_run",
        (sys.executable, "scripts/run_external_validation.py", "configs/integration/external_validation.example.json", "--dry-run"),
    ),
    CheckCommand("mavlink_record_dry_run", (sys.executable, "scripts/record_mavlink_telemetry.py", "--samples", "2", "--dry-run")),
    CheckCommand("camera_capture_dry_run", (sys.executable, "scripts/capture_camera_frames.py", "--frames", "2", "--dry-run")),
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Phase 17 external execution readiness checks")
    parser.add_argument("--dry-run", action="store_true", help="Print checks without executing them")
    parser.add_argument("--stop-on-failure", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    failures: list[str] = []
    for check in CHECKS:
        printable = " ".join(check.command)
        if args.dry_run:
            print(f"[DRY-RUN] {check.name}: {printable}")
            continue
        print(f"[RUN] {check.name}: {printable}", flush=True)
        proc = subprocess.run(check.command, cwd=ROOT, env=env, text=True, capture_output=True)
        if proc.returncode != 0:
            failures.append(check.name)
            print(f"[FAIL] {check.name}: exit {proc.returncode}", file=sys.stderr)
            if proc.stdout:
                print(proc.stdout, file=sys.stderr)
            if proc.stderr:
                print(proc.stderr, file=sys.stderr)
            if args.stop_on_failure:
                break
        else:
            print(f"[PASS] {check.name}")
    if args.dry_run:
        return 0
    if failures:
        print(f"Phase 17 check failed: {failures}", file=sys.stderr)
        return 1
    print("Phase 17 external execution readiness check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
