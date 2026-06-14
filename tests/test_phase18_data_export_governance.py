from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from uas_ai_module.data.dataset_manifest import class_balance_warnings, dataset_report, load_dataset_manifest
from uas_ai_module.data.export_plan import export_plan_summary, load_export_plan, ExportPlanError

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "configs" / "data" / "dataset_manifest.example.json"
EXPORT_PLAN = ROOT / "configs" / "models" / "export_plan.example.json"


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True, check=True)


def test_dataset_manifest_loads_and_reports() -> None:
    manifest = load_dataset_manifest(DATASET)
    assert manifest.dataset_id == "uas-rebuild-example"
    assert manifest.total_images == 1000
    assert manifest.split_names() == ("train", "val", "test")
    report = dataset_report(manifest)
    assert report["aggregate_class_counts"]["Vehicle-Wheeled"] == 280
    assert class_balance_warnings(manifest, min_fraction=0.005, max_imbalance_ratio=50.0) == []


def test_dataset_manifest_rejects_unknown_class_count(tmp_path: Path) -> None:
    data = json.loads(DATASET.read_text())
    data["splits"][0]["class_counts"]["NotAClass"] = 1
    path = tmp_path / "bad_dataset.json"
    path.write_text(json.dumps(data))
    with pytest.raises(Exception):
        load_dataset_manifest(path)


def test_export_plan_loads_and_summarizes() -> None:
    plan = load_export_plan(EXPORT_PLAN)
    assert plan.plan_id == "detector-export-example"
    assert plan.artifacts[0].onnx_output.suffix == ".onnx"
    summary = export_plan_summary(plan)
    assert summary["artifacts"][0]["role"] == "detector"


def test_export_plan_rejects_runtime_artifact_as_checkpoint(tmp_path: Path) -> None:
    data = json.loads(EXPORT_PLAN.read_text())
    data["artifacts"][0]["source_checkpoint"] = "bad.onnx"
    path = tmp_path / "bad_export_plan.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ExportPlanError):
        load_export_plan(path)


def test_phase18_governance_scripts_dry_run() -> None:
    commands = [
        [sys.executable, "scripts/validate_dataset_manifest.py", str(DATASET), "--dry-run"],
        [sys.executable, "scripts/generate_dataset_report.py", str(DATASET), "--dry-run"],
        [sys.executable, "scripts/check_class_balance.py", str(DATASET), "--dry-run"],
        [sys.executable, "scripts/prepare_model_export.py", str(EXPORT_PLAN), "--dry-run"],
        [sys.executable, "scripts/write_model_metadata.py", str(EXPORT_PLAN), "--dry-run"],
        [sys.executable, "scripts/phase18_check.py", "--dry-run"],
    ]
    for command in commands:
        proc = run(command)
        assert proc.stdout


def test_phase18_training_scripts_dry_run_and_help() -> None:
    commands = [
        [sys.executable, "training/train_detector.py", "--dataset-manifest", str(DATASET), "--epochs", "1", "--dry-run"],
        [sys.executable, "training/export_onnx.py", "--export-plan", str(EXPORT_PLAN), "--dry-run"],
        [sys.executable, "training/build_tensorrt.py", "--export-plan", str(EXPORT_PLAN), "--dry-run"],
        [sys.executable, "training/train_detector.py", "--help"],
        [sys.executable, "training/export_onnx.py", "--help"],
        [sys.executable, "training/build_tensorrt.py", "--help"],
    ]
    for command in commands:
        proc = run(command)
        assert proc.stdout
