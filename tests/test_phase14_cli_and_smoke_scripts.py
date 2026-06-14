from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True, check=True)


def test_run_once_with_mock_backends_validates_schema() -> None:
    proc = run([
        sys.executable,
        "-m",
        "uas_ai_module.cli",
        "--run-once",
        "--config",
        "configs/inference.example.json",
        "--allow-mock-backends",
        "--validate-output-schema",
    ])
    packet = json.loads(proc.stdout)
    assert packet["advisory_only"] is True
    assert packet["schema_version"] == "1.1"


def test_phase14_smoke_scripts_dry_run() -> None:
    commands = [
        [sys.executable, "scripts/mavlink_smoke_test.py", "--dry-run"],
        [sys.executable, "scripts/camera_smoke_test.py", "--dry-run"],
        [sys.executable, "scripts/model_smoke_test.py", "models/detector.metadata.example.json", "--dry-run"],
        [sys.executable, "scripts/tensorrt_engine_check.py", "models/detector.engine", "--dry-run"],
        [sys.executable, "scripts/phase14_check.py", "--dry-run"],
    ]
    for command in commands:
        proc = run(command)
        assert proc.stdout


def test_phase14_smoke_scripts_expose_help() -> None:
    commands = [
        [sys.executable, "scripts/mavlink_smoke_test.py", "--help"],
        [sys.executable, "scripts/camera_smoke_test.py", "--help"],
        [sys.executable, "scripts/model_smoke_test.py", "--help"],
        [sys.executable, "scripts/tensorrt_engine_check.py", "--help"],
        [sys.executable, "scripts/phase14_check.py", "--help"],
    ]
    for command in commands:
        proc = run(command)
        assert "usage:" in proc.stdout.lower()
