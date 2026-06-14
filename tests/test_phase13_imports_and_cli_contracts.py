from __future__ import annotations

import importlib
import os
import pkgutil
import subprocess
import sys
from pathlib import Path

import uas_ai_module

ROOT = Path(__file__).resolve().parents[1]


def test_all_runtime_modules_import() -> None:
    failures: list[str] = []
    for module in pkgutil.walk_packages(uas_ai_module.__path__, prefix="uas_ai_module."):
        try:
            importlib.import_module(module.name)
        except Exception as exc:  # pragma: no cover - diagnostic assertion
            failures.append(f"{module.name}: {exc}")
    assert failures == []


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True, check=True)


def test_cli_and_scripts_expose_help() -> None:
    commands = [
        [sys.executable, "-m", "uas_ai_module.cli", "--help"],
        [sys.executable, "scripts/validate_assets.py", "--help"],
        [sys.executable, "scripts/check_runtime_deps.py", "--help"],
        [sys.executable, "scripts/replay_mission.py", "--help"],
        [sys.executable, "scripts/jetson_health_check.py", "--help"],
        [sys.executable, "scripts/phase13_check.py", "--help"],
        [sys.executable, "scripts/phase14_check.py", "--help"],
        [sys.executable, "scripts/phase15_check.py", "--help"],
        [sys.executable, "scripts/phase16_check.py", "--help"],
        [sys.executable, "scripts/phase17_check.py", "--help"],
        [sys.executable, "scripts/phase18_check.py", "--help"],
    ]
    for command in commands:
        proc = run_command(command)
        assert "usage:" in proc.stdout.lower()


def test_heavier_scripts_support_dry_run() -> None:
    commands = [
        [
            sys.executable,
            "scripts/replay_mission.py",
            "tests/fixtures/replay/sample_mission.json",
            "--dry-run",
        ],
        [sys.executable, "scripts/phase13_check.py", "--dry-run"],
        [sys.executable, "scripts/phase14_check.py", "--dry-run"],
        [sys.executable, "scripts/phase15_check.py", "--dry-run"],
        [sys.executable, "scripts/phase16_check.py", "--dry-run"],
        [sys.executable, "scripts/phase17_check.py", "--dry-run"],
        [sys.executable, "scripts/phase18_check.py", "--dry-run"],
    ]
    for command in commands:
        proc = run_command(command)
        assert proc.stdout
