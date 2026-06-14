#!/usr/bin/env python3
"""Deployment health check for the rebuilt runtime package."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> tuple[int, str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    proc = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True)
    return proc.returncode, proc.stdout, proc.stderr


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run runtime health checks for the advisory package")
    parser.add_argument("--pretty", action="store_true", default=True, help="Pretty-print JSON result")
    return parser


def main(argv: list[str] | None = None) -> int:
    _ = build_parser().parse_args(argv)
    checks: list[dict[str, object]] = []

    code, stdout, stderr = run([sys.executable, "scripts/check_runtime_deps.py"])
    checks.append({"name": "runtime_dependency_guard", "ok": code == 0, "stdout": stdout, "stderr": stderr})

    code, stdout, stderr = run([sys.executable, "-m", "uas_ai_module.cli", "--dry-run", "--validate-output-schema"])
    ok = False
    if code == 0:
        try:
            packet = json.loads(stdout)
            ok = packet.get("advisory_only") is True and packet.get("schema_version") == "1.1"
        except Exception:
            ok = False
    checks.append({"name": "dry_run_advisory", "ok": ok, "stdout": stdout[:500], "stderr": stderr})

    overall = all(bool(item["ok"]) for item in checks)
    print(json.dumps({"ok": overall, "checks": checks}, indent=2))
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
