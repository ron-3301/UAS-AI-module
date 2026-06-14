#!/usr/bin/env python3
"""Run the Phase 18 dataset/training/export governance gate."""
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


DATASET_MANIFEST = "configs/data/dataset_manifest.example.json"
EXPORT_PLAN = "configs/models/export_plan.example.json"

CHECKS = (
    CheckCommand("phase17_gate", (sys.executable, "scripts/phase17_check.py", "--stop-on-failure")),
    CheckCommand("dataset_manifest_validation", (sys.executable, "scripts/validate_dataset_manifest.py", DATASET_MANIFEST, "--dry-run")),
    CheckCommand("dataset_report_dry_run", (sys.executable, "scripts/generate_dataset_report.py", DATASET_MANIFEST, "--dry-run")),
    CheckCommand("class_balance_check", (sys.executable, "scripts/check_class_balance.py", DATASET_MANIFEST, "--dry-run")),
    CheckCommand("export_plan_prepare", (sys.executable, "scripts/prepare_model_export.py", EXPORT_PLAN, "--dry-run")),
    CheckCommand("write_metadata_dry_run", (sys.executable, "scripts/write_model_metadata.py", EXPORT_PLAN, "--dry-run")),
    CheckCommand("train_detector_dry_run", (sys.executable, "training/train_detector.py", "--dataset-manifest", DATASET_MANIFEST, "--epochs", "1", "--dry-run")),
    CheckCommand("export_onnx_dry_run", (sys.executable, "training/export_onnx.py", "--export-plan", EXPORT_PLAN, "--dry-run")),
    CheckCommand("build_tensorrt_dry_run", (sys.executable, "training/build_tensorrt.py", "--export-plan", EXPORT_PLAN, "--dry-run")),
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Phase 18 dataset/training/export governance checks")
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
        print(f"Phase 18 check failed: {failures}", file=sys.stderr)
        return 1
    print("Phase 18 dataset/training/export governance check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
