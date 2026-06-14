#!/usr/bin/env python3
"""Run the Phase 13 stabilization gate.

This script is intentionally small and explicit so CI and operators run the same
checks. Use `--dry-run` to print the commands without executing them.
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
    CheckCommand("asset_validation", (sys.executable, "scripts/validate_assets.py")),
    CheckCommand("runtime_dependency_guard", (sys.executable, "scripts/check_runtime_deps.py")),
    CheckCommand("test_suite", (sys.executable, "-m", "pytest", "-q")),
    CheckCommand(
        "dry_run_schema_validation",
        (sys.executable, "-m", "uas_ai_module.cli", "--dry-run", "--validate-output-schema"),
    ),
    CheckCommand(
        "replay_schema_validation",
        (
            sys.executable,
            "-m",
            "uas_ai_module.cli",
            "--replay",
            "tests/fixtures/replay/sample_mission.json",
            "--replay-steps",
            "2",
            "--validate-output-schema",
        ),
    ),
    CheckCommand("deployment_health_check", (sys.executable, "scripts/jetson_health_check.py")),
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Phase 13 readiness/stabilization checks")
    parser.add_argument("--dry-run", action="store_true", help="Print checks without executing them")
    parser.add_argument("--stop-on-failure", action="store_true", help="Stop after the first failed check")
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
        print(f"Phase 13 check failed: {failures}", file=sys.stderr)
        return 1
    print("Phase 13 check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
