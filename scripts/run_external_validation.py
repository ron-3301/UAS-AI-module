#!/usr/bin/env python3
"""Run an advisory-only external SITL/hardware validation plan.

All MAVLink checks are read-only smoke checks. This runner never sends vehicle
commands.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from uas_ai_module.integration.external_validation import ExternalCheck, load_external_validation_plan  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run external SITL/hardware validation plan")
    parser.add_argument("plan", help="External validation plan JSON")
    parser.add_argument("--output", help="Optional report JSON path")
    parser.add_argument("--dry-run", action="store_true", help="Print report with planned commands only")
    parser.add_argument("--stop-on-failure", action="store_true")
    return parser


def command_for_check(check: ExternalCheck) -> list[str]:
    params = check.parameters
    if check.kind == "mavlink":
        return [
            sys.executable,
            "scripts/mavlink_smoke_test.py",
            "--endpoint",
            str(params.get("endpoint", "udp:0.0.0.0:14550")),
            "--timeout-s",
            str(params.get("timeout_s", 1.0)),
        ]
    if check.kind == "camera":
        return [
            sys.executable,
            "scripts/camera_smoke_test.py",
            "--source",
            str(params.get("source", "0")),
            "--frames",
            str(params.get("frames", 1)),
        ]
    if check.kind == "onnx":
        command = [sys.executable, "scripts/onnx_runtime_smoke.py", str(params.get("metadata", "models/detector.metadata.example.json"))]
        if bool(params.get("verify_hash", False)):
            command.append("--verify-hash")
        return command
    if check.kind == "tensorrt":
        return [sys.executable, "scripts/tensorrt_engine_check.py", str(params.get("engine", "models/detector.engine"))]
    if check.kind == "observability":
        command = [sys.executable, "scripts/runtime_observability_smoke.py"]
        if params.get("log_jsonl"):
            command.extend(["--log-jsonl", str(params["log_jsonl"])])
        if bool(params.get("prometheus", False)):
            command.append("--prometheus")
        return command
    raise ValueError(f"unsupported check kind: {check.kind}")


def dry_run_command(command: list[str]) -> list[str]:
    if "--dry-run" in command:
        return command
    return command + ["--dry-run"]


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    plan = load_external_validation_plan(args.plan)
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SRC)
    results = []
    failures = []

    for check in plan.checks:
        command = command_for_check(check)
        if not check.enabled:
            results.append({
                "name": check.name,
                "kind": check.kind,
                "enabled": False,
                "ok": True,
                "command": command,
                "returncode": None,
                "stdout": "",
                "stderr": "",
                "skipped_reason": "disabled",
            })
            continue

        command_to_run = dry_run_command(command) if args.dry_run else command
        if args.dry_run:
            results.append({
                "name": check.name,
                "kind": check.kind,
                "enabled": True,
                "ok": True,
                "command": command_to_run,
                "returncode": None,
                "stdout": "",
                "stderr": "",
                "skipped_reason": "dry-run",
            })
            continue

        proc = subprocess.run(command_to_run, cwd=ROOT, env=env, text=True, capture_output=True)
        ok = proc.returncode == 0
        if not ok:
            failures.append(check.name)
        results.append({
            "name": check.name,
            "kind": check.kind,
            "enabled": True,
            "ok": ok,
            "command": command_to_run,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "skipped_reason": None,
        })
        if failures and args.stop_on_failure:
            break

    report = {
        "version": "1.0",
        "plan_id": plan.plan_id,
        "advisory_only": True,
        "ok": not failures,
        "results": results,
    }
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
