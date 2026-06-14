from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from uas_ai_module.integration.external_validation import ExternalValidationPlanError, load_external_validation_plan

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "configs" / "integration" / "external_validation.example.json"


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True, check=True)


def test_external_validation_plan_loads_and_is_advisory_only() -> None:
    plan = load_external_validation_plan(PLAN)
    assert plan.advisory_only is True
    assert len(plan.enabled_checks()) == 5
    assert {check.kind for check in plan.checks} == {"mavlink", "camera", "onnx", "tensorrt", "observability"}


def test_external_validation_plan_rejects_non_advisory(tmp_path: Path) -> None:
    data = json.loads(PLAN.read_text())
    data["advisory_only"] = False
    path = tmp_path / "bad_plan.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ExternalValidationPlanError):
        load_external_validation_plan(path)


def test_external_validation_runner_dry_run_outputs_report() -> None:
    proc = run([sys.executable, "scripts/run_external_validation.py", str(PLAN), "--dry-run"])
    report = json.loads(proc.stdout)
    assert report["advisory_only"] is True
    assert report["ok"] is True
    assert len(report["results"]) == 5
    assert all(result["skipped_reason"] == "dry-run" for result in report["results"])


def test_phase17_support_scripts_dry_run_and_help() -> None:
    commands = [
        [sys.executable, "scripts/record_mavlink_telemetry.py", "--samples", "1", "--dry-run"],
        [sys.executable, "scripts/capture_camera_frames.py", "--frames", "1", "--dry-run"],
        [sys.executable, "scripts/run_external_validation.py", str(PLAN), "--dry-run"],
        [sys.executable, "scripts/phase17_check.py", "--dry-run"],
        [sys.executable, "scripts/phase17_check.py", "--help"],
    ]
    for command in commands:
        proc = run(command)
        assert proc.stdout
