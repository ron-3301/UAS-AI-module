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


def test_phase15_smoke_scripts_dry_run() -> None:
    commands = [
        [sys.executable, "scripts/onnx_runtime_smoke.py", "models/detector.metadata.example.json", "--dry-run"],
        [sys.executable, "scripts/runtime_observability_smoke.py", "--dry-run", "--prometheus"],
        [sys.executable, "scripts/phase15_check.py", "--dry-run"],
    ]
    for command in commands:
        proc = run(command)
        assert proc.stdout


def test_observability_smoke_can_write_jsonl(tmp_path) -> None:
    log_path = tmp_path / "advisory.jsonl"
    proc = run([
        sys.executable,
        "scripts/runtime_observability_smoke.py",
        "--log-jsonl",
        str(log_path),
    ])
    result = json.loads(proc.stdout)
    assert result["ok"] is True
    assert log_path.exists()
    assert json.loads(log_path.read_text().splitlines()[0])["advisory_only"] is True


def test_phase15_smoke_scripts_expose_help() -> None:
    commands = [
        [sys.executable, "scripts/onnx_runtime_smoke.py", "--help"],
        [sys.executable, "scripts/runtime_observability_smoke.py", "--help"],
        [sys.executable, "scripts/phase15_check.py", "--help"],
    ]
    for command in commands:
        proc = run(command)
        assert "usage:" in proc.stdout.lower()
